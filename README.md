# Coding AI Assistant Backend

A production-ready FastAPI backend for an AI-powered coding assistant using the Phi-3.1-mini-4k-instruct model. Features adaptive questioning, code error detection, conversation history, and personalized suggestions.

## Features

- 🤖 **AI-Powered Chat**: Integrates Phi-3.1-mini-4k-instruct model via llama-cpp-python
- 💬 **Adaptive Questioning**: Context-aware follow-up questions based on user needs
- 🔍 **Error Detection**: Automatic syntax checking for Python and JavaScript code
- 📝 **Conversation History**: MongoDB-backed persistent chat history
- 🎯 **Personalized Suggestions**: Tailored coding recommendations based on skill level
- 🔐 **JWT Authentication**: Optional user authentication system
- ⚡ **Rate Limiting**: Protects API from abuse
- 🐳 **Docker Support**: Production-ready containerization
- 🚀 **Render Ready**: Optimized for deployment on Render's free tier

## Tech Stack

- **Framework**: FastAPI
- **Language Model**: Phi-3.1-mini-4k-instruct (GGUF format)
- **Database**: MongoDB Atlas
- **Authentication**: JWT tokens
- **Container**: Docker with Python 3.13-slim
- **Deployment**: Render.com compatible

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and available endpoints |
| `/health` | GET | Health check endpoint |
| `/chat` | POST | Main chat endpoint for AI interactions |
| `/history/{user_id}` | GET | Retrieve user's conversation history |
| `/save/{user_id}` | POST | Save conversation to database |
| `/suggest/{user_id}` | GET | Get personalized coding suggestions |
| `/auth/register` | POST | Register new user (optional) |
| `/auth/login` | POST | User login (optional) |
| `/download/code` | GET | Download generated code as file |

## Local Setup

### Prerequisites

- Python 3.13.4 or higher
- MongoDB (local or Atlas account)
- Git

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd coding-assistant-backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your MongoDB URI and other configurations
```

5. **Run the application**
```bash
python main.py
# Or use uvicorn directly:
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker Setup

### Build and Run

1. **Build the Docker image**
```bash
docker build -t coding-assistant-backend .
```

2. **Run the container**
```bash
docker run -p 8000:8000 \
  -e MONGO_URI="your-mongodb-uri" \
  -e SECRET_KEY="your-secret-key" \
  -e MODEL_PATH="./models/phi-3.1-mini-4k-instruct.gguf" \
  coding-assistant-backend
```

### Docker Compose (Optional)

Create a `docker-compose.yml`:
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=${MONGO_URI}
      - SECRET_KEY=${SECRET_KEY}
      - MODEL_PATH=${MODEL_PATH}
      - PORT=8000
    volumes:
      - ./models:/app/models
```

Run with:
```bash
docker-compose up
```

## MongoDB Atlas Setup

1. **Create a free MongoDB Atlas account** at [mongodb.com](https://www.mongodb.com/cloud/atlas)

2. **Create a new cluster** (free tier available)

3. **Configure network access**:
   - Add your IP address or allow access from anywhere (0.0.0.0/0)

4. **Create database user**:
   - Note the username and password

5. **Get connection string**:
   - Click "Connect" → "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database user password

6. **Update `.env` file**:
```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/coding_assistant?retryWrites=true&w=majority
```

## Render Deployment

### Prerequisites
- GitHub account with repository
- Render account (free tier works)
- MongoDB Atlas database

### Deployment Steps

1. **Push to GitHub**
```bash
git add .
git commit -m "Initial backend setup"
git push origin main
```

2. **Create New Web Service on Render**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Choose the repository

3. **Configure the service**:
   - **Name**: `coding-assistant-backend`
   - **Environment**: `Docker`
   - **Instance Type**: Free
   - **Docker Build Context**: `.`
   - **Dockerfile Path**: `./Dockerfile`

4. **Add Environment Variables**:
   - `MONGO_URI`: Your MongoDB Atlas connection string
   - `SECRET_KEY`: A secure random string
   - `MODEL_PATH`: `./models/phi-3.1-mini-4k-instruct.gguf`
   - `PORT`: Leave empty (Render sets this automatically)

5. **Deploy**:
   - Click "Create Web Service"
   - Wait for the build and deployment to complete
   - Your API will be available at `https://your-service.onrender.com`

