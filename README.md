# Golf Card Game

A full-stack web application for playing the Golf card game with AI opponents and interactive chatbot commentary featuring Jim Nantz-style voice commentary.

## Project Structure

```
Golf/
├── frontend/                    # Frontend files (HTML, CSS, JS)
│   ├── static/                 # Static assets
│   │   ├── css/               # Stylesheets
│   │   │   ├── layout.css     # Main layout styles
│   │   │   ├── cards.css      # Card display styles
│   │   │   ├── players.css    # Player grid styles
│   │   │   ├── game-controls.css # Game control styles
│   │   │   ├── notification.css # Notification styles
│   │   │   ├── probabilities.css # Probability panel styles
│   │   │   └── chatbot.css    # Chat interface styles
│   │   ├── js/                # Modularized JavaScript files
│   │   │   ├── game-core.js   # Core game logic and state management
│   │   │   ├── game-ui.js     # UI updates and display functions
│   │   │   ├── chatbot.js     # Chatbot functionality and bot interactions
│   │   │   ├── voice.js       # Voice system and TTS integration
│   │   │   ├── probabilities.js # Probability calculations and charts
│   │   │   ├── golf.js        # Game actions and card interactions
│   │   │   └── golf-organized.js # Legacy organized file (not loaded)
│   │   ├── sounds/            # Audio files
│   │   ├── cards/             # Card images
│   │   ├── edited_cards/      # Custom card images
│   │   └── masters_images/    # Tournament images
│   ├── templates/             # HTML templates
│   │   └── index.html         # Main game interface
│   └── test_chatbot_simple.html # Test file
├── backend/                    # Backend files (Python Flask)
│   ├── web_app.py             # Main Flask application
│   ├── game.py                # Game logic and rules
│   ├── chatbot.py             # Chatbot functionality
│   ├── agents.py              # AI agent implementations
│   ├── requirements.txt       # Python dependencies
│   └── run_app.py             # Script to run the application
├── RL/                        # Reinforcement Learning components
├── create/                    # Additional creation tools
├── venv/                      # Python virtual environment
├── .gitignore                 # Git ignore rules
├── game_rules.txt             # Game rules documentation
├── rules_gameplay.txt         # Detailed gameplay rules
├── celebration_gifs.json      # Celebration GIF data
├── voices_list.csv            # Available voice options
└── README.md                  # This file
```

## Quick Start

### Prerequisites
- Python 3.8+
- pip
- Modern web browser

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

### Core Game Features
- **Golf Card Game**: Play the classic Golf card game with 1v1 or 1v3 modes
- **Multiple AI Opponents**: Choose from different difficulty levels (Easy, Medium, Hard)
- **Custom Bot Creation**: Create your own AI bot personalities with custom names and descriptions
- **Multi-game Matches**: Play 1, 3, 6, 9, or 18 holes
- **Real-time Game State**: Live updates and visual feedback

### Interactive Features
- **Jim Nantz Commentary**: Professional golf commentary with voice synthesis
- **Interactive Chatbot**: Chat with Golf Bro, Golf Pro, and other bots
- **GIF Integration**: Send and receive GIFs in chat
- **Voice System**: Text-to-speech for bot responses and commentary
- **Proactive Comments**: Bots provide commentary during gameplay

### UI/UX Features
- **Modern Responsive Design**: Works on desktop and mobile
- **Drag & Drop Interface**: Intuitive card manipulation
- **Probability Panel**: Real-time card probability calculations
- **Action History**: Track game moves and decisions
- **Celebration Animations**: Visual feedback for wins and achievements

## JavaScript Architecture

The frontend uses a modular JavaScript architecture with clear separation of concerns:

### Core Modules
- **`game-core.js`**: Game state management, API calls, and core game functions
- **`game-ui.js`**: UI updates, display functions, and visual feedback
- **`chatbot.js`**: Chat functionality, bot interactions, and message handling
- **`voice.js`**: Voice system integration and TTS functionality
- **`probabilities.js`**: Probability calculations and chart management
- **`golf.js`**: Game actions, card interactions, and event handling

### Key Features
- **Modular Design**: Each module has a specific responsibility
- **Global Exports**: Functions are exported to `window` for cross-module access
- **Error Handling**: Comprehensive error handling and debugging
- **Event-Driven**: Responsive event handling for user interactions

## API Endpoints

### Game Management
- `GET /` - Main game interface
- `POST /create_game` - Create a new game
- `GET /game_state/{game_id}` - Get current game state
- `POST /make_move` - Make a game move

### Chatbot & AI
- `POST /chatbot/send_message` - Send chat message to bots
- `POST /chatbot/get_bot_response` - Get individual bot response
- `POST /chatbot/proactive_comment` - Get proactive bot comments

### Voice & Media
- `POST /gif/search` - Search for GIFs
- Voice system integration with browser TTS and ElevenLabs

## Development

### Backend Development
- **Main Application**: `backend/web_app.py`
- **Game Logic**: `backend/game.py`
- **AI Agents**: `backend/agents.py`
- **Chatbot**: `backend/chatbot.py`
- **Run**: `cd backend && python run_app.py`

### Frontend Development
- **Main Template**: `frontend/templates/index.html`
- **JavaScript Modules**: `frontend/static/js/`
- **Styles**: `frontend/static/css/`
- **Assets**: `frontend/static/` (images, sounds, etc.)

### Recent Improvements
- **Modularized JavaScript**: Separated concerns into focused modules
- **Fixed Variable Conflicts**: Resolved duplicate variable declarations
- **Enhanced Error Handling**: Added comprehensive debugging and error recovery
- **Improved Chat System**: Better event handling and message processing
- **GIF Integration**: Robust GIF search and display functionality

## Troubleshooting

### Common Issues
1. **JavaScript Errors**: Check browser console for module loading issues
2. **Chat Not Working**: Ensure chatbot.js is properly initialized
3. **Voice Issues**: Check browser TTS permissions and voice availability
4. **Game State**: Verify backend is running and accessible

### Debug Mode
The application includes comprehensive console logging for debugging:
- Game state changes
- Chat interactions
- Voice system events
- Error handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (check console for errors)
5. Submit a pull request

## License

[Add your license information here]