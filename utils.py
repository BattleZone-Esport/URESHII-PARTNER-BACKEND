"""
Utility functions for the Coding AI Assistant
"""

import re
import ast
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzes code for syntax errors and improvements"""
    
    @staticmethod
    def check_python_syntax(code: str) -> Dict[str, Any]:
        """
        Check Python code for syntax errors and potential issues
        
        Args:
            code: Python code string to analyze
            
        Returns:
            Dictionary with analysis results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check for syntax errors
        try:
            tree = ast.parse(code)
            results["ast_valid"] = True
        except SyntaxError as e:
            results["valid"] = False
            results["errors"].append({
                "line": e.lineno,
                "column": e.offset,
                "message": e.msg,
                "type": "SyntaxError"
            })
            return results
        except Exception as e:
            results["valid"] = False
            results["errors"].append({
                "message": str(e),
                "type": "ParseError"
            })
            return results
        
        # Analyze the AST
        analyzer = PythonASTAnalyzer()
        analyzer.visit(tree)
        
        # Add analysis results
        results["warnings"].extend(analyzer.warnings)
        results["suggestions"].extend(analyzer.suggestions)
        
        # Check for common issues
        if not analyzer.has_main_guard and analyzer.has_executable_code:
            results["suggestions"].append(
                "Consider adding 'if __name__ == \"__main__\":' guard for executable code"
            )
        
        if analyzer.missing_imports:
            for imp in analyzer.missing_imports:
                results["warnings"].append(f"Potentially missing import: {imp}")
        
        return results
    
    @staticmethod
    def check_javascript_syntax(code: str) -> Dict[str, Any]:
        """
        Basic JavaScript syntax checking
        
        Args:
            code: JavaScript code string to analyze
            
        Returns:
            Dictionary with analysis results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check for balanced brackets
        brackets = {'{': '}', '[': ']', '(': ')'}
        stack = []
        
        for i, char in enumerate(code):
            if char in brackets:
                stack.append((char, i))
            elif char in brackets.values():
                if not stack:
                    results["valid"] = False
                    results["errors"].append({
                        "position": i,
                        "message": f"Unmatched closing bracket '{char}'",
                        "type": "BracketError"
                    })
                else:
                    opening, pos = stack.pop()
                    if brackets[opening] != char:
                        results["valid"] = False
                        results["errors"].append({
                            "position": i,
                            "message": f"Mismatched brackets: '{opening}' at position {pos} and '{char}' at position {i}",
                            "type": "BracketError"
                        })
        
        if stack:
            results["valid"] = False
            for bracket, pos in stack:
                results["errors"].append({
                    "position": pos,
                    "message": f"Unclosed bracket '{bracket}'",
                    "type": "BracketError"
                })
        
        # Check for common patterns
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for console.log in production code
            if 'console.log' in line and '// debug' not in line.lower():
                results["warnings"].append({
                    "line": i,
                    "message": "console.log found - consider removing for production",
                    "type": "DebugCode"
                })
            
            # Check for var usage (suggest let/const)
            if re.search(r'\bvar\s+', line):
                results["suggestions"].append({
                    "line": i,
                    "message": "Consider using 'let' or 'const' instead of 'var'",
                    "type": "ModernJS"
                })
        
        return results
    
    @staticmethod
    def extract_imports(code: str, language: str = "python") -> List[str]:
        """Extract import statements from code"""
        imports = []
        
        if language == "python":
            pattern = r'(?:from\s+(\S+)\s+)?import\s+(.+)'
            matches = re.findall(pattern, code)
            for from_module, import_names in matches:
                if from_module:
                    imports.append(from_module)
                else:
                    # Handle comma-separated imports
                    for name in import_names.split(','):
                        imports.append(name.strip().split()[0])
        
        elif language in ["javascript", "js", "typescript", "ts"]:
            # ES6 imports
            pattern = r'import\s+(?:{[^}]+}|\S+)\s+from\s+[\'"]([^\'\"]+)[\'"]'
            matches = re.findall(pattern, code)
            imports.extend(matches)
            
            # CommonJS requires
            pattern = r'(?:const|let|var)\s+\S+\s*=\s*require\([\'"]([^\'\"]+)[\'"]\)'
            matches = re.findall(pattern, code)
            imports.extend(matches)
        
        return imports


class PythonASTAnalyzer(ast.NodeVisitor):
    """AST visitor for Python code analysis"""
    
    def __init__(self):
        self.warnings = []
        self.suggestions = []
        self.imports = set()
        self.defined_names = set()
        self.used_names = set()
        self.has_main_guard = False
        self.has_executable_code = False
        self.missing_imports = set()
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        self.defined_names.add(node.name)
        
        # Check for missing docstring
        if not ast.get_docstring(node):
            self.suggestions.append({
                "line": node.lineno,
                "message": f"Function '{node.name}' lacks a docstring",
                "type": "Documentation"
            })
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.defined_names.add(node.name)
        
        # Check for missing docstring
        if not ast.get_docstring(node):
            self.suggestions.append({
                "line": node.lineno,
                "message": f"Class '{node.name}' lacks a docstring",
                "type": "Documentation"
            })
        
        self.generic_visit(node)
    
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        self.generic_visit(node)
    
    def visit_If(self, node):
        # Check for main guard
        if isinstance(node.test, ast.Compare):
            if isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__":
                if any(isinstance(op, ast.Eq) for op in node.test.ops):
                    if any(isinstance(comp, ast.Constant) and comp.value == "__main__" 
                           for comp in node.test.comparators):
                        self.has_main_guard = True
        self.generic_visit(node)
    
    def visit_Expr(self, node):
        # Check for executable code at module level
        if isinstance(node.value, ast.Call):
            self.has_executable_code = True
        self.generic_visit(node)


class ConversationManager:
    """Manages conversation context and history"""
    
    @staticmethod
    def create_session_id(user_id: str) -> str:
        """Create a unique session ID"""
        timestamp = datetime.utcnow().isoformat()
        raw = f"{user_id}{timestamp}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    @staticmethod
    def format_conversation(messages: List[Dict[str, Any]]) -> str:
        """Format conversation history for context"""
        formatted = []
        for msg in messages[-10:]:  # Last 10 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role.capitalize()}: {content}")
        return "\n".join(formatted)
    
    @staticmethod
    def extract_code_context(message: str) -> Dict[str, Any]:
        """Extract code context from message"""
        context = {
            "has_code": False,
            "languages": [],
            "frameworks": [],
            "concepts": []
        }
        
        # Check for code blocks
        code_pattern = r'```(\w+)?'
        matches = re.findall(code_pattern, message)
        if matches:
            context["has_code"] = True
            context["languages"].extend([m for m in matches if m])
        
        # Check for language mentions
        languages = ["python", "javascript", "typescript", "java", "c++", "rust", "go"]
        for lang in languages:
            if lang in message.lower():
                context["languages"].append(lang)
        
        # Check for framework mentions
        frameworks = ["react", "vue", "angular", "django", "flask", "fastapi", "express", "nextjs"]
        for fw in frameworks:
            if fw in message.lower():
                context["frameworks"].append(fw)
        
        # Check for concept mentions
        concepts = ["api", "database", "authentication", "deployment", "testing", "docker", "ci/cd"]
        for concept in concepts:
            if concept in message.lower():
                context["concepts"].append(concept)
        
        # Remove duplicates
        context["languages"] = list(set(context["languages"]))
        context["frameworks"] = list(set(context["frameworks"]))
        context["concepts"] = list(set(context["concepts"]))
        
        return context


class ProjectTemplates:
    """Project scaffolding templates"""
    
    @staticmethod
    def get_python_api_template() -> Dict[str, str]:
        """Get Python FastAPI project template"""
        return {
            "main.py": """from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
""",
            "requirements.txt": """fastapi==0.100.0
uvicorn[standard]==0.23.0
""",
            "README.md": """# FastAPI Project

## Installation
```bash
pip install -r requirements.txt
```

## Run
```bash
uvicorn main:app --reload
```
"""
        }
    
    @staticmethod
    def get_react_app_template() -> Dict[str, str]:
        """Get React app project template"""
        return {
            "package.json": """{
  "name": "react-app",
  "version": "1.0.0",
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  }
}""",
            "src/App.js": """import React from 'react';

function App() {
  return (
    <div className="App">
      <h1>Welcome to React</h1>
    </div>
  );
}

export default App;
""",
            "src/index.js": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""
        }


def generate_suggestions_for_skill_level(skill_level: str) -> List[str]:
    """Generate suggestions based on skill level"""
    suggestions = {
        "beginner": [
            "Start with simple projects and gradually increase complexity",
            "Focus on understanding basic concepts before moving to advanced topics",
            "Practice writing clean, readable code with meaningful variable names",
            "Use version control (Git) from the beginning",
            "Don't be afraid to ask questions and seek help"
        ],
        "intermediate": [
            "Learn about design patterns and best practices",
            "Implement comprehensive error handling in your code",
            "Write unit tests for your functions",
            "Explore asynchronous programming concepts",
            "Consider contributing to open source projects"
        ],
        "advanced": [
            "Focus on system design and architecture",
            "Optimize for performance and scalability",
            "Implement CI/CD pipelines for your projects",
            "Explore microservices and distributed systems",
            "Mentor others and share your knowledge"
        ]
    }
    
    return suggestions.get(skill_level, suggestions["intermediate"])