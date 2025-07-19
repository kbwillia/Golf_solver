# Golf Card Game

A full-stack web application for playing the Golf card game with AI opponents and interactive chatbot commentary.

## Project Structure

```
Golf/
├── frontend/              # Frontend files (HTML, CSS, JS)
│   ├── static/           # Static assets (CSS, JS, images)
│   │   ├── css/         # Stylesheets
│   │   ├── js/          # JavaScript files
│   │   └── images/      # Image assets
│   ├── templates/       # HTML templates
│   └── test_chatbot_simple.html
├── backend/              # Backend files (Python Flask)
│   ├── web_app.py       # Main Flask application
│   ├── game.py          # Game logic
│   ├── chatbot.py       # Chatbot functionality
│   ├── bot_personalities.py  # Bot personality definitions
│   ├── agents.py        # AI agent implementations
│   ├── requirements.txt # Python dependencies
│   └── run_app.py       # Script to run the application
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Golf
   ```

2. **Set up the backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   cd backend
   python run_app.py
   ```

4. **Access the game**
   Open your browser and go to: http://localhost:5000

## Features

- **Golf Card Game**: Play the classic Golf card game
- **AI Opponents**: Multiple AI difficulty levels
- **Interactive Chatbot**: Jim Nantz commentary and other bot personalities
- **Voice System**: Text-to-speech for bot commentary
- **Custom Bots**: Create your own bot personalities
- **Real-time Updates**: Live game state updates

## Development

### Backend Development
- All Python files are in the `backend/` directory
- Main application: `backend/web_app.py`
- Run with: `cd backend && python run_app.py`

### Frontend Development
- All frontend files are in the `frontend/` directory
- Templates: `frontend/templates/`
- Static assets: `frontend/static/`

## API Endpoints

- `GET /` - Main game interface
- `POST /create_game` - Create a new game
- `POST /make_move` - Make a game move
- `POST /chatbot/send_message` - Send chat message
- `POST /chatbot/get_bot_response` - Get bot response
- `POST /chatbot/proactive_comment` - Get proactive bot comments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request


Golf/
├── frontend/                    # React/Vue.js frontend
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   │   ├── Game/
│   │   │   │   ├── GameBoard.jsx
│   │   │   │   ├── PlayerGrid.jsx
│   │   │   │   ├── Card.jsx
│   │   │   │   └── GameControls.jsx
│   │   │   ├── Chat/
│   │   │   │   ├── ChatPanel.jsx
│   │   │   │   ├── BotMessage.jsx
│   │   │   │   └── VoiceSystem.jsx
│   │   │   ├── Setup/
│   │   │   │   ├── GameSetup.jsx
│   │   │   │   └── CustomBotCreator.jsx
│   │   │   └── Common/
│   │   │       ├── Button.jsx
│   │   │       ├── Modal.jsx
│   │   │       └── Loading.jsx
│   │   ├── services/           # API calls and external services
│   │   │   ├── api/
│   │   │   │   ├── gameApi.js
│   │   │   │   ├── chatApi.js
│   │   │   │   └── botApi.js
│   │   │   ├── voice/
│   │   │   │   ├── browserTTS.js
│   │   │   │   └── elevenLabsTTS.js
│   │   │   └── websocket/
│   │   │       └── gameSocket.js
│   │   ├── hooks/              # Custom React hooks
│   │   │   ├── useGameState.js
│   │   │   ├── useVoiceSystem.js
│   │   │   └── useChatbot.js
│   │   ├── store/              # State management (Redux/Zustand)
│   │   │   ├── gameSlice.js
│   │   │   ├── chatSlice.js
│   │   │   └── settingsSlice.js
│   │   ├── utils/              # Helper functions
│   │   │   ├── gameLogic.js
│   │   │   ├── cardUtils.js
│   │   │   └── constants.js
│   │   └── styles/             # CSS/SCSS files
│   │       ├── components/
│   │       └── global.css
│   ├── public/
│   └── package.json
├── backend/                     # Python Flask/FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── game_routes.py
│   │   │   ├── chat_routes.py
│   │   │   ├── bot_routes.py
│   │   │   └── tts_routes.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── game.py
│   │   │   ├── player.py
│   │   │   └── bot.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── game_service.py
│   │   │   ├── ai_service.py
│   │   │   ├── chat_service.py
│   │   │   └── tts_service.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── game_utils.py
│   │   │   └── validators.py
│   │   └── config/
│   │       ├── __init__.py
│   │       └── settings.py
│   ├── tests/
│   │   ├── test_game.py
│   │   ├── test_chat.py
│   │   └── test_bots.py
│   ├── requirements.txt
│   └── main.py
├── shared/                      # Shared code between frontend/backend
│   ├── types/
│   │   ├── game.types.ts
│   │   └── bot.types.ts
│   └── constants/
│       └── game.constants.ts
├── docs/                        # Documentation
│   ├── api.md
│   ├── architecture.md
│   └── deployment.md
├── docker/                      # Docker configuration
│   ├── Dockerfile.frontend
│   ├── Dockerfile.backend
│   └── docker-compose.yml
├── scripts/                     # Build/deployment scripts
│   ├── build.sh
│   ├── deploy.sh
│   └── setup.sh
└── README.md


cd backend && python run_app.py