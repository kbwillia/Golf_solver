# Golf Card Game - Deployment Guide

## Quick Deploy Options for Students

### Option 1: Render (Recommended - Easiest)

1. **Sign up**: Go to [render.com](https://render.com) and create a free account
2. **Connect GitHub**: Link your GitHub account
3. **New Web Service**: Click "New Web Service"
4. **Connect Repository**: Select your golf game repository
5. **Configure**:
   - **Name**: `golf-card-game`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && python web_app.py`
6. **Deploy**: Click "Create Web Service"
7. **Get URL**: Your app will be available at `https://your-app-name.onrender.com`

### Option 2: Railway

1. **Sign up**: Go to [railway.app](https://railway.app) and create account
2. **New Project**: Click "New Project"
3. **Deploy from GitHub**: Select your repository
4. **Auto-deploy**: Railway will automatically detect it's a Python app
5. **Get URL**: Your app will be available at `https://your-app-name.railway.app`

### Option 3: Heroku (Student Plan)

1. **GitHub Student Pack**: Get free credits at [education.github.com](https://education.github.com)
2. **Install Heroku CLI**: Download from [heroku.com](https://heroku.com)
3. **Login**: `heroku login`
4. **Create app**: `heroku create your-golf-game`
5. **Deploy**: `git push heroku main`
6. **Open**: `heroku open`

## Environment Variables

You may need to set these environment variables in your hosting platform:

- `GIPHY_API_KEY` - For GIF functionality
- `TOP_MEDIA` - For text-to-speech
- `ELEVENLABS_API_KEY` - For voice features

## Troubleshooting

### Common Issues:

1. **Port issues**: The app is configured to run on port 5000, but hosting platforms will set their own port via `PORT` environment variable
2. **Static files**: Make sure the frontend/static folder is accessible
3. **Dependencies**: All required packages are in `backend/requirements.txt`

### Local Testing:

```bash
cd backend
pip install -r requirements.txt
python web_app.py
```

Visit `http://localhost:5000` to test locally.

## Sharing Your App here

Once deployed, you'll get a URL like:
- `https://your-golf-game.onrender.com`
- `https://your-golf-game.railway.app`
- `https://your-golf-game.herokuapp.com`

Share this URL with friends and family to test your golf card game!