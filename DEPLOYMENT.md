# Deployment Guide for Coding AI Assistant Backend

## 📋 Prerequisites

1. **GitHub Account** with this repository
2. **MongoDB Atlas Account** (free tier)
3. **Render Account** (free tier)

## 🚀 Quick Deploy to Render

### Step 1: MongoDB Atlas Setup

1. **Create Account**: Go to [mongodb.com](https://www.mongodb.com/cloud/atlas)
2. **Create Free Cluster**:
   - Choose AWS/GCP/Azure
   - Select closest region
   - Choose M0 Sandbox (free tier)
3. **Security Setup**:
   - Go to "Network Access" → Add IP Address → Allow from Anywhere (0.0.0.0/0)
   - Go to "Database Access" → Add New Database User
   - Username: `codingai`
   - Password: Generate secure password (save it!)
4. **Get Connection String**:
   - Click "Connect" → "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database password
   - Example: `mongodb+srv://codingai:YourPassword@cluster.mongodb.net/coding_assistant?retryWrites=true&w=majority`

### Step 2: Deploy to Render

1. **Fork/Use This Repository**
   - Repository is at: https://github.com/BattleZone-Esport/URESHII-PARTNER-BACKEND

2. **Create Render Account**: 
   - Sign up at [render.com](https://render.com)
   - Connect your GitHub account

3. **Create New Web Service**:
   - Click "New +" → "Web Service"
   - Select this repository
   - Configure:
     ```
     Name: coding-ai-backend
     Environment: Docker
     Region: Choose closest to you
     Branch: main
     Root Directory: (leave empty)
     Docker Build Context Path: .
     Dockerfile Path: ./Dockerfile
     Instance Type: Free
     ```

4. **Add Environment Variables**:
   - Click "Advanced" → "Add Environment Variable"
   - Add these variables:
     ```
     MONGO_URI = [Your MongoDB Atlas connection string]
     SECRET_KEY = [Generate random 32-char string]
     MODEL_PATH = ./models/phi-3.1-mini-4k-instruct.gguf
     ```
   - Leave PORT empty (Render sets it automatically)

5. **Deploy**:
   - Click "Create Web Service"
   - Wait 10-15 minutes for initial build and deployment
   - Your API will be at: `https://your-app-name.onrender.com`

### Step 3: Verify Deployment

1. **Check Health**: Visit `https://your-app-name.onrender.com/health`
2. **View API Docs**: Visit `https://your-app-name.onrender.com/docs`
3. **Monitor Logs**: Check Render dashboard for logs

## 🐳 Docker Deployment (Alternative)

### Local Docker Testing

```bash
# Build image
docker build -t coding-ai-backend .

# Run container
docker run -p 8000:8000 \
  -e MONGO_URI="your-mongodb-uri" \
  -e SECRET_KEY="your-secret-key" \
  coding-ai-backend

# Access at http://localhost:8000
```

### Docker Compose

```bash
# Copy .env.example to .env and configure
cp .env.example .env
nano .env  # Edit with your values

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## ☁️ Other Deployment Options

### Railway.app

1. Connect GitHub repo
2. Add environment variables
3. Deploy (automatic from Dockerfile)

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Launch app
flyctl launch

# Set secrets
flyctl secrets set MONGO_URI="your-uri"
flyctl secrets set SECRET_KEY="your-key"

# Deploy
flyctl deploy
```

### Heroku

1. Create `Procfile`:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
2. Deploy via Heroku CLI or GitHub integration

### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT-ID/coding-ai-backend

# Deploy
gcloud run deploy --image gcr.io/PROJECT-ID/coding-ai-backend \
  --platform managed \
  --set-env-vars MONGO_URI="your-uri",SECRET_KEY="your-key"
```

## 🔧 Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | `mongodb+srv://...` |
| `SECRET_KEY` | JWT secret key (32+ chars) | `use-a-random-string-here` |
| `MODEL_PATH` | Path to AI model | `./models/phi-3.1-mini-4k-instruct.gguf` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CORS_ORIGINS` | Allowed origins | `*` |
| `ENABLE_AUTH` | Enable authentication | `true` |
| `ENABLE_RATE_LIMITING` | Enable rate limiting | `true` |

## 🔍 Monitoring & Troubleshooting

### Health Checks

- **Endpoint**: `/health`
- **Expected Response**: 
  ```json
  {
    "status": "ok",
    "model_loaded": true,
    "database_connected": true
  }
  ```

### Common Issues & Solutions

#### 1. Out of Memory (Render)
- **Symptom**: Service crashes after startup
- **Solution**: The app auto-falls back to mock responses if model can't load
- **Note**: Free tier has 512MB RAM limit

#### 2. MongoDB Connection Failed
- **Symptom**: `database_connected: false` in health check
- **Solutions**:
  - Verify MongoDB URI is correct
  - Check IP whitelist (should be 0.0.0.0/0)
  - Ensure database user password is correct

#### 3. Slow Initial Response
- **Symptom**: First request takes 30+ seconds
- **Cause**: Model loading on first request
- **Solution**: Normal behavior, subsequent requests will be fast

#### 4. Rate Limit Errors
- **Symptom**: 429 Too Many Requests
- **Solution**: Default is 30 req/min for chat, wait or adjust limits

### Performance Optimization

1. **Model Loading**: Model downloads and loads on first startup
2. **Cold Starts**: Free tier services may sleep after 15 min inactivity
3. **Response Time**: First response ~5-10s, subsequent ~1-2s
4. **Memory Usage**: Optimized to stay under 400MB

## 📊 API Testing

### Using curl

```bash
# Health check
curl https://your-app.onrender.com/health

# Chat endpoint
curl -X POST https://your-app.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How to create a Python API?", "skill_level": "intermediate"}'

# Get suggestions
curl https://your-app.onrender.com/suggest/test_user
```

### Using Postman

1. Import the API endpoints
2. Set base URL to your deployment
3. Test each endpoint

### Using the test script

```bash
# Update BASE_URL in test_api.py
python test_api.py
```

## 🔐 Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Use strong MongoDB password
- [ ] Enable HTTPS (automatic on Render)
- [ ] Set CORS origins for production
- [ ] Review rate limits
- [ ] Monitor logs regularly
- [ ] Keep dependencies updated

## 📈 Scaling Guide

### When to Scale

- Response time > 5 seconds consistently
- Memory usage > 450MB
- Request rate > 100 req/min

### Scaling Options

1. **Render Paid Tier**: More RAM, always-on service
2. **Multiple Instances**: Load balancing
3. **Caching Layer**: Redis for responses
4. **CDN**: For static assets
5. **Database Scaling**: MongoDB Atlas M10+

## 🆘 Support

- **Issues**: Open issue on GitHub
- **Logs**: Check Render dashboard
- **API Docs**: `/docs` endpoint
- **Health**: `/health` endpoint

## 📝 Notes

- Free tier services may sleep after inactivity
- Initial model download takes ~2-3 minutes
- MongoDB Atlas free tier: 512MB storage
- Render free tier: 512MB RAM, 750 hours/month