### Auto-Deploy Setup

Render automatically deploys when you push to the connected GitHub branch. To ensure smooth deployments:

1. **Test locally** before pushing
2. **Monitor logs** in Render dashboard
3. **Check health endpoint** after deployment: `https://your-service.onrender.com/health`

## Usage Examples

### Chat Request
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I create a REST API in Python?",
    "skill_level": "intermediate",
    "preferences": {
      "languages": ["Python"],
      "frameworks": ["FastAPI"]
    }
  }'
```

### Get Conversation History
```bash
curl "http://localhost:8000/history/user123"
```

### Get Suggestions
```bash
curl "http://localhost:8000/suggest/user123"
```

### Health Check
```bash
curl "http://localhost:8000/health"
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017/` | Yes |
| `MODEL_PATH` | Path to Phi-3.1 model | `./models/phi-3.1-mini-4k-instruct.gguf` | Yes |
| `SECRET_KEY` | JWT secret key | Random string | Yes |
| `PORT` | Server port | `8000` | No |

### Model Configuration

The application uses the Phi-3.1-mini-4k-instruct model in GGUF format for optimal performance on limited resources:

- **Model size**: ~2GB (Q4_K_M quantization)
- **Memory usage**: ~400MB when loaded
- **Context window**: 4096 tokens
- **Automatic download**: If model file is not present, it downloads automatically on startup

### Rate Limiting

Default rate limits:
- `/chat`: 30 requests/minute
- `/history`: 10 requests/minute
- `/save`: 20 requests/minute
- `/suggest`: 10 requests/minute

## Monitoring

### Health Endpoint

The `/health` endpoint returns:
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00",
  "model_loaded": true,
  "database_connected": true
}
```

### Logs

- Application logs are written to `app.log` and stdout
- Docker logs: `docker logs <container-id>`
- Render logs: Available in Render dashboard

## Troubleshooting

### Common Issues

1. **Model not loading**:
   - Ensure sufficient memory (minimum 512MB)
   - Check MODEL_PATH environment variable
   - Model downloads automatically if not present

2. **MongoDB connection failed**:
   - Verify MONGO_URI is correct
   - Check network access settings in MongoDB Atlas
   - Ensure IP is whitelisted

3. **Out of memory on Render**:
   - The app is optimized for 512MB RAM
   - Uses quantized model (Q4_K_M) for lower memory usage
   - Falls back to mock responses if model can't load

4. **Slow initial response**:
   - First request may be slow due to model loading
   - Subsequent requests will be faster

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Format code
black .

# Lint
pylint main.py

# Type checking
mypy main.py
```

## Security Considerations

- **JWT tokens** expire after 30 minutes
- **Rate limiting** prevents abuse
- **Input validation** on all endpoints
- **MongoDB injection** protection via PyMongo
- **CORS** configured for production use
- **Environment variables** for sensitive data
- **Non-root Docker user** for security

## Performance Optimization

- **Model quantization**: Uses Q4_K_M for 75% size reduction
- **Lazy loading**: Model loads only when needed
- **Connection pooling**: MongoDB client reuse
- **Response caching**: In-memory cache for frequent requests
- **Async operations**: Non-blocking I/O throughout

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or suggestions:
1. Check the [Issues](https://github.com/your-username/your-repo/issues) page
2. Create a new issue with detailed information
3. Include logs and error messages

## Acknowledgments

- Phi-3.1 model by Microsoft
- FastAPI framework
- MongoDB Atlas for database hosting
- Render.com for deployment platform