"""
FastAPI Backend for Coding AI + Chatbot Application
Production-ready implementation with Phi-3.1 model integration
"""

import os
import sys
import json
import logging
import hashlib
import ast
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import asyncio
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, validator
from pymongo import MongoClient, ASCENDING, errors
from pymongo.database import Database
from dotenv import load_dotenv
import uvicorn
from jose import JWTError, jwt
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
PORT = int(os.getenv("PORT"))  # Port is required in production
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MODEL_PATH = os.getenv("MODEL_PATH", "/opt/render/project/src/models/phi-2.Q4_K_M.gguf")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Global variables for model
llm = None
model_loading_task = None

# MongoDB connection
mongo_client = None
db: Optional[Database] = None

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    skill_level: Optional[str] = Field(default="intermediate", pattern="^(beginner|intermediate|advanced)$")
    preferences: Optional[Dict[str, List[str]]] = None

class ChatResponse(BaseModel):
    response: str
    suggestions: Optional[List[str]] = None
    code_blocks: Optional[List[Dict[str, str]]] = None
    follow_up_questions: Optional[List[str]] = None
    error_detected: bool = False
    error_details: Optional[List[str]] = None

class UserProfile(BaseModel):
    user_id: str
    skill_level: str = "intermediate"
    preferences: Dict[str, List[str]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ConversationHistory(BaseModel):
    user_id: str
    messages: List[Dict[str, Any]]
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TokenData(BaseModel):
    username: Optional[str] = None

class UserAuth(BaseModel):
    username: str
    password: str

async def download_model():
    """Download the Phi-3.1 model if not present"""
    model_dir = Path("./models")
    model_dir.mkdir(exist_ok=True)
    
    if not Path(MODEL_PATH).exists():
        logger.info("Model not found. Downloading Phi-3.1-mini-4k-instruct...")
        try:
            # Using a quantized GGUF model suitable for low memory
            model_url = "https://huggingface.co/TheBloke/Phi-3-mini-4k-instruct-GGUF/resolve/main/phi-3-mini-4k-instruct.Q4_K_M.gguf"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(model_url, follow_redirects=True, timeout=300.0)
                if response.status_code == 200:
                    with open(MODEL_PATH, "wb") as f:
                        f.write(response.content)
                    logger.info("Model downloaded successfully")
                else:
                    logger.error(f"Failed to download model: {response.status_code}")
                    # Use a fallback simple model for demo purposes
                    logger.info("Using fallback model configuration")
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            logger.info("Continuing without model download - will use mock responses")

async def initialize_llm():
    """Initialize the language model"""
    global llm
    try:
        # Import llama-cpp-python only when needed
        from llama_cpp import Llama
        
        if Path(MODEL_PATH).exists():
            logger.info("Loading Phi-3.1 model...")
            llm = Llama(
                model_path=MODEL_PATH,
                n_ctx=4096,  # Context window
                n_threads=2,  # Use 2 threads for low memory usage
                n_gpu_layers=0,  # CPU only for Render free tier
                verbose=False
            )
            logger.info("Model loaded successfully")
        else:
            logger.warning("Model file not found. Using mock responses.")
            llm = None
    except ImportError:
        logger.warning("llama-cpp-python not installed. Using mock responses.")
        llm = None
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        llm = None

def initialize_mongodb():
    """Initialize MongoDB connection with proper error handling"""
    global mongo_client, db
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        mongo_client.admin.command('ping')
        db = mongo_client.coding_assistant
        
        # Create indexes
        db.users.create_index([("user_id", ASCENDING)], unique=True)
        db.conversations.create_index([("user_id", ASCENDING), ("session_id", ASCENDING)])
        db.conversations.create_index([("created_at", ASCENDING)])
        
        logger.info("MongoDB connected successfully")
    except errors.ServerSelectionTimeoutError:
        logger.error("MongoDB connection timeout. Using in-memory storage.")
        db = None
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("Starting up...")
    initialize_mongodb()
    
    # Start model download and loading in background
    global model_loading_task
    model_loading_task = asyncio.create_task(download_model())
    await model_loading_task
    await initialize_llm()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if mongo_client:
        mongo_client.close()

# Initialize FastAPI app
app = FastAPI(
    title="Coding AI Assistant API",
    description="Production-ready backend for AI-powered coding assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def check_python_syntax(code: str) -> List[str]:
    """Check Python code for syntax errors"""
    errors_found = []
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors_found.append(f"Syntax error at line {e.lineno}: {e.msg}")
    except Exception as e:
        errors_found.append(f"Parse error: {str(e)}")
    
    # Check for missing imports
    import_pattern = r'\b(import|from)\s+(\w+)'
    imports = re.findall(import_pattern, code)
    common_modules = {'os', 'sys', 'json', 'datetime', 'typing', 'math', 'random', 're'}
    
    # Check if undefined names are used
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                name = node.id
                if name not in dir(__builtins__) and not any(name in imp for imp in imports):
                    if name in common_modules:
                        errors_found.append(f"Missing import: {name}")
    except:
        pass
    
    return errors_found

def check_javascript_syntax(code: str) -> List[str]:
    """Basic JavaScript syntax checking"""
    errors_found = []
    
    # Check for common JS errors
    if code.count('{') != code.count('}'):
        errors_found.append("Mismatched curly braces")
    if code.count('(') != code.count(')'):
        errors_found.append("Mismatched parentheses")
    if code.count('[') != code.count(']'):
        errors_found.append("Mismatched square brackets")
    
    # Check for missing semicolons (basic check)
    lines = code.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.endswith((';', '{', '}', ',', ':', '//', '/*', '*/', '*/')) and not line.startswith('//'):
            if any(line.startswith(kw) for kw in ['if', 'else', 'for', 'while', 'function', 'class', 'const', 'let', 'var']):
                continue
            if i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if not next_line.startswith(('.', '[', '(', '{', '}', ')', ']')):
                    errors_found.append(f"Possible missing semicolon at line {i + 1}")
    
    return errors_found

def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """Extract code blocks from text"""
    code_blocks = []
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    for language, code in matches:
        if not language:
            language = "plaintext"
        code_blocks.append({
            "language": language,
            "code": code.strip()
        })
    
    return code_blocks

def generate_mock_response(message: str, context: Dict[str, Any]) -> str:
    """Generate a mock response when model is not available"""
    responses = {
        "hello": "Hello! I'm your coding assistant. How can I help you today?",
        "python": "Python is a great language! What would you like to build?",
        "javascript": "JavaScript is perfect for web development. Are you working on frontend or backend?",
        "help": "I can help you with Python, JavaScript, React, and more. What's your project about?"
    }
    
    message_lower = message.lower()
    for key, response in responses.items():
        if key in message_lower:
            return response
    
    return "I'm here to help with your coding questions. What would you like to build today?"

async def generate_ai_response(message: str, context: Dict[str, Any], user_history: List[Dict] = None) -> ChatResponse:
    """Generate AI response using Phi-3.1 model or fallback"""
    try:
        # Prepare context
        skill_level = context.get("skill_level", "intermediate")
        preferences = context.get("preferences", {})
        
        # Build prompt
        system_prompt = f"""You are an expert coding assistant. The user is a {skill_level} developer.
        Preferred languages: {preferences.get('languages', ['Python', 'JavaScript'])}
        Preferred frameworks: {preferences.get('frameworks', [])}
        
        Provide helpful, accurate code examples and explanations.
        Ask clarifying questions when needed.
        Check code for errors and suggest improvements."""
        
        if llm:
            # Use actual model
            full_prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"
            
            response = llm(
                full_prompt,
                max_tokens=512,
                temperature=0.7,
                top_p=0.95,
                stop=["User:", "\n\n"]
            )
            
            response_text = response['choices'][0]['text'].strip()
        else:
            # Use mock response
            response_text = generate_mock_response(message, context)
        
        # Extract code blocks
        code_blocks = extract_code_blocks(response_text)
        
        # Check for syntax errors in code
        errors_found = []
        for block in code_blocks:
            if block['language'] == 'python':
                errors = check_python_syntax(block['code'])
                errors_found.extend(errors)
            elif block['language'] in ['javascript', 'js']:
                errors = check_javascript_syntax(block['code'])
                errors_found.extend(errors)
        
        # Generate follow-up questions
        follow_up_questions = []
        if "web" in message.lower() or "app" in message.lower():
            follow_up_questions.append("Are you building a web application or mobile app?")
        if "database" in message.lower():
            follow_up_questions.append("Which database are you planning to use?")
        if "api" in message.lower():
            follow_up_questions.append("Do you need authentication for your API?")
        
        # Generate suggestions
        suggestions = []
        if code_blocks:
            suggestions.append("Consider adding error handling to your code")
            suggestions.append("You might want to add logging for debugging")
            if "async" in response_text:
                suggestions.append("Don't forget to handle async errors properly")
        
        return ChatResponse(
            response=response_text,
            suggestions=suggestions if suggestions else None,
            code_blocks=code_blocks if code_blocks else None,
            follow_up_questions=follow_up_questions if follow_up_questions else None,
            error_detected=len(errors_found) > 0,
            error_details=errors_found if errors_found else None
        )
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail="Error generating response")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = None) -> Optional[str]:
    """Get current user from JWT token (optional)"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Coding AI Assistant API",
        "version": "1.0.0",
        "endpoints": ["/chat", "/history/{user_id}", "/save/{user_id}", "/suggest/{user_id}", "/health"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "model_loaded": llm is not None,
        "database_connected": db is not None
    }
    return health_status

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(request: Request, message: ChatMessage, user_id: Optional[str] = "anonymous"):
    """Main chat endpoint"""
    logger.info(f"Chat request from user {user_id}: {message.message[:100]}...")
    
    try:
        # Get user profile if exists
        user_profile = None
        user_history = []
        
        if db and user_id != "anonymous":
            user_profile = db.users.find_one({"user_id": user_id})
            
            # Get recent conversation history
            recent_conversations = list(db.conversations.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(5))
            
            for conv in recent_conversations:
                user_history.extend(conv.get("messages", []))
        
        # Prepare context
        context = {
            "skill_level": message.skill_level or (user_profile.get("skill_level") if user_profile else "intermediate"),
            "preferences": message.preferences or (user_profile.get("preferences") if user_profile else {})
        }
        
        if message.context:
            context.update(message.context)
        
        # Generate response
        response = await generate_ai_response(message.message, context, user_history)
        
        # Save conversation if user is logged in
        if db and user_id != "anonymous":
            conversation_entry = {
                "user_id": user_id,
                "session_id": hashlib.md5(f"{user_id}{datetime.utcnow()}".encode()).hexdigest(),
                "messages": [
                    {"role": "user", "content": message.message, "timestamp": datetime.utcnow()},
                    {"role": "assistant", "content": response.response, "timestamp": datetime.utcnow()}
                ],
                "created_at": datetime.utcnow()
            }
            db.conversations.insert_one(conversation_entry)
        
        logger.info(f"Response generated for user {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{user_id}")
@limiter.limit("10/minute")
async def get_history(request: Request, user_id: str, limit: int = 50):
    """Get conversation history for a user"""
    logger.info(f"History request for user {user_id}")
    
    if not db:
        return {"error": "Database not available", "history": []}
    
    try:
        conversations = list(db.conversations.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit))
        
        # Convert ObjectId to string
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
            conv["created_at"] = conv["created_at"].isoformat()
            for msg in conv.get("messages", []):
                if "timestamp" in msg:
                    msg["timestamp"] = msg["timestamp"].isoformat()
        
        return {"user_id": user_id, "history": conversations}
        
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Error fetching history")

@app.post("/save/{user_id}")
@limiter.limit("20/minute")
async def save_conversation(request: Request, user_id: str, conversation: ConversationHistory):
    """Save a conversation"""
    logger.info(f"Save conversation for user {user_id}")
    
    if not db:
        return {"error": "Database not available", "saved": False}
    
    try:
        # Save user profile if not exists
        existing_user = db.users.find_one({"user_id": user_id})
        if not existing_user:
            db.users.insert_one({
                "user_id": user_id,
                "skill_level": "intermediate",
                "preferences": {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        
        # Save conversation
        conv_dict = conversation.dict()
        conv_dict["user_id"] = user_id
        result = db.conversations.insert_one(conv_dict)
        
        return {"saved": True, "conversation_id": str(result.inserted_id)}
        
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
        raise HTTPException(status_code=500, detail="Error saving conversation")

@app.get("/suggest/{user_id}")
@limiter.limit("10/minute")
async def get_suggestions(request: Request, user_id: str):
    """Get coding suggestions for a user"""
    logger.info(f"Suggestions request for user {user_id}")
    
    suggestions = {
        "project_ideas": [],
        "learning_resources": [],
        "tools_and_libraries": [],
        "best_practices": []
    }
    
    # Get user profile and history
    if db:
        user_profile = db.users.find_one({"user_id": user_id})
        recent_conversations = list(db.conversations.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(10))
        
        # Analyze conversation topics
        topics = set()
        for conv in recent_conversations:
            for msg in conv.get("messages", []):
                content = msg.get("content", "").lower()
                if "python" in content:
                    topics.add("python")
                if "javascript" in content or "js" in content:
                    topics.add("javascript")
                if "react" in content:
                    topics.add("react")
                if "api" in content:
                    topics.add("api")
                if "database" in content or "mongodb" in content:
                    topics.add("database")
        
        # Generate personalized suggestions
        if "python" in topics:
            suggestions["project_ideas"].append("Build a REST API with FastAPI")
            suggestions["tools_and_libraries"].append("Try pytest for testing")
            suggestions["learning_resources"].append("Python Design Patterns")
        
        if "javascript" in topics:
            suggestions["project_ideas"].append("Create a real-time chat app with Socket.IO")
            suggestions["tools_and_libraries"].append("Explore TypeScript for type safety")
            suggestions["learning_resources"].append("JavaScript async/await patterns")
        
        if "react" in topics:
            suggestions["project_ideas"].append("Build a task management app with React and Redux")
            suggestions["tools_and_libraries"].append("Check out Next.js for SSR")
            suggestions["learning_resources"].append("React Hooks deep dive")
        
        if "database" in topics:
            suggestions["best_practices"].append("Always create indexes for frequently queried fields")
            suggestions["tools_and_libraries"].append("Use MongoDB Compass for database visualization")
        
        # Add general suggestions
        skill_level = user_profile.get("skill_level", "intermediate") if user_profile else "intermediate"
        
        if skill_level == "beginner":
            suggestions["best_practices"].extend([
                "Always use version control (Git)",
                "Write comments to explain your code",
                "Start with simple projects and gradually increase complexity"
            ])
        elif skill_level == "intermediate":
            suggestions["best_practices"].extend([
                "Focus on clean code principles",
                "Implement proper error handling",
                "Learn about design patterns"
            ])
        else:  # advanced
            suggestions["best_practices"].extend([
                "Optimize for performance and scalability",
                "Implement comprehensive testing",
                "Consider microservices architecture"
            ])
    else:
        # Default suggestions
        suggestions["project_ideas"] = [
            "Build a personal portfolio website",
            "Create a todo list application",
            "Develop a weather app with API integration"
        ]
        suggestions["learning_resources"] = [
            "MDN Web Docs for web development",
            "Python official documentation",
            "freeCodeCamp for hands-on learning"
        ]
        suggestions["tools_and_libraries"] = [
            "VS Code for code editing",
            "Postman for API testing",
            "Git for version control"
        ]
        suggestions["best_practices"] = [
            "Write clean, readable code",
            "Use meaningful variable names",
            "Test your code thoroughly"
        ]
    
    return {
        "user_id": user_id,
        "suggestions": suggestions,
        "generated_at": datetime.utcnow().isoformat()
    }

@app.post("/auth/register")
async def register(user: UserAuth):
    """Register a new user (optional feature)"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Check if user exists
    if db.users.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hash password
    hashed_password = pwd_context.hash(user.password)
    
    # Create user
    user_doc = {
        "username": user.username,
        "user_id": hashlib.md5(user.username.encode()).hexdigest(),
        "hashed_password": hashed_password,
        "skill_level": "intermediate",
        "preferences": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    db.users.insert_one(user_doc)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_doc["user_id"]}

@app.post("/auth/login")
async def login(user: UserAuth):
    """Login endpoint (optional feature)"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Find user
    user_doc = db.users.find_one({"username": user.username})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not pwd_context.verify(user.password, user_doc.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user_id": user_doc["user_id"]}

@app.get("/download/code")
async def download_code(code: str, filename: str = "code.py"):
    """Download generated code as file"""
    try:
        # Create temporary file
        temp_path = f"/tmp/{filename}"
        with open(temp_path, "w") as f:
            f.write(code)
        
        return FileResponse(
            path=temp_path,
            filename=filename,
            media_type="application/octet-stream"
        )
    except Exception as e:
        logger.error(f"Error creating download: {e}")
        raise HTTPException(status_code=500, detail="Error creating file")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )