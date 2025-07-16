// ===== GOLF GAME VARIABLES =====
let currentGameState = null; // Holds the current game state from backend
let gameId = null; // Unique game session ID
let drawnCard = null; // Card drawn from deck
let currentAction = null; // Current action type
let dragActive = false; // Drag state for discard
let draggedDiscardCard = null; // Card being dragged from discard
let drawnCardData = null; // Data for the currently drawn card
let drawnCardDragActive = false; // Drag state for drawn card
let lastGameSetupReset = 0; // Track which game we last reset the setup for
let turnAnimateTimeout = null; // Timeout for turn animation
let lastTurnIndex = null; // Last turn index to detect turn changes
let setupHideTimeout = null; // Timeout for hiding setup cards
let setupCardsHidden = false; // Whether setup cards are hidden
let setupViewInterval = null; // Interval for setup view timer
let cardVisibilityDuration = 1.5; // Default duration, updated from user input
const SNAP_THRESHOLD = 30; // pixels
let isMyTurn = false;
let actionInProgress = false; // Prevents multiple simultaneous actions
let pollingPaused = false; // Used to pause polling during actions
let isDrawingFromDeck = false; // Track if deck is being drawn from for fade effect
let previousGameState = null;
let aiTurnInProgress = false; // Prevents multiple concurrent AI turn polling
let humanDiscardPosition = null; // Track position for human discard animation
let humanDiscardAction = null; // Track action type for human discard animation
let humanDrawnCardPosition = null; // Track position for drawn card replacement animation
let previousActionHistory = []; // Place this at the top of your JS file
let previousHumanPairs = [];
let previousActionHistoryLength = 0;

// ===== CHATBOT VARIABLES =====
let chatbotEnabled = true;
let currentPersonality = 'Jim Nantz';

let lastNantzCommentTime = 0; // Place this at the top of your JS file if not already present
let lastNantzTurn = null;
let proactiveCommentTimeout = null;

let proactiveCommentInterval = null;

console.log('🎯 Golf.js loaded successfully!');

// Custom HTML legend plugin for Chart.js
const htmlLegendPlugin = {
  id: 'htmlLegend',
  afterUpdate(chart, args, options) {
    const legendContainer = document.getElementById('customLegend');
    if (!legendContainer) return;
    const items = chart.options.plugins.legend.labels.generateLabels(chart);
    legendContainer.innerHTML = items.map(item => `
      <div class="legend-item-box">
        <span class="legend-color-box" style="background:${item.fillStyle};"></span>
        <span>${item.text}</span>
      </div>
    `).join('');
  }
};

// Function to create card display content (SVG or fallback text)
function getCardDisplayContent(card, faceDown = false) {
    if (faceDown || !card) {
        return ''; // Empty content for face-down cards - CSS handles the back design
    }

    // Map card values to file names
    const rankMap = {
        'A': 'A', '2': '2', '3': '3', '4': '4', '5': '5',
        '6': '6', '7': '7', '8': '8', '9': '9', '10': 'T',
        'J': 'J', 'Q': 'Q', 'K': 'K'
    };

    const suitMap = {
        '♠': 'S', '♥': 'H', '♦': 'D', '♣': 'C',
        'S': 'S', 'H': 'H', 'D': 'D', 'C': 'C',
        'spades': 'S', 'hearts': 'H', 'diamonds': 'D', 'clubs': 'C'
    };

    const rank = rankMap[card.rank] || card.rank;
    const suit = suitMap[card.suit] || card.suit;
    const filename = `${rank}${suit}.svg`;
    const cardPath = `/static/edited_cards/${filename}`; //where front of cards is loaded.
    // const cardPath = `/static/cards/${filename}`; //where front of cards is loaded.

    // Return an SVG image element
    return `<svg viewBox="0 0 240 336" width="100%" height="100%" style="display: block;">
        <image href="${cardPath}" width="240" height="336" x="0" y="0" />
    </svg>`;
}

// Celebration GIFs for human win (now loaded from JSON)
let celebrationGifs = [];
fetch('/static/golf_celebration_gifs.json')
    .then(response => response.json())
    .then(data => {
        if (data && data.data) {
            celebrationGifs = data.data
                .map(gif => {
                    if (gif.images && gif.images.downsized_large && gif.images.downsized_large.url) {
                        const url = gif.images.downsized_large.url;
                        // Clean the URL by removing tracking parameters
                        return url.split('?')[0];
                    }
                    return null;
                })
                .filter(Boolean);
        }
    });

// Hurry up timer for slow play
let hurryUpTimer = null;
const HURRY_UP_DELAY = 150000; // 150 seconds
let lastHurryUpGifIndex = -1; // Track last shown GIF to avoid repeats
const hurryUpGifs = [
    "https://media.giphy.com/media/3oriNYQX2lC6dfW2cK/giphy.gif", // Hurry up
    "https://media.giphy.com/media/TqiwHbFBaZ4ti/giphy.gif", // Time's up
    "https://media.giphy.com/media/l0HlPystfePnAI3G8/giphy.gif", // Waiting
    "https://media.giphy.com/media/26tPplGWjN0xLybiU/giphy.gif" ,// Tap tap tap
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3cXh4bnI2YjNzcDR2azZ0cmt0M2FxOGJqdWxibmg1OHlxOGpoMDhkbSZlcD12MV9naWZzX3JlbGF0ZWQmY3Q9Zw/M2EazvA5Fyu8U/giphy.gif" // well we're waiting
];

function startHurryUpTimer() {
    // Only start a new timer if one isn't already running
    if (hurryUpTimer) {
        return; // Timer already running, don't restart it
    }

    hurryUpTimer = setTimeout(() => {
        showHurryUpGif();
    }, HURRY_UP_DELAY);
}

function clearHurryUpTimer() {
    if (hurryUpTimer) {
        clearTimeout(hurryUpTimer);
        hurryUpTimer = null;
    }
}

function showHurryUpGif() {
    const celebrationContainer = document.getElementById('celebrationGif');
    if (celebrationContainer && hurryUpGifs.length > 0) {
        // Select a random GIF, but avoid the last one shown
        let randomIndex;
        do {
            randomIndex = Math.floor(Math.random() * hurryUpGifs.length);
        } while (randomIndex === lastHurryUpGifIndex && hurryUpGifs.length > 1);

        lastHurryUpGifIndex = randomIndex;
        const randomGif = hurryUpGifs[randomIndex];

        console.log('⏰ Showing hurry up GIF:', randomIndex, randomGif);

        celebrationContainer.innerHTML = `
            <div class="celebration-gif-container">
                <img src="${randomGif}" alt="Hurry Up!" class="celebration-gif-img" onerror="console.error('Failed to load hurry up GIF:', this.src);" />
                <div style="text-align: center; margin-top: 10px; color: #ff6b6b; font-weight: bold; font-size: 1.2em;">
                    Let's pick up the pace of play!
                </div>
            </div>
        `;
    }
}

// Helper function to clear celebrations and reset header
function clearCelebration() {
    const celebrationContainer = document.getElementById('celebrationGif');
    const headerTitle = document.querySelector('.header h1');
    const youWonMessage = document.getElementById('youWonHeaderMessage');

    if (celebrationContainer) {
        celebrationContainer.innerHTML = '';
    }

    // Remove the You Won message from header
    if (youWonMessage) {
        youWonMessage.remove();
    }

    // Reset header positioning
    const header = document.querySelector('.header');
    if (header) {
        header.style.position = '';
    }

    // Reset header title to original (in case it was modified)
    if (headerTitle) {
        headerTitle.innerHTML = '🏌️ Golf Card Game';
    }

    // Hide Next Hole button when clearing celebrations
    const nextHoleContainer = document.getElementById('nextHoleContainer');
    if (nextHoleContainer) {
        nextHoleContainer.style.display = 'none';
    }
}

function clearHurryUpGif() {
    clearCelebration();
}

// Show celebration GIF when human wins
function showCelebrationGif() {
    const celebrationContainer = document.getElementById('celebrationGif');
    const header = document.querySelector('.header');

    // Prevent duplicate celebrations
    const existingMessage = document.getElementById('youWonHeaderMessage');
    if (existingMessage) {
        console.log('🚫 CELEBRATION BLOCKED: Already showing celebration');
        return;
    }

    console.log('🎯 showCelebrationGif() called - checking conditions...');

    if (celebrationContainer && celebrationGifs.length > 0) {
        const randomIndex = Math.floor(Math.random() * celebrationGifs.length);
        const randomGif = celebrationGifs[randomIndex];

        console.log('🎉 Showing celebration GIF:', randomIndex, randomGif);

        // Show GIF without the text
        celebrationContainer.innerHTML = `
            <div class="celebration-gif-container">
                <img src="${randomGif}" alt="Celebration!" class="celebration-gif-img" onerror="console.error('Failed to load celebration GIF:', this.src);" />
            </div>
        `;

        // Add "You Won!" message to the middle of the header
        const existingMessage = document.getElementById('youWonHeaderMessage');
        if (existingMessage) {
            existingMessage.remove();
        }

        if (header) {
            const youWonMessage = document.createElement('div');
            youWonMessage.id = 'youWonHeaderMessage';
            youWonMessage.style.cssText = `
                color: #28a745;
                font-weight: bold;
                font-size: 3.2em;
                animation: pulse 1.5s infinite;
                text-align: center;
                white-space: nowrap;
                position: absolute;
                left: 35%;
                top: 0%;
                transform: translate(-50%, -50%);
                z-index: 1000;

            `;
            youWonMessage.innerHTML = '🎉 You Won! 🎉';

            // Make header relative positioned to contain the absolute positioned message
            header.style.position = 'relative';

            // Insert the message into the header
            header.appendChild(youWonMessage);
        }
    }
}

// Hide opponent selection for 1v3 mode
document.getElementById('gameMode').addEventListener('change', function() {
    const opponentSection = document.getElementById('opponentSection');
    opponentSection.style.display = this.value === '1v1' ? 'block' : 'none';
});

function showSetupViewTimer(seconds) {
    const timerDiv = document.getElementById('setupViewTimer');
    if (!timerDiv) return;
    const secondsNum = parseFloat(seconds);
    timerDiv.textContent = `Bottom two cards visible for: ${seconds} second${secondsNum !== 1 ? 's' : ''}`;
}

function hideSetupViewTimer() {
    const timerDiv = document.getElementById('setupViewTimer');
    if (!timerDiv) return;
    timerDiv.textContent = '';
}

async function startGame() {
    // Reset turn tracking for new game
    lastTurnIndex = null;

    // Reset AI turn flag
    aiTurnInProgress = false;

    // Clear any existing celebrations when starting new game
    clearCelebration();

    // Hide replay button when starting new game
    onGameStart();

    const gameMode = document.getElementById('gameMode').value;

    // Get bot name and map to difficulty
    const botNameSelect = document.getElementById('botNameSelect');
    const botName = botNameSelect ? botNameSelect.value : 'peter_parker';
    const botNameToDifficulty = {
        'peter_parker': 'random',
        'happy_gilmore': 'basic_logic',
        'tiger_woods': 'ev_ai'
    };
    const opponentType = botNameToDifficulty[botName];

    const playerName = document.getElementById('playerName').value || 'Human';
    const numGames = parseInt(document.getElementById('numGames').value) || 1;
    cardVisibilityDuration = parseFloat(document.getElementById('cardVisibilityDuration').value) || 1.5;

    try {
        const response = await fetch('/create_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mode: gameMode,
                opponent: opponentType,
                bot_name: botName,
                player_name: playerName,
                num_games: numGames
            })
        });

        const data = await response.json();
        // Debug: Response received successfully
        if (data.success && data.game_state && data.game_state.players) {
            gameId = data.game_id;
            currentGameState = data.game_state;
            document.getElementById('gameSetup').style.display = 'none';
            document.getElementById('gameBoard').style.display = 'block';
            showHeaderButtons(true); // <-- Add this here
            setupCardsHidden = false;
            if (setupHideTimeout) clearTimeout(setupHideTimeout);
            if (setupViewInterval) clearInterval(setupViewInterval);
            let secondsLeft = cardVisibilityDuration;
            showSetupViewTimer(secondsLeft);
            setupViewInterval = setInterval(() => {
                secondsLeft -= 0.1;
                if (secondsLeft > 0) {
                    showSetupViewTimer(Math.max(0, secondsLeft).toFixed(1));
                } else {
                    hideSetupViewTimer();
                    clearInterval(setupViewInterval);
                }
            }, 100);
            setupHideTimeout = setTimeout(() => {
                setupCardsHidden = true;
                try {
                    updateGameDisplay();
                } catch (error) {
                    console.error('Error in updateGameDisplay (timeout):', error);
                }
                hideSetupViewTimer();
                if (setupViewInterval) clearInterval(setupViewInterval);
            }, cardVisibilityDuration * 1000);
            try {
                updateGameDisplay();
            } catch (error) {
                console.error('Error in updateGameDisplay (initial):', error);
                throw error; // Re-throw to see the full error
            }

            // Clear chatbot UI on new game
            clearChatUI();
            updateChatInputState();
            if (currentPersonality === 'nantz') {
                requestProactiveComment('turn_start');
            }

            // Check if it's an AI's turn right after game creation
            if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                pollAITurns();
            }
        } else {
            console.error('Game start error:', data);
            alert('Error starting game: ' + (data.error || JSON.stringify(data)));
        }
    } catch (error) {
        console.error('Error starting game:', error, error.stack);
        alert('Error starting game: ' + (error.message || error));
    }

    // After the game board is shown and chat is cleared:
    setJimNantzDefault();
}

async function refreshGameState() {
    if (!gameId) return;

    try {
        const response = await fetch(`/game_state/${gameId}`);
        const data = await response.json();
                if (data && !data.error) {
                        // Check if we're in a new game but setup timer hasn't been reset
            const isNewGame = currentGameState && data.current_game > currentGameState.current_game;
            const isMultiGameAndRound1 = data.current_game > 1 && data.round === 1 && setupCardsHidden && lastGameSetupReset < data.current_game;

                        if (isNewGame || isMultiGameAndRound1) {
                lastGameSetupReset = data.current_game; // Mark that we've reset for this game

                // RESET SETUP TIMER FOR NEW GAME
                setupCardsHidden = false;
                if (setupHideTimeout) clearTimeout(setupHideTimeout);
                if (setupViewInterval) clearInterval(setupViewInterval);

                // Start the setup timer for the new game
                let secondsLeft = cardVisibilityDuration;
                showSetupViewTimer(secondsLeft);
                setupViewInterval = setInterval(() => {
                    secondsLeft -= 0.1;
                    if (secondsLeft > 0) {
                        showSetupViewTimer(Math.max(0, secondsLeft).toFixed(1));
                    } else {
                        hideSetupViewTimer();
                        clearInterval(setupViewInterval);
                    }
                }, 100);
                setupHideTimeout = setTimeout(() => {
                    setupCardsHidden = true;
                    updateGameDisplay();
                    hideSetupViewTimer();
                    if (setupViewInterval) clearInterval(setupViewInterval);
                }, cardVisibilityDuration * 1000);
            }

                        currentGameState = data;
            updateGameDisplay();
            // Update chart after game state refresh
            updateCumulativeScoreChart();

            // Check if it's an AI's turn and start polling if needed
            if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                console.log('🔄 refreshGameState: AI turn detected, calling pollAITurns');
                pollAITurns();
            }

            if (data.game_over) {
                // Game over - no modal needed
            }
        }
    } catch (error) {
        console.error('Error refreshing game state:', error);
    }
}

function updateGameDisplay() {
    if (!currentGameState || !currentGameState.players) return;

    try {
        // Get custom player names
        const playerNames = currentGameState.players.map(p => p.name);
        const currentPlayer = currentGameState.players[currentGameState.current_turn];
        const isHumanTurn = currentPlayer && currentGameState.current_turn === 0;

        // Show current game number and total games
        const roundDisplay = Math.min(currentGameState.round, currentGameState.max_rounds);
        let infoText = `Game ${currentGameState.current_game || 1} of ${currentGameState.num_games || 1} | Round ${roundDisplay}/${currentGameState.max_rounds}`;

        // Put game info in the notification area instead of the game info bar
        const gameInfoDisplay = document.getElementById('gameInfoDisplay');
        if (gameInfoDisplay) {
            gameInfoDisplay.textContent = infoText;
        }

        // Clear the old game info bar (keep it empty)
        const gameInfoBar = document.getElementById('gameInfo');
        if (gameInfoBar) {
            gameInfoBar.textContent = '';
        }

        // Update deck size
        const deckSizeElem = document.getElementById('deckSize');
        if (deckSizeElem) {
            deckSizeElem.textContent = `${currentGameState.deck_size} cards`;
        }

        // Update discard pile with comprehensive visual refresh
        const discardCard = document.getElementById('discardCard');
        if (currentGameState.discard_top) {
            // Remove any problematic classes
            discardCard.classList.remove('faded', 'disabled');

            // Add fade if drawing from deck
            if (isDrawingFromDeck) {
                discardCard.classList.add('faded');
            }

            // Restore functionality when not disabled
            if (!discardCard.classList.contains('disabled')) {
                discardCard.onclick = takeDiscard;
            }

            // Force clear and reset all styles
            discardCard.innerHTML = '';
            discardCard.style.cssText = 'opacity: 1 !important; visibility: visible !important;';

            // Force reflow
            discardCard.offsetHeight;

            // Add new content
            const newCardContent = getCardDisplayContent(currentGameState.discard_top, false);
            discardCard.innerHTML = newCardContent;

            console.log('🔄 UPDATED DISCARD PILE:', currentGameState.discard_top.rank + currentGameState.discard_top.suit);
        } else {
            discardCard.innerHTML = '';
            discardCard.classList.add('face-down');
        }

        // Update player grids
        updatePlayerGrids();
        // Update game and round info in header
        updateGameAndRoundInfo();
        // Update last action panel
        updateLastActionPanel();
        // Update probabilities panel
        updateProbabilitiesPanel();

        // Update cumulative score chart (only if game state changed)
        updateCumulativeScoreChart();

        // Update Next Hole button visibility
        updateNextHoleButton();

        // Check if game or match is over and show replay button
        if (currentGameState.game_over) {
            // Check if human player won and show celebration
            if (currentGameState.winner === 0) {
                console.log('🎉 Human player won! Showing celebration...');
                showCelebrationGif();
            }

            if (currentGameState.num_games === 1 || currentGameState.current_game === currentGameState.num_games) {
                // Single game or last game of match - show replay button
                onGameOver();
            }
        }

        // Game display updated successfully
    } catch (error) {
        console.error('Error in updateGameDisplay:', error, error.stack);
        throw error;
    }

    // 1. Compare previous and current state
    if (previousGameState && aiJustMoved()) {
        const {aiIndex, cardPos} = findAIDiscardedCard(previousGameState, currentGameState);
        const cardElem = document.querySelector(`.player-grid[data-player="${aiIndex}"] .card[data-position="${cardPos}"]`);
        const discardElem = document.getElementById('discardCard');
        if (aiIndex !== null && cardPos !== null && cardElem && discardElem) {
            // 2. Animate BEFORE updating the UI to the new state
            animateSnapToGrid(cardElem, discardElem, () => {
                // 3. Now update the UI to the new state
                actuallyUpdateUI();
                previousGameState = JSON.parse(JSON.stringify(currentGameState));
            });
            return;
        }
    }
    // If no animation, just update UI
    actuallyUpdateUI();
    previousGameState = JSON.parse(JSON.stringify(currentGameState));

    // Detect new pair for human player
    if (currentGameState && currentGameState.players && currentGameState.players.length > 0) {
        const human = currentGameState.players[0];
        if (human && Array.isArray(human.pairs)) {
            // Only consider pairs where both cards are public
            const publicPairs = human.pairs.filter(pair => {
                const [pos1, pos2] = pair;
                return human.grid[pos1]?.public && human.grid[pos2]?.public;
            });

            // Compare with previous public pairs
            const newPublicPairs = publicPairs.filter(
                pair => !previousHumanPairs.some(
                    prevPair => prevPair[0] === pair[0] && prevPair[1] === pair[1]
                )
            );
            if (newPublicPairs.length > 0) {
                playGolfClap();
            }
            previousHumanPairs = publicPairs.slice();
        }
    }

    console.log('DEBUG: updateGameDisplay called');
    console.log('DEBUG: currentGameState 561:', currentGameState);
    console.log('DEBUG: previousGameState:', previousGameState);
    if (currentGameState && previousGameState) {
        console.log('DEBUG: current_player:', currentGameState.current_player, 'previous_player:', previousGameState.current_player);
    }

    if (
        currentGameState &&
        currentGameState.action_history &&
        chatbotEnabled
    ) {
        const currentLength = currentGameState.action_history.length;
        if (currentLength > previousActionHistoryLength) {
            previousActionHistoryLength = currentLength;
            if (proactiveCommentTimeout) clearTimeout(proactiveCommentTimeout);
            proactiveCommentTimeout = setTimeout(() => {
                const now = Date.now();
                if (now - lastNantzCommentTime > 400000) { // 4s cooldown
                    console.log('Proactive comment triggered for new action');
                    requestProactiveComment('card_played');
                    lastNantzCommentTime = now;
                } else {
                    console.log('Skipped comment due to cooldown');
                }
            }, 800); // 800ms debounce window
        }
    }

    // Always trigger a summary comment when the game is over
    if (
        currentGameState &&
        currentGameState.game_over &&
        previousGameState &&
        !previousGameState.game_over &&
        chatbotEnabled
    ) {
        console.log('Proactive comment triggered for game over');
        requestProactiveComment('game_over');
    }

    console.log('After move, action_history.length:', currentGameState.action_history.length);
}

function actuallyUpdateUI() {
    // ... your main UI update logic here ...
}

function updatePlayerGrids() {
    const container = document.getElementById('playerGrids');

    // Store old turn index for transition animation
    const oldTurnIndex = lastTurnIndex;
    const currentTurnIndex = currentGameState.current_turn;
    const turnChanged = oldTurnIndex !== currentTurnIndex && oldTurnIndex !== undefined && oldTurnIndex !== null;

    // Prepare for smooth transition if turn changed
    let oldPlayerGrid = null;
    let newPlayerGrid = null;

    if (turnChanged) {
        // Store reference to old current player grid for transition
        const oldCurrentGrid = container.querySelector('.player-grid.current-turn');
        if (oldCurrentGrid) {
            // Create a snapshot of the old spinning background position
            const rect = oldCurrentGrid.getBoundingClientRect();
            oldPlayerGrid = {
                element: oldCurrentGrid,
                rect: rect,
                index: oldTurnIndex
            };
        }
    }

    container.innerHTML = '';
    // Add or remove four-player-grid class
    if (currentGameState.players.length === 4) {
        container.classList.add('four-player-grid');
    } else {
        container.classList.remove('four-player-grid');
    }
    // Only clear timeout and remove animation if turn index changes
    if (lastTurnIndex !== currentTurnIndex) {
        if (turnAnimateTimeout) {
            clearTimeout(turnAnimateTimeout);
            turnAnimateTimeout = null;
        }
        document.querySelectorAll('.player-grid.current-turn').forEach(el => el.classList.remove('turn-animate'));
    }
    currentGameState.players.forEach((player, index) => {
        const playerDiv = document.createElement('div');
        playerDiv.className = 'player-grid';
        playerDiv.setAttribute('data-player', index);
        if (index === currentGameState.current_turn) {
            playerDiv.classList.add('current-turn'); // Highlight current turn
            // Set animation offset to prevent restart on DOM updates
            const animationOffset = (Date.now() % 8000) / 1000; // 8s animation cycle
            playerDiv.style.setProperty('--animation-offset', `${animationOffset}s`);
        }
        const isHuman = index === 0; // Human is always player 0
        // --- NEW: Player name and score header ---
        let displayName = player.name;
        let scoreText = 'Hidden';
        let winnerIcon = '';
        if (currentGameState.public_scores && typeof currentGameState.public_scores[index] !== 'undefined') {
            scoreText = currentGameState.public_scores[index];
            if (currentGameState.game_over && index === currentGameState.winner) {
                winnerIcon = ' 🏆';
            }
        }
        const isCurrentTurn = currentGameState.current_turn === index && !currentGameState.game_over;
        let turnIndicator = '';
        if (isCurrentTurn) {
            if (index === 0) {
                turnIndicator = ' <span class="turn-label">(Your Turn)</span>';
            } else {
                turnIndicator = ' <span class="turn-label">(AI Turn)</span>';
            }
        }
        // Get player color for name
        const playerColor = getPlayerColor(index);
        // --- END NEW ---
        const gridHtml = player.grid.map((card, pos) => {
            if (!card) return '<div class="card face-down"></div>'; // Empty slot
            let cardClass = 'card';
            let displayContent = '';
            let isFaceDown = true;
            let extraAttrs = '';

            if (isHuman && pos >= 2) {
                if (!setupCardsHidden) {
                    cardClass += ' privately-visible'; // Show bottom cards at setup
                    displayContent = getCardDisplayContent(card, false);
                    isFaceDown = false;
                } else if (card.public) {
                    cardClass += ' face-up public'; // Show if made public
                    displayContent = getCardDisplayContent(card, false);
                    isFaceDown = false;
                } else {
                    cardClass += ' face-down'; // Hide after setup
                    displayContent = '';
                    isFaceDown = true;
                }
            } else if (card.visible) {
                if (card.public) {
                    cardClass += ' face-up public';
                } else {
                    cardClass += ' privately-visible';
                }
                displayContent = getCardDisplayContent(card, false);
                isFaceDown = false;
            } else {
                cardClass += ' face-down';
                displayContent = '';
                isFaceDown = true;
            }

            // Drag-and-drop for human player
            if (isHuman && !card.public && currentGameState.current_turn === 0 && !currentGameState.game_over) {
                // Accept drop from discard or drawn card - more lenient detection
                extraAttrs += ' ondragover="event.preventDefault();this.classList.add(\'drop-target\');event.stopPropagation();"';
                extraAttrs += ' ondragenter="event.preventDefault();this.classList.add(\'drop-target\');"';
                extraAttrs += ' ondragleave="if(!event.relatedTarget || !this.contains(event.relatedTarget)) this.classList.remove(\'drop-target\');"';
                extraAttrs += ` ondrop="handleDropOnGrid(${pos});this.classList.remove('drop-target');event.preventDefault();event.stopPropagation();"`;
                // If in flip mode, add flippable class and different styling
                if (window.flipDrawnMode) {
                    cardClass += ' flippable';
                    // Don't add drop-target styling in flip mode unless actively dragging
                    if (!drawnCardDragActive) {
                        cardClass = cardClass.replace(' drop-target', '');
                    }
                }
            } else if (isHuman) {
                extraAttrs += ' class="card not-droppable"';
            }
            return `<div class="${cardClass}" data-position="${pos}" ${extraAttrs}>${displayContent}</div>`;
        }).join('');
        // --- NEW: Add player header above grid ---
        playerDiv.innerHTML = `
        <div class="player-header">
            <span class="player-name"><strong>${displayName}</strong>${winnerIcon}</span>
            <span class="player-score">Score: ${scoreText}</span>
            <span class="player-turn-status">${turnIndicator}</span>
        </div>
        <div class="grid-container">${gridHtml}</div>
    `;
        // --- END NEW ---
        container.appendChild(playerDiv);
    });
    // Robust delayed turn animation for human (border pulse)
    if (currentTurnIndex === 0 && !currentGameState.game_over && lastTurnIndex !== currentTurnIndex) {
        turnAnimateTimeout = setTimeout(() => {
            // Only add animation if still human's turn
            if (currentGameState.current_turn === 0 && !currentGameState.game_over) {
                const grids = document.querySelectorAll('.player-grid.current-turn');
                if (grids.length > 0) {
                    grids[0].classList.add('turn-animate'); // Border pulse
                }
            }
        }, 1); // Delay for border pulse (set to 1ms for instant)
    }
    // Clean up any existing transition backgrounds to prevent duplicates
    document.querySelectorAll('.transition-background').forEach(el => el.remove());

    lastTurnIndex = currentTurnIndex;
    // Attach click handler to flippable cards in flip mode
    if (window.flipDrawnMode) {
        document.querySelectorAll('.flippable').forEach(el => {
            el.onclick = function() {
                const pos = parseInt(this.getAttribute('data-position'));
                flipDrawnCardOnGrid(pos);
            };
        });
    }

    // Handle deck and discard interactivity based on game state
    const deckCard = document.getElementById('deckCard');
    const discardCard = document.getElementById('discardCard');

    if (currentGameState && currentGameState.current_turn === 0 && !currentGameState.game_over) {
        // Human's turn - check if we're in the middle of a drawn card action
        if (window.flipDrawnMode || drawnCardData) {
            // In the middle of resolving a drawn card - disable both deck and discard
            deckCard.classList.add('disabled');
            deckCard.onclick = null;
            discardCard.classList.add('disabled');
            discardCard.onclick = null;
            discardCard.classList.add('faded'); // Add fade effect
        } else {
            // Normal turn - enable both deck and discard
            deckCard.classList.remove('disabled');
            deckCard.onclick = drawFromDeck;
            discardCard.classList.remove('disabled');
            discardCard.onclick = takeDiscard;
            discardCard.classList.remove('faded'); // Remove fade effect
        }
    } else {
        // Not human's turn or game over - disable both
        deckCard.classList.add('disabled');
        deckCard.onclick = null;
        discardCard.classList.add('disabled');
        discardCard.onclick = null;
        discardCard.classList.remove('faded'); // Remove fade effect
    }
}

function updateGameAndRoundInfo() {
    const container = document.getElementById('GameAndRoundInfo');
    if (!container || !currentGameState) {
        return;
    }

    // Game and round info for header
    const roundDisplay = Math.min(currentGameState.round, currentGameState.max_rounds);
    const gameText = `Game ${currentGameState.current_game || 1} of ${currentGameState.num_games || 1} | Round ${roundDisplay}/${currentGameState.max_rounds}`;

    container.textContent = gameText;
}

function updateLastActionPanel() {
    const container = document.getElementById('LastActionPanel');
    if (!container || !currentGameState) {
        return;
    }

    // Action history display (collapsible) - only this, no last action panel
    let actionHistoryHtml = '';
    if (currentGameState.action_history && currentGameState.action_history.length > 0) {
        const isExpanded = window.actionHistoryExpanded || false;
        const toggleIcon = isExpanded ? '▲' : '▼';
        const toggleClass = isExpanded ? 'expanded' : '';
        const containerClass = isExpanded ? 'action-history-expanded' : 'action-history-minimized';

        actionHistoryHtml = `
            <div class="action-history-container ${containerClass}">
                <button class="action-history-toggle ${toggleClass}" onclick="toggleActionHistory()">${toggleIcon}</button>
                <div class="action-history-panel">
                    <div class="last-action-header">Action History:</div>
                    <div class="action-history-list" id="actionHistoryList">
                        ${currentGameState.action_history.map(action => `<div class="action-history-item">${action}</div>`).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    // Auto-scroll action history to bottom only if expanded
    if (window.actionHistoryExpanded) {
        const actionHistoryPanel = container.querySelector('.action-history-panel');
        if (actionHistoryPanel) {
            actionHistoryPanel.scrollTop = actionHistoryPanel.scrollHeight;
        }
    }

    container.innerHTML = actionHistoryHtml;

    setTimeout(() => {
        const actionHistoryList = container.querySelector('.action-history-list');
        if (actionHistoryList) {
            actionHistoryList.scrollTop = actionHistoryList.scrollHeight;
        }
    }, 0);

    // ... after you have currentGameState.action_history ...
    const actionHistoryListElem = document.getElementById('actionHistoryList');
    const newHistory = currentGameState.action_history || [];

    if (actionHistoryListElem) {
        // Only add new items
        for (let i = actionHistoryListElem.children.length; i < newHistory.length; i++) {
            const div = document.createElement('div');
            div.className = 'action-history-item';
            div.textContent = newHistory[i];
            actionHistoryListElem.appendChild(div);
        }
        // Scroll to bottom if new items were added
        if (actionHistoryListElem.children.length === newHistory.length) {
            actionHistoryListElem.scrollTop = actionHistoryListElem.scrollHeight;
        }
    }
}



async function takeDiscard() {
    // Check if the discard card is disabled
    const discardCard = document.getElementById('discardCard');
    if (discardCard.classList.contains('disabled')) {
        return; // Do nothing if disabled
    }

    const availablePositions = getAvailablePositions();
    if (availablePositions.length === 0) {
        alert('No available positions!');
        return;
    }

    if (!currentGameState.discard_top) {
        alert('No discard pile available!');
        return;
    }

    // Now using drag-and-drop instead of modal
    alert('Drag the discard card to a position in your grid to place it.');
}

async function drawFromDeck() {
    // Check if the deck card is disabled
    const deckCard = document.getElementById('deckCard');
    if (deckCard.classList.contains('disabled')) {
        return; // Do nothing if disabled
    }

    if (currentGameState.deck_size === 0) {
        alert('No cards left in deck!');
        return;
    }

    // Clear hurry up timer and GIF when human draws a card or takes a discard
    clearHurryUpTimer();
    clearHurryUpGif();

    // Set fade flag before fetch
    isDrawingFromDeck = true;

    try {
        const response = await fetch(`/draw_card/${gameId}`);
        const data = await response.json();

        if (data.success) {
            showDrawnCardArea(data.drawn_card);
        } else {
            alert('Error drawing card: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error drawing card:', error);
        alert('Error drawing card. Please try again.');
    } finally {
        // Remove fade after UI update
        isDrawingFromDeck = false;
        updateGameDisplay();
    }
}

function showDrawnCardArea(card) {
    drawnCardData = card;
    const area = document.getElementById('drawnCardArea');
    const display = document.getElementById('drawnCardDisplay');
    const instructions = document.getElementById('drawnCardInstructions');
    display.innerHTML = getCardDisplayContent(card, false);
    area.style.display = 'flex';
    instructions.style.display = 'block'; // Show instructions when drawn card is active
    display.setAttribute('draggable', 'true');
    display.classList.remove('dragging');
    display.classList.add('playable');

    // Add drag event listeners for the drawn card
    display.ondragstart = function(e) {
        drawnCardDragActive = true;
        this.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    };

    display.ondragend = function(e) {
        drawnCardDragActive = false;
        this.classList.remove('dragging');
    };

        // Disable deck and discard during drawn card interaction
    const deckCard = document.getElementById('deckCard');
    const discardCard = document.getElementById('discardCard');
    deckCard.classList.add('disabled');
    deckCard.onclick = null;
    discardCard.classList.add('disabled');
    discardCard.onclick = null;

    window.flipDrawnMode = true; // Enable flip mode for clicking grid cards
    updatePlayerGrids();
}

function hideDrawnCardArea() {
    drawnCardData = null;
    drawnCardDragActive = false;
    document.getElementById('drawnCardArea').style.display = 'none';
    document.getElementById('drawnCardInstructions').style.display = 'none'; // Hide instructions when drawn card is hidden
    document.getElementById('drawnCardDisplay').classList.remove('playable');

        // Re-enable deck and discard card
    const deckCard = document.getElementById('deckCard');
    const discardCard = document.getElementById('discardCard');

    deckCard.classList.remove('disabled');
    deckCard.onclick = drawFromDeck;

    discardCard.classList.remove('disabled');
    discardCard.onclick = takeDiscard;

    window.flipDrawnMode = false;
    updatePlayerGrids(); // Refresh to remove flip indicators and update interactivity
}

function getAvailablePositions() {
    if (!currentGameState || currentGameState.current_turn !== 0) return [];

    const humanPlayer = currentGameState.players[0];
    const positions = [];

    for (let i = 0; i < humanPlayer.grid.length; i++) {
        const card = humanPlayer.grid[i];
        if (card && !card.public) {  // Card exists but not publicly known
            positions.push(i);
        }
    }

    return positions;
}

// Position modal functions removed - now using drag-and-drop

async function executeAction(position, actionType = null) {
    if (actionInProgress) {
        console.log('Action blocked: another action is in progress.');
        return;
    }
    actionInProgress = true;
    pausePolling();
    console.log('Sending action to backend:', { position, actionType });
    try {
        const action = {
            game_id: gameId,
            action: {
                type: actionType || currentAction,
                position: position
            }
        };

        // Add extra fields based on action type
        if (actionType === 'draw_keep' || currentAction === 'draw_keep') {
            action.action.type = 'draw_deck';
            action.action.keep = true;
        } else if (actionType === 'draw_discard' || currentAction === 'draw_discard') {
            action.action.type = 'draw_deck';
            action.action.keep = false;
            action.action.flip_position = position;
        }

        const response = await fetch('/make_move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(action)
        });

        const data = await response.json();
        console.log('Received backend response:', data);
        if (data.success) {
            // Clear hurry up timer and GIF when human makes a move
            clearHurryUpTimer();
            clearHurryUpGif();

            console.log('🎯 executeAction: Received updated game state:', data.game_state);
            console.log('🃏 executeAction: Discard top card:', data.game_state.discard_top);

                        // Check if this was a human discard move that needs animation
            if (humanDiscardPosition !== null && humanDiscardAction === 'take_discard') {
                // Animate the card from grid to discard pile
                const cardElem = document.querySelector(`.player-grid[data-player="0"] .card[data-position="${humanDiscardPosition}"]`);
                const discardElem = document.getElementById('discardCard');

                if (cardElem && discardElem) {
                    // First update the game state without UI refresh
                    currentGameState = data.game_state;
                    aiTurnInProgress = false;

                    // Animate the old card to discard pile, then update UI
                    animateSnapToGrid(cardElem, discardElem, () => {
                        updateGameDisplay();
                        updateCumulativeScoreChart();
                        refreshGameState();

                        // Continue with AI turn logic
                        if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                            console.log('⚡ executeAction: AI turn detected, calling pollAITurns');
                            pollAITurns();
                        }
                    });

                    // Reset the trackers
                    humanDiscardPosition = null;
                    humanDiscardAction = null;
                    return; // Don't execute the normal update flow
                }

                // Reset trackers if animation elements not found
                humanDiscardPosition = null;
                humanDiscardAction = null;
            }

            // Check if this was a drawn card move that needs animation
            if (humanDrawnCardPosition !== null && humanDiscardAction === 'draw_keep') {
                // Animate the old card from grid to discard pile
                const cardElem = document.querySelector(`.player-grid[data-player="0"] .card[data-position="${humanDrawnCardPosition}"]`);
                const discardElem = document.getElementById('discardCard');

                if (cardElem && discardElem) {
                    // First update the game state without UI refresh
                    currentGameState = data.game_state;
                    aiTurnInProgress = false;

                    // Animate the old card to discard pile, then update UI
                    animateSnapToGrid(cardElem, discardElem, () => {
                        updateGameDisplay();
                        updateCumulativeScoreChart();
                        refreshGameState();

                        // Continue with AI turn logic
                        if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                            console.log('⚡ executeAction: AI turn detected, calling pollAITurns');
                            pollAITurns();
                        }
                    });

                    // Reset the trackers
                    humanDrawnCardPosition = null;
                    humanDiscardAction = null;
                    return; // Don't execute the normal update flow
                }

                // Reset trackers if animation elements not found
                humanDrawnCardPosition = null;
                humanDiscardAction = null;
            }

            currentGameState = data.game_state;

            // Reset AI turn flag when human takes a turn
            aiTurnInProgress = false;

            updateGameDisplay();
            console.log('🔄 executeAction: Called updateGameDisplay()');
            updateCumulativeScoreChart();
            refreshGameState(); // This may trigger the AI turn if needed
            if (data.game_state.game_over) {
                // Game over - no modal needed
            }
            // If it's now an AI's turn, start polling for AI turns
            if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                console.log('⚡ executeAction: AI turn detected, calling pollAITurns');
                pollAITurns();
            }
        } else {
            console.error('Action failed:', data.error);
            alert('Action failed: ' + (data.error || 'Unknown error'));
            // Reset trackers on failure
            humanDiscardPosition = null;
            humanDiscardAction = null;
            humanDrawnCardPosition = null;
        }
    } catch (error) {
        console.error('Error executing action:', error);
        alert('Error executing action. Please try again.');
        // Reset trackers on error
        humanDiscardPosition = null;
        humanDiscardAction = null;
        humanDrawnCardPosition = null;
    } finally {
        actionInProgress = false;
        resumePolling();
    }
}

function restartGame() {
    // Reset turn tracking for restart
    lastTurnIndex = null;

    // Reset AI turn flag
    aiTurnInProgress = false;

    // Hide game board and show setup screen
    document.getElementById('gameBoard').style.display = 'none';
    document.getElementById('gameSetup').style.display = 'block';

    // Reset chart data for replay
    window.cumulativeScoreHistory = null;
    window.cumulativeScoreLabels = null;
    window.lastMatchId = null;

    // Destroy existing chart instance to ensure fresh start
    if (cumulativeScoreChart) {
        cumulativeScoreChart.destroy();
        cumulativeScoreChart = null;
    }
    // Clear the chart container's HTML
    const chartContainer = document.querySelector('.chart-container');
    if (chartContainer) {
        chartContainer.innerHTML = '<canvas id="cumulativeScoreChart"></canvas><div id="customLegend"></div>';
    }

    // Clear the celebration GIF
    clearCelebration();

    // Reset drawn card state variables
    drawnCardData = null;
    drawnCardDragActive = false;
    window.flipDrawnMode = false;

    // Hide the drawn card area
    hideDrawnCardArea();

    // Optionally reset form fields or keep last settings
}

// Modal closing logic removed - no modals in use

// Periodically refresh game state to catch AI moves
setInterval(() => {
    if (gameId && currentGameState && !currentGameState.game_over && !pollingPaused) {
        refreshGameState();
    }
}, 500); // Reduced from 1000ms to 500ms for more responsive AI turns

// Drawn card drag-and-drop logic
document.addEventListener('DOMContentLoaded', () => {
    const discardCard = document.getElementById('discardCard');
    discardCard.addEventListener('dragstart', (e) => {
        // Check if the discard card is disabled
        if (discardCard.classList.contains('disabled')) {
            console.log('🚫 DRAG BLOCKED: Discard card is disabled');
            e.preventDefault();
            return false;
        }

        console.log('🎯 DRAG START: Discard card drag initiated!');
        dragActive = true;
        // DON'T add drop-target class to the discard card itself
        // Add drag-active class to all potential drop targets (grid cards only)
        document.querySelectorAll('.card:not(.public):not(.not-droppable)').forEach(el => {
            if (el.classList.contains('drop-target')) {
                el.classList.add('drag-active');
            }
        });
        // Store the discard card value at drag start
        if (currentGameState && currentGameState.discard_top) {
            draggedDiscardCard = {
                rank: currentGameState.discard_top.rank,
                suit: currentGameState.discard_top.suit
            };
            console.log('🃏 DRAG START: Stored discard card:', draggedDiscardCard);
        } else {
            draggedDiscardCard = null;
        }
    });
    discardCard.addEventListener('dragend', (e) => {
        console.log('🎯 DRAG END: Discard card drag ended!');
        dragActive = false;
        // DON'T remove drop-target from discard card since we never added it
        draggedDiscardCard = null;
        // Remove highlight from all grid cells
        document.querySelectorAll('.card.drop-target').forEach(el => {
            el.classList.remove('drop-target', 'drag-active');
        });
    });
    // Drawn card drag logic
    const display = document.getElementById('drawnCardDisplay');
    display.addEventListener('dragstart', (e) => {
        if (!drawnCardData) return e.preventDefault();
        drawnCardDragActive = true;
        display.classList.add('dragging');
        // DON'T add drop-target class to the drawn card itself
        // Add drag-active class to all potential drop targets (grid cards only)
        document.querySelectorAll('.card:not(.public):not(.not-droppable)').forEach(el => {
            if (el.classList.contains('drop-target')) {
                el.classList.add('drag-active');
            }
        });
    });
    display.addEventListener('dragend', (e) => {
        drawnCardDragActive = false;
        display.classList.remove('dragging');
        document.querySelectorAll('.card.drop-target').forEach(el => {
            el.classList.remove('drop-target', 'drag-active');
        });
    });
});

// Helper to animate snap effect
function animateSnapToGrid(cardElem, targetElem, callback) {
    const cardRect = cardElem.getBoundingClientRect();
    const targetRect = targetElem.getBoundingClientRect();
    // Create a clone
    const clone = cardElem.cloneNode(true);
    document.body.appendChild(clone);
    clone.style.position = 'fixed';
    clone.style.left = cardRect.left + 'px';
    clone.style.top = cardRect.top + 'px';
    clone.style.width = cardRect.width + 'px';
    clone.style.height = cardRect.height + 'px';
    clone.style.zIndex = 9999;
    clone.style.pointerEvents = 'none';
    clone.style.transition = 'all 0.75s cubic-bezier(.4,1.4,.6,1)'; // sliding card animation
    // Hide original
    cardElem.style.visibility = 'hidden';
    // Animate to target
    requestAnimationFrame(() => {
        clone.style.left = targetRect.left + 'px';
        clone.style.top = targetRect.top + 'px';
    });
    // After animation completes, clean up and trigger next actions
    setTimeout(() => {
        // Remove the animated clone element from the DOM (it's no longer needed)
        clone.remove();

        // Make the original card element visible again (it was hidden during animation)
        cardElem.style.visibility = '';

        // Execute the callback function if provided (usually updates game state/UI)
        if (callback) callback();
    }, 700); // Wait 200ms - should be slightly less than animation duration (500ms)
}

function handleDropOnGrid(pos) {
    // Find the grid cell element
    const gridCells = document.querySelectorAll('.player-grid.current-turn .grid-container .card');
    let targetElem = null;
    gridCells.forEach(cell => {
        if (parseInt(cell.getAttribute('data-position')) === pos) {
            targetElem = cell;
        }
    });
    // Drawn card drop
    if (drawnCardDragActive && drawnCardData) {
        // Store position for animation AFTER the move (similar to discard logic)
        humanDrawnCardPosition = pos;
        humanDiscardAction = 'draw_keep';

        // NO animation for drawn card->grid, but we want grid->discard animation
        // We'll handle the animation in the backend response processing
        executeAction(pos, 'draw_keep');
        hideDrawnCardArea();
        return;
    }
    // Discard card drop
    if (!dragActive) return;
    if (currentGameState.current_turn !== 0 || currentGameState.game_over || !currentGameState.discard_top) return;
    const card = currentGameState.players[0].grid[pos];
    if (!card || card.public) return;
    if (!draggedDiscardCard ||
        currentGameState.discard_top.rank !== draggedDiscardCard.rank ||
        currentGameState.discard_top.suit !== draggedDiscardCard.suit) {
        alert('The discard card has changed. Please try again.');
        return;
    }
    console.log('🎯 handleDropOnGrid: About to take discard at position', pos);
    console.log('🃏 handleDropOnGrid: Current discard top before move:', currentGameState.discard_top);

    // Store position and action for animation AFTER the move
    humanDiscardPosition = pos;
    humanDiscardAction = 'take_discard';

    // NO animation for discard->grid, but we want grid->discard animation
    // We'll handle the animation in the backend response processing
    executeAction(pos, 'take_discard');
}

function flipDrawnCardOnGrid(pos) {
    if (!window.flipDrawnMode || !drawnCardData) return;
    // Only allow if the position is not public
    const card = currentGameState.players[0].grid[pos];
    if (!card || card.public) return;
    // 1. Get the card element and discard pile element
    const cardElem = document.querySelector(`.player-grid.current-turn .card[data-position="${pos}"]`);
    const discardElem = document.getElementById('discardCard');

    // 2. Animate the card to the discard pile
    animateSnapToGrid(cardElem, discardElem, () => {
        // 3. After animation, update the game state/UI
        executeAction(pos, 'draw_discard');
        hideDrawnCardArea();
    });
}

function updateProbabilitiesPanel() {
    const unknownCardsPanel = document.getElementById('unknownCardsPanel');
    const otherProbabilitiesPanel = document.getElementById('otherProbabilitiesPanel');

    // Hide probabilities if game is over
    if (currentGameState && currentGameState.game_over) {
        if (unknownCardsPanel) unknownCardsPanel.classList.add('hidden');
        // Only hide the content, not the column
        const panelBox = otherProbabilitiesPanel.querySelector('.probabilities-panel-box');
        if (panelBox) panelBox.classList.add('hidden');
        return;
    } else {
        if (unknownCardsPanel) unknownCardsPanel.classList.remove('hidden');
        const panelBox = otherProbabilitiesPanel.querySelector('.probabilities-panel-box');
        if (panelBox) panelBox.classList.remove('hidden');
    }

    if (!currentGameState || !currentGameState.probabilities) {
        if (unknownCardsPanel) unknownCardsPanel.innerHTML = '';
        if (otherProbabilitiesPanel) otherProbabilitiesPanel.innerHTML = '';
        return;
    }

    const probs = currentGameState.probabilities;

    // LEFT COLUMN: Unknown Cards Chart
    if (unknownCardsPanel && probs.deck_counts) {
        let unknownHtml = '<div class="probabilities-panel-box">';
        unknownHtml += '<h4 class="probabilities-title">Cards Left</h4>';

        // Desired order: J, A, 2-10, Q, K
        const order = ['J', 'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Q', 'K'];
        const maxCount = Math.max(...Object.values(probs.deck_counts));

        unknownHtml += '<table class="probabilities-table">';
        unknownHtml += '<thead><tr><th class="rank-header">Rank</th><th class="count-header">Count</th></tr></thead><tbody>';

        for (const rank of order) {
            if (probs.deck_counts[rank] !== undefined) {
                const count = probs.deck_counts[rank];
                const barWidth = maxCount > 0 ? (count / maxCount) * 100 : 0;

                // Color based on count
                let barColorClass;
                if (count === 0) {
                    barColorClass = 'card-bar-red';
                } else if (count === 1) {
                    barColorClass = 'card-bar-orange';
                } else if (count <= 2) {
                    barColorClass = 'card-bar-yellow';
                } else if (count <= 3) {
                    barColorClass = 'card-bar-teal';
                } else {
                    barColorClass = 'card-bar-green';
                }

                unknownHtml += `<tr><td class="rank-cell">${rank}</td>`;
                unknownHtml += `<td class="count-cell">`;
                unknownHtml += `<div class="card-count-bar-container">`;
                unknownHtml += `<div class="card-count-bar ${barColorClass}" style="width:${Math.max(barWidth, 8)}%;">`;
                unknownHtml += `<span class="card-count-text">${count}</span>`;
                unknownHtml += `</div>`;
                unknownHtml += `</div>`;
                unknownHtml += `</td></tr>`;
            }
        }
        unknownHtml += '</tbody></table></div>';
        unknownCardsPanel.innerHTML = unknownHtml;
    }

    // RIGHT COLUMN: Other Probabilities
    if (otherProbabilitiesPanel) {
        let otherHtml = '<div class="probabilities-panel-box">';
        otherHtml += '<h4 class="probabilities-title">Probabilities</h4>';

        // Expected Value Comparison (most important - show first)
        if (probs.expected_value_draw_vs_discard && currentGameState.current_turn === 0 && !currentGameState.game_over) {
            const ev = probs.expected_value_draw_vs_discard;
            otherHtml += '<div class="probabilities-bar">';
            otherHtml += '<div class="probabilities-bar-title">🎯 Strategery!</div>';
            otherHtml += `<div class="probabilities-bar-main"><b>${ev.recommendation}</b></div>`;
            otherHtml += `<div class="probabilities-bar-detail">Draw: ${ev.draw_expected_value > 0 ? '+' : ''}${ev.draw_expected_value} EV</div>`;
            otherHtml += `<div class="probabilities-bar-detail">Discard: ${ev.discard_expected_value > 0 ? '+' : ''}${ev.discard_expected_value} EV</div>`;
            otherHtml += `<div class="probabilities-bar-detail">Advantage: ${ev.draw_advantage > 0 ? '+' : ''}${ev.draw_advantage} EV</div>`;
            // if (ev.discard_card) {
            //     otherHtml += `<div class="probabilities-bar-detail">Discard: ${ev.discard_card} (score: ${ev.discard_score})</div>`;
            // }
            otherHtml += '</div>';
        }

        // Probability statistics
        if (probs.prob_draw_pair && probs.prob_draw_pair.length > 0) {
            otherHtml += `<div class="probabilities-stat">`;
            otherHtml += `<b>Prob. next card matches your grid:</b> <span class="probability-blue">${probs.prob_draw_pair[0]}</span>`;
            otherHtml += '</div>';
        }
        // Probability of drawing a card that improves your hand (for human)
        if (probs.prob_improve_hand && probs.prob_improve_hand.length > 0) {
            otherHtml += `<div class="probabilities-stat">`;
            otherHtml += `<b>Prob. next card improves your hand:</b> <span class="probability-blue">${probs.prob_improve_hand[0]}</span>`;
            otherHtml += '</div>';
        }

        // Average score of remaining cards in deck
        if (probs.average_deck_score !== undefined) {
            otherHtml += `<div class="probabilities-stat">`;
            otherHtml += `<b>Average score of remaining cards:</b> <span class="probability-blue">${probs.average_deck_score}</span>`;
            otherHtml += '</div>';
        }

        otherHtml += '</div>';
        otherProbabilitiesPanel.innerHTML = otherHtml;
    }

    // Hide probabilities panel box if game is over
    if (currentGameState && currentGameState.game_over) {
        // Hide the probabilities panel box
        const panelBox = otherProbabilitiesPanel.querySelector('.probabilities-panel-box');
        if (panelBox) {
            panelBox.classList.add('hidden');
        }
    } else {
        // Show it if not game over
        const panelBox = otherProbabilitiesPanel.querySelector('.probabilities-panel-box');
        if (panelBox) {
            panelBox.classList.remove('hidden');
        }
    }
}

// Draw a line chart of cumulative scores for all players
let cumulativeScoreChart = null;
let lastChartGameId = null;
let lastChartRound = null;

function initializeCumulativeScoreChart() {
    const canvas = document.getElementById('cumulativeScoreChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart if it exists
    if (cumulativeScoreChart) {
        cumulativeScoreChart.destroy();
    }

    // Initialize with empty data
    const initialLabels = window.cumulativeScoreLabels || [];
    const initialDatasets = [];

    // Create datasets for current players if available
    if (currentGameState && currentGameState.players) {
        currentGameState.players.forEach((player, i) => {
            initialDatasets.push({
                label: player.name,
                data: window.cumulativeScoreHistory ? (window.cumulativeScoreHistory[i] || []) : [],
                borderColor: getPlayerColor(i),
                backgroundColor: getPlayerColor(i),
                borderWidth: 3, // Thicker lines
                fill: false,
                tension: 0.4, // Smooth curved lines
                pointRadius: 3,
                hoverRadius: 6
            });
        });
    }

    cumulativeScoreChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: initialLabels,
            datasets: initialDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false, // Hide default legend
                    position: 'left', // Changed from 'right' to 'left'
                    labels: {
                        boxWidth: 10,
                        padding: 4,
                        usePointStyle: true,
                        font: {
                            size: 7  // Reduced from 10 to 8
                        },
                        color: '#ffffff'
                    }
                },
                title: {
                    display: true,
                    text: 'Cumulative Scores by Round',
                    color: '#ffffff',
                    font: {
                        size: 12,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Game & Round',
                        color: '#ffffff',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        autoSkip: false,
                        color: '#ffffff',
                        font: {
                            size: 9
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.6)',
                        lineWidth: 1
                    },
                    border: {
                        color: '#ffffff',
                        width: 1
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Score',
                        color: '#ffffff',
                        font: {
                            size: 10
                        }
                    },
                    beginAtZero: true,
                    suggestedMin: 0,
                    suggestedMax: 20,
                    ticks: {
                        color: '#ffffff',
                        font: {
                            size: 9
                        },
                        stepSize: 4
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.6)',
                        lineWidth: 1
                    },
                    border: {
                        color: '#ffffff',
                        width: 1
                    }
                }
            },
            elements: {
                point: {
                    radius: 2,
                    hoverRadius: 4
                },
                line: {
                    spanGaps: false
                }
            }
        },
        plugins: [htmlLegendPlugin, {
            id: 'textOutline',
            afterDraw: (chart) => {
                const ctx = chart.ctx;
                const originalStrokeText = ctx.strokeText;
                const originalFillText = ctx.fillText;

                // Override fillText to add stroke
                ctx.fillText = function(text, x, y, maxWidth) {
                    // Save current state
                    ctx.save();

                    // Draw black outline
                    ctx.strokeStyle = '#000000';
                    ctx.lineWidth = 3;
                    ctx.lineJoin = 'round';
                    ctx.miterLimit = 2;
                    if (originalStrokeText) {
                        originalStrokeText.call(ctx, text, x, y, maxWidth);
                    }

                    // Draw white fill
                    ctx.fillStyle = '#ffffff';
                    originalFillText.call(ctx, text, x, y, maxWidth);

                    // Restore state
                    ctx.restore();
                };

                // Trigger a redraw
                Chart.helpers.each(chart.boxes, (box) => {
                    box.draw();
                });

                // Restore original methods
                ctx.fillText = originalFillText;
                ctx.strokeText = originalStrokeText;
            }
        }]
    });
}

// Helper function to get consistent player colors
function getPlayerColor(playerIndex) {
    const colors = ['#007bff', '#e67e22', '#28a745', '#764ba2', '#f39c12', '#e74c3c'];
    return colors[playerIndex % colors.length];
}

// Add throttling to prevent excessive chart updates
let lastChartUpdate = 0;
const CHART_UPDATE_THROTTLE = 100; // minimum 100ms between updates

function updateCumulativeScoreChart() {
    const canvas = document.getElementById('cumulativeScoreChart');
    if (!canvas) {
        return;
    }

    // Throttle chart updates to prevent excessive rendering
    const now = Date.now();
    if (now - lastChartUpdate < CHART_UPDATE_THROTTLE) {
        return;
    }
    lastChartUpdate = now;

    const ctx = canvas.getContext('2d');

    // Initialize chart if it doesn't exist
    if (!cumulativeScoreChart) {
        initializeCumulativeScoreChart();
    }

    if (!currentGameState || !currentGameState.current_game) {
        return;
    }

    const gameId = currentGameState.current_game;

    // Build score history for each player, per round
    // Only reset history when starting a completely new match (not when advancing games)
    const matchId = `${currentGameState.num_games}_` +
        currentGameState.players.map(p => (p.name + '_' + (p.agent_type || '')).toLowerCase()).join('_');
    if (!window.cumulativeScoreHistory || !window.lastMatchId || window.lastMatchId !== matchId) {
        // Reset history for new match session (not just new game)
        window.cumulativeScoreHistory = [];
        for (let i = 0; i < currentGameState.players.length; i++) {
            window.cumulativeScoreHistory.push([]);
        }
        window.cumulativeScoreLabels = [];
        window.lastMatchId = matchId; // Track match with num_games and player names
        window.lastProcessedRound = 1; // Reset round tracking
        lastChartRound = null;
    }

    // Track current round progress
    const currentRoundKey = `G${currentGameState.current_game}R${currentGameState.round}`;

    // Use cumulative_scores first (which contains accumulated match totals), fallback to public_scores
    let roundScores = null;
    if (currentGameState.cumulative_scores && currentGameState.cumulative_scores.every(score => score !== null && score !== undefined)) {
        // Use cumulative scores first (contains accumulated match totals)
        roundScores = currentGameState.cumulative_scores;
        console.log('Using cumulative_scores:', roundScores);
    } else if (currentGameState.public_scores && currentGameState.public_scores.some(score => typeof score === 'number')) {
        // Fallback to public scores if cumulative not available
        roundScores = currentGameState.public_scores.map(score => typeof score === 'number' ? score : 0);
        console.log('Using public_scores:', roundScores);
    }

    console.log('Chart Debug - Game:', currentGameState.current_game, 'Round:', currentGameState.round, 'Scores:', roundScores, 'Game Over:', currentGameState.game_over);

    // Only proceed if we have valid scores to chart
    if (!roundScores) {
        console.log('No valid scores available for charting');
        return;
    }

    // Round completion detection: When scores exist but we're in a later round,
    // the scores represent the previous completed round
    let targetRound = currentGameState.round;
    let targetRoundKey = currentRoundKey;

    // Track the last round we processed
    if (!window.lastProcessedRound) {
        window.lastProcessedRound = 1;
    }

    // If we have scores and round has advanced, scores are for the previous round
    if (currentGameState.round > window.lastProcessedRound && roundScores.some(score => score > 0)) {
        targetRound = currentGameState.round - 1;
        targetRoundKey = `G${currentGameState.current_game}R${targetRound}`;
        console.log('=== ROUND COMPLETION DETECTED ===');
        console.log('Current round:', currentGameState.round, 'Recording scores for completed round:', targetRound);
        window.lastProcessedRound = currentGameState.round;
    }

    const isNewRound = !window.cumulativeScoreLabels.includes(targetRoundKey);
    let dataChanged = false;

    if (isNewRound) {
        // Add new data point for new round
        for (let i = 0; i < currentGameState.players.length; i++) {
            window.cumulativeScoreHistory[i].push(roundScores[i] || 0);
        }
        window.cumulativeScoreLabels.push(targetRoundKey);
        lastChartRound = targetRoundKey;
        dataChanged = true;
        console.log('=== ADDED NEW ROUND ===', targetRoundKey, 'with scores:', roundScores);
    } else {
        // Update existing data point if scores have changed
        const lastIndex = window.cumulativeScoreLabels.findIndex(label => label === targetRoundKey);
        if (lastIndex >= 0) {
            for (let i = 0; i < currentGameState.players.length; i++) {
                const newScore = roundScores[i] || 0;
                if (window.cumulativeScoreHistory[i][lastIndex] !== newScore) {
                    console.log('=== UPDATING SCORE ===', `Player ${i}:`, window.cumulativeScoreHistory[i][lastIndex], '→', newScore);
                    window.cumulativeScoreHistory[i][lastIndex] = newScore;
                    dataChanged = true;
                }
            }
        }
    }

    // Only update the chart if data actually changed
    if (!dataChanged) {
        return;
    }

    // Update chart data without recreating the chart
    if (cumulativeScoreChart && cumulativeScoreChart.data) {
        // Determine what data to show based on game progression
        let displayLabels = [...window.cumulativeScoreLabels];
        let displayHistory = window.cumulativeScoreHistory.map(playerHistory => [...playerHistory]);

        const maxRoundsToShow = 12; // or whatever number you want
        if (displayLabels.length > maxRoundsToShow) {
            displayLabels = displayLabels.slice(-maxRoundsToShow);
            displayHistory = displayHistory.map(playerHistory =>
                playerHistory.slice(-maxRoundsToShow)
            );
        }

        // Update chart with the determined data
        cumulativeScoreChart.data.labels = displayLabels;

        // Update datasets for active players only
        const activePlayerNames = currentGameState.players.map(p => p.name);
        cumulativeScoreChart.data.datasets = activePlayerNames.map((playerName, i) => ({
            label: playerName,
            data: displayHistory[i] || [],
            borderColor: getPlayerColor(i),
            backgroundColor: getPlayerColor(i),
            borderWidth: 3, // Thicker lines
            fill: false,
            tension: 0.4, // Smooth curved lines
            spanGaps: false // Don't connect lines across null values
        }));

        // Update the chart display
        cumulativeScoreChart.update('none'); // Use 'none' animation mode for smooth updates
    } else {
        // Fallback: recreate chart if something went wrong
        initializeCumulativeScoreChart();
    }

    console.log('Chart DEBUG:', {
        matchId,
        lastMatchId: window.lastMatchId,
        cumulativeScoreHistory: window.cumulativeScoreHistory,
        cumulativeScoreLabels: window.cumulativeScoreLabels
    });
}

// Show timer on initial load
document.addEventListener('DOMContentLoaded', function() {
    showSetupViewTimer(cardVisibilityDuration);
    // Initialize the chart when page loads
    setTimeout(() => {
        initializeCumulativeScoreChart();
    }, 100); // Small delay to ensure DOM is ready
});

function onDrop(card, slot) {
    const cardRect = card.getBoundingClientRect();
    const slotRect = slot.getBoundingClientRect();

    const dx = cardRect.left - slotRect.left;
    const dy = cardRect.top - slotRect.top;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < SNAP_THRESHOLD) {
        // Snap the card to the slot
        card.style.transition = 'all 0.2s';
        card.style.left = `${slotRect.left}px`;
        card.style.top = `${slotRect.top}px`;
        // Optionally, update your game state here
    } else {
        // Return card to original position or handle as invalid drop
    }
}

async function pollAITurns() {
    console.log('🤖 pollAITurns called - current_turn:', currentGameState?.current_turn, 'game_over:', currentGameState?.game_over, 'aiTurnInProgress:', aiTurnInProgress);

    // Prevent multiple concurrent AI turn polling
    if (aiTurnInProgress) {
        console.log('🤖 AI turn already in progress, skipping...');
        return;
    }

    // FIXED: Only run ONE AI turn at a time, not all AI turns in a loop
    // This allows humans to see each AI move before the next one happens
    if (currentGameState && currentGameState.current_turn !== 0 && !currentGameState.game_over) {
        aiTurnInProgress = true; // Set flag to prevent concurrent calls
        console.log('🤖 Making AI turn request for player', currentGameState.current_turn);

        try {
            const response = await fetch('/run_ai_turn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ game_id: gameId })
            });
            const data = await response.json();
            if (data.success) {
                console.log('🤖 AI turn successful, updating game state');
                currentGameState = data.game_state;
                updateGameDisplay();

                // If there's another AI turn needed, schedule it after a delay
                if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                    console.log('🤖 Scheduling next AI turn after delay...');
                    setTimeout(() => {
                        aiTurnInProgress = false; // Reset flag before next call
                        pollAITurns(); // Recursive call for next AI turn
                    }, 1500); // 1.5 second delay between AI turns for visibility
                } else {
                    aiTurnInProgress = false; // Reset flag when done
                }
            } else {
                console.log('🤖 AI turn failed or game over:', data.error);
                aiTurnInProgress = false; // Reset flag on error
            }
        } catch (error) {
            console.error('🤖 Error in pollAITurns:', error);
            aiTurnInProgress = false; // Reset flag on error
        }
    }
    console.log('🤖 pollAITurns finished - current_turn:', currentGameState?.current_turn, 'aiTurnInProgress:', aiTurnInProgress);
}

// Add the replayGame function
function replayGame() {
    onGameStart(); // Hide the replay button immediately
    // Reset turn tracking for replay
    lastTurnIndex = null;

    // Reset drawn card state variables
    drawnCardData = null;
    drawnCardDragActive = false;
    window.flipDrawnMode = false;

    // Reset chart data for replay
    window.cumulativeScoreHistory = null;
    window.cumulativeScoreLabels = null;
    window.lastMatchId = null;

    // Destroy existing chart instance to ensure fresh start
    if (cumulativeScoreChart) {
        cumulativeScoreChart.destroy();
        cumulativeScoreChart = null;
    }
    // Clear the chart container's HTML
    const chartContainer = document.querySelector('.chart-container');
    if (chartContainer) {
        chartContainer.innerHTML = '<canvas id="cumulativeScoreChart"></canvas><div id="customLegend"></div>';
    }

    // Clear the celebration GIF
    clearCelebration();

    // Hide the drawn card area
    hideDrawnCardArea();

    // Use the last selected settings
    const gameMode = currentGameState.mode || '1v1';
    const opponentType = currentGameState.players && currentGameState.players[1] ? currentGameState.players[1].agent_type : 'random';
    const playerName = currentGameState.players && currentGameState.players[0] ? currentGameState.players[0].name : 'Human2';
    const numGames = currentGameState.num_games || 1;
    // Start a new game with the same settings
    startGameWithSettings(gameMode, opponentType, playerName, numGames);

    // Check if it's a multi-hole match
    if (currentGameState && (currentGameState.num_games === 1 || !currentGameState.num_games)) {
        // Single game mode: clear chat
        clearChatUI();
    }
    // else: multi-hole match, do NOT clear chat

    previousActionHistoryLength = 0;
    lastNantzCommentTime = 0;
    if (proactiveCommentTimeout) clearTimeout(proactiveCommentTimeout);
    proactiveCommentTimeout = null;
}

async function nextGame() {
    if (!gameId) {
        console.error('No game ID available');
        return;
    }

    // Clear the celebration GIF when starting next game
    clearCelebration();

    try {
        const response = await fetch('/next_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_id: gameId
            })
        });

        const data = await response.json();

        if (data.success) {
            currentGameState = data.game_state;

            // Set up card visibility for the new game (same as startGame/startGameWithSettings)
            setupCardsHidden = false;
            if (setupHideTimeout) clearTimeout(setupHideTimeout);
            if (setupViewInterval) clearInterval(setupViewInterval);
            let secondsLeft = cardVisibilityDuration;
            showSetupViewTimer(secondsLeft);
            setupViewInterval = setInterval(() => {
                secondsLeft -= 0.1;
                if (secondsLeft > 0) {
                    showSetupViewTimer(Math.max(0, secondsLeft).toFixed(1));
                } else {
                    hideSetupViewTimer();
                    clearInterval(setupViewInterval);
                }
            }, 100);
            setupHideTimeout = setTimeout(() => {
                setupCardsHidden = true;
                updateGameDisplay();
                hideSetupViewTimer();
                if (setupViewInterval) clearInterval(setupViewInterval);
            }, cardVisibilityDuration * 1000);

            updateGameDisplay();
            updateCumulativeScoreChart();

            // Check if it's an AI's turn right after new game creation
            if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                pollAITurns();
            }
        } else {
            console.error('Next game error:', data.error);
            alert('Error starting next game: ' + data.error);
        }
    } catch (error) {
        console.error('Error starting next game:', error);
        alert('Error starting next game. Please try again.');
    }
}

// Add a helper to start a game with specific settings
async function startGameWithSettings(gameMode, opponentType, playerName, numGames) {
    // Clear the celebration GIF when starting a new game
    clearCelebration();

    try {
        const response = await fetch('/create_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mode: gameMode,
                opponent: opponentType,
                player_name: playerName,
                num_games: numGames
            })
        });
        const data = await response.json();
        if (data.success && data.game_state && data.game_state.players) {
            gameId = data.game_id;
            currentGameState = data.game_state;
            document.getElementById('gameSetup').style.display = 'none';
            document.getElementById('gameBoard').style.display = 'block';
            setupCardsHidden = false;
            if (setupHideTimeout) clearTimeout(setupHideTimeout);
            if (setupViewInterval) clearInterval(setupViewInterval);
            let secondsLeft = cardVisibilityDuration;
            showSetupViewTimer(secondsLeft);
            setupViewInterval = setInterval(() => {
                secondsLeft -= 0.1;
                if (secondsLeft > 0) {
                    showSetupViewTimer(Math.max(0, secondsLeft).toFixed(1));
                } else {
                    hideSetupViewTimer();
                    clearInterval(setupViewInterval);
                }
            }, 100);
            setupHideTimeout = setTimeout(() => {
                setupCardsHidden = true;
                updateGameDisplay();
                hideSetupViewTimer();
                if (setupViewInterval) clearInterval(setupViewInterval);
            }, cardVisibilityDuration * 1000);
            updateGameDisplay();

            // Check if it's an AI's turn right after game creation - add delay for first turn
            if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                setTimeout(() => {
                    if (currentGameState && currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                        pollAITurns();
                    }
                }, 500); // Add 500ms delay for first AI turn
            }
        } else {
            alert('Error starting game: ' + (data.error || JSON.stringify(data)));
        }
    } catch (error) {
        alert('Error starting game: ' + (error.message || error));
    }
}

// Remove the problematic global scope code that was causing the null reference error
// The pollAITurns() function should only be called from within functions after a game is started

function updateInteractivity(isMyTurn) {
    // Deck
    const deck = document.getElementById('deckCard');
    if (deck) {
        deck.classList.toggle('disabled', !isMyTurn);
    }

    // Discard
    const discard = document.getElementById('discardCard');
    if (discard) {
        discard.classList.toggle('disabled', !isMyTurn);
    }

    // All your cards
    document.querySelectorAll('.player-grid.human .card').forEach(card => {
        card.classList.toggle('disabled', !isMyTurn);
    });
}

function setPlayerInteractivity(isMyTurn) {
    // Deck
    const deck = document.getElementById('deckCard');
    if (deck) deck.classList.toggle('disabled', !isMyTurn);

    // Discard
    const discard = document.getElementById('discardCard');
    if (discard) {
        discard.classList.toggle('disabled', !isMyTurn);
        discard.draggable = !!isMyTurn;
        if (isMyTurn) {
            discard.onclick = takeDiscard;
        } else {
            discard.onclick = null;
        }
    }

    // All your cards
    document.querySelectorAll('.player-grid.human .card').forEach(card => {
        card.classList.toggle('disabled', !isMyTurn);
        card.draggable = !!isMyTurn;
    });
}
//was causing error before so not sure about this.
// discardCard.onclick = function() {
//     if (!isMyTurn) return;
//     // ...rest of logic...
// };

function handleGameEnd() {
    // Immediately fetch new game state, don't wait for polling
    fetch(`/game_state/${gameId}`)
        .then(response => response.json())
        .then(newState => {
            currentGameState = newState;
            updateGameDisplay(); // Force immediate UI update
        });
}

function updateChart(gameData) {
    // Only include players that are actually in the game
    const activePlayers = gameData.players.filter(player => player.isActive);

    // Create datasets only for active players
    const datasets = activePlayers.map(player => ({
        label: player.name,
        data: player.scores,
        backgroundColor: player.color,
        // ...
    }));
}

// Wrap polling interval logic
function pausePolling() { pollingPaused = true; }
function resumePolling() { pollingPaused = false; }

function findAIDiscardedCard(prev, curr) {
    for (let aiIndex = 1; aiIndex < prev.players.length; aiIndex++) {
        const prevGrid = prev.players[aiIndex].grid;
        const currGrid = curr.players[aiIndex].grid;
        for (let pos = 0; pos < prevGrid.length; pos++) {
            if (prevGrid[pos] && !currGrid[pos]) {
                // Check if this card matches the new discard top
                const discard = curr.discard_top;
                if (prevGrid[pos].rank === discard.rank && prevGrid[pos].suit === discard.suit) {
                    console.log('findAIDiscardedCard: Found discarded card', {aiIndex, pos, card: prevGrid[pos]});
                    return { aiIndex, cardPos: pos };
                }
            }
        }
    }
    console.log('findAIDiscardedCard: No discarded card found');
    return { aiIndex: null, cardPos: null };
}

function aiJustMoved() {
    const result = previousGameState && previousGameState.current_turn !== 0 && currentGameState.current_turn === 0;
    console.log('aiJustMoved:', result, 'prev turn:', previousGameState && previousGameState.current_turn, 'curr turn:', currentGameState.current_turn);
    return result;
}

function deepCopy(obj) {
    return JSON.parse(JSON.stringify(obj));
}

const discardCard = document.getElementById('discardCard');
if (discardCard) {
    // Fade if a drawn card is active or in flip mode
    if (window.flipDrawnMode || drawnCardData) {
        discardCard.classList.add('faded');
        discardCard.onclick = null;
        discardCard.setAttribute('tabindex', '-1');
    } else {
        discardCard.classList.remove('faded');
        discardCard.onclick = takeDiscard;
        discardCard.setAttribute('tabindex', '0');
    }
}

// Update Next Hole button visibility
function updateNextHoleButton() {
    const nextHoleContainer = document.getElementById('nextHoleContainer');
    if (nextHoleContainer) {
        if (currentGameState && currentGameState.waiting_for_next_game) {
            nextHoleContainer.style.display = 'block';
        } else {
            nextHoleContainer.style.display = 'none';
        }
    }
}

function showHeaderButtons(show) {
    const headerButtons = document.getElementById('headerButtons');
    if (headerButtons) {
        headerButtons.style.display = show ? 'flex' : 'none';
    }
}

// When showing setup:
showHeaderButtons(false);

// When starting the game:
showHeaderButtons(true);

document.addEventListener('DOMContentLoaded', function() {
    showHeaderButtons(false);
});

showHeaderButtons(true);

function enableActionHistory() {
  const chat = document.querySelector('.action-history');
  chat.style.pointerEvents = 'auto';
  chat.style.overflow = 'auto';
  chat.style.scrollbarWidth = '';
  chat.style.msOverflowStyle = '';
}

function showReplayButton(show) {
    document.getElementById('replayContainer').style.display = show ? 'block' : 'none';
}

// Call this when the game is over (single game mode)
function onGameOver() {
    showReplayButton(true);
}

// Call this when the match is over (multi-game mode)
function onMatchOver() {
    showReplayButton(true);
}

// Hide it at the start of a new game/match
function onGameStart() {
    showReplayButton(false);
}

function playGolfClap() {
    const audio = document.getElementById('golfClapAudio');
    if (audio) {
        audio.currentTime = 0;
        audio.play();
    }
}

// ===== CHATBOT FUNCTIONALITY =====

// Chatbot state (already declared at top)

// Initialize chatbot functionality
function initializeChatbot() {
    proactiveCommentSent = false;
    console.log('🔧 Initializing chatbot...');

    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const personalitySelect = document.getElementById('personalitySelect');

    console.log('Chat elements found:', {
        chatInput: !!chatInput,
        sendBtn: !!sendBtn,
        personalitySelect: !!personalitySelect
    });

    if (chatInput && sendBtn) {
        console.log('✅ Setting up chat event listeners');

        // Send message on Enter key
        chatInput.addEventListener('keypress', function(e) {
            console.log('Keypress event:', e.key);
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                console.log('Enter pressed, calling sendChatMessage');
                sendChatMessage();
            }
        });

        // Send message on button click
        sendBtn.addEventListener('click', function(e) {
            console.log('Send button clicked');
            e.preventDefault();
            sendChatMessage();
        });

        console.log('✅ Chat event listeners set up');
    } else {
        console.error('❌ Chat elements not found:', {
            chatInput: chatInput,
            sendBtn: sendBtn
        });
    }

    if (personalitySelect) {
        personalitySelect.addEventListener('change', function(e) {
            console.log('Personality changed to:', e.target.value);
            changePersonality(e.target.value);
        });
    }

    // Load initial personality
    // loadPersonalities();

    // Always (re)attach the event listener for the dropdown
    const chatOpponentSelect = document.getElementById('chatOpponentSelect');
    if (chatOpponentSelect) {
        chatOpponentSelect.onchange = function(e) {
            const selected = e.target.value;
            console.log('Dropdown changed to:', selected);
            currentPersonality = selected;
            updateChatInputState();
            // changePersonality(selected);  // <--- REMOVE or COMMENT OUT this line!
        };
    }
}

// Send a message to the chatbot
async function sendChatMessage() {
    console.log('📤 sendChatMessage called');

    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const message = chatInput.value.trim();

    console.log('Message:', message);
    console.log('Game ID:', gameId);

    if (!message) {
        console.log('❌ No message to send');
        return;
    }

    if (!gameId) {
        console.log('❌ No game ID available');
        addMessageToChat('bot', 'Please start a game first before chatting.');
        return;
    }

    console.log('✅ Sending message to chatbot...');

    // Disable input while processing
    chatInput.disabled = true;
    sendBtn.disabled = true;

    // Add user message to chat
    addMessageToChat('user', message);

    // Debug before clearing
    console.log('Message before clearing input:', message);
    chatInput.value = '';
    console.log('Message after clearing input:', chatInput.value);

    try {
        console.log('🌐 Making API request to /chatbot/send_message');
        const personalityType = getSelectedChatbotPersonality();

        // Debug what will be sent
        console.log('Sending to backend:', {
            game_id: gameId,
            message: message,
            personality_type: personalityType
        });

        console.log('🔄 Awaiting response...');
        const response = await fetch('/chatbot/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: gameId,
                message: message,
                personality_type: personalityType
            })
        });

        console.log('📥 Response received:', response.status);
        console.log('📥 Response ok:', response.ok);

        if (!response.ok) {
            console.error('❌ Response not ok:', response.status, response.statusText);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('📄 Response data:', data);
        console.log('📄 Response data.bot:', data.bot);
        console.log('📄 Response data.bot_name:', data.bot_name);
        console.log('📄 Response data.message:', data.message);

        if (data.success) {
            if (data.responses) {
                                // Handle responses sequentially to use async/await
                for (const resp of data.responses) {
                    // For opponent responses, use bot_name field
                    const botName = resp.bot_name || resp.bot;
                    let message = resp.message;

                    // Add the text message first
                    addMessageToChat('bot', message, botName);

                    // Send GIF as a separate message if needed
                    if (shouldSendGif()) {
                        // Extract relevant search terms from the message
                        const searchTerms = extractSearchTerms(message, botName);
                        const relevantGif = await getRelevantGif(searchTerms, botName);
                        addMessageToChat('bot', relevantGif, botName, true); // true = GIF only
                    }
                }
            } else if (data.message) {
                // Try both bot and bot_name fields to handle different response formats
                const botName = data.bot || data.bot_name;
                let message = data.message;

                // Add the text message first
                addMessageToChat('bot', message, botName);

                // Send GIF as a separate message if needed
                if (shouldSendGif()) {
                    // Extract relevant search terms from the message
                    const searchTerms = extractSearchTerms(message, botName);
                    const relevantGif = await getRelevantGif(searchTerms, botName);
                    addMessageToChat('bot', relevantGif, botName, true); // true = GIF only
                }
            } else {
                addMessageToChat('bot', 'Sorry, I encountered an error. Please try again.');
            }
        } else {
            addMessageToChat('bot', 'Sorry, I\'m having trouble connecting right now.');
        }
    } catch (error) {
        console.error('❌ Chatbot error:', error);
        addMessageToChat('bot', 'Sorry, I\'m having trouble connecting right now.');
    } finally {
        // Re-enable input
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

// Add a message to the chat display
function addMessageToChat(sender, message, botName = null, gifOnly = false) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.error('Chat container #chatMessages not found!');
        return;
    }

    // If sender is 'user', treat as human; otherwise, treat as bot
    const isHuman = sender === 'user';
    const isBot = !isHuman;
    const displayBotName = botName || (isBot ? 'bot' : null);

    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message';
    if (isBot) {
        msgDiv.classList.add('bot-message');
    } else {
        msgDiv.classList.add('user-message');
    }

    // Message content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Check if message contains an image/GIF URL
    const imageRegex = /(https?:\/\/[^\s]+\.(?:gif|jpg|jpeg|png|webp))/i;
    const imageMatch = message.match(imageRegex);

    if (imageMatch && gifOnly) {
        // GIF-only message - no bubble styling
        const imageUrl = imageMatch[1];

        const imgElement = document.createElement('img');
        imgElement.src = imageUrl;
        imgElement.alt = 'Chat GIF';
        imgElement.className = 'chat-image';
        imgElement.style.maxWidth = '200px';
        imgElement.style.maxHeight = '150px';
        imgElement.style.borderRadius = '8px';
        imgElement.style.marginTop = '4px';
        imgElement.style.marginBottom = '4px';
        contentDiv.appendChild(imgElement);

        // Remove bubble styling for GIF-only messages
        contentDiv.style.background = 'transparent';
        contentDiv.style.border = 'none';
        contentDiv.style.padding = '0';
        contentDiv.style.boxShadow = 'none';

        // Remove the bubble pointer by hiding the ::after pseudo-element
        contentDiv.style.position = 'relative';
        contentDiv.style.setProperty('--hide-pointer', 'true');

    } else if (imageMatch) {
        // Mixed text and image message (legacy case)
        const imageUrl = imageMatch[1];
        const textBefore = message.substring(0, imageMatch.index).trim();
        const textAfter = message.substring(imageMatch.index + imageUrl.length).trim();

        // Create separate containers for text and image
        if (textBefore) {
            const textDiv = document.createElement('div');
            textDiv.textContent = textBefore;
            textDiv.style.marginBottom = '8px';
            contentDiv.appendChild(textDiv);
        }

        // Add image with proper styling
        const imgElement = document.createElement('img');
        imgElement.src = imageUrl;
        imgElement.alt = 'Chat image';
        imgElement.className = 'chat-image';
        imgElement.style.maxWidth = '200px';
        imgElement.style.maxHeight = '150px';
        imgElement.style.borderRadius = '8px';
        imgElement.style.marginTop = '8px';
        imgElement.style.marginBottom = '8px';
        contentDiv.appendChild(imgElement);

        if (textAfter) {
            const textDiv = document.createElement('div');
            textDiv.textContent = textAfter;
            textDiv.style.marginTop = '8px';
            contentDiv.appendChild(textDiv);
        }

        // Don't override the CSS bubble styling - let it work naturally
        // The CSS will handle the bubble background, border-radius, and pointer
    } else {
        // Regular text message
        contentDiv.textContent = message;
    }

    msgDiv.appendChild(contentDiv);

    // Show bot name below for all bot messages
    if (displayBotName && isBot) {
        const nameDivBottom = document.createElement('div');
        nameDivBottom.className = 'bot-name bot-name-bottom';
        nameDivBottom.textContent = displayBotName;
        msgDiv.appendChild(nameDivBottom);
    }

    // Optionally show user label below for user messages
    if (isHuman) {
        const nameDivBottom = document.createElement('div');
        nameDivBottom.className = 'user-name user-name-bottom';
        nameDivBottom.textContent = 'you';
        msgDiv.appendChild(nameDivBottom);
    }

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Random threshold function for GIF triggers (placeholder for future event-based system)
function shouldSendGif() {
    // Random 95% chance for now - can be replaced with event-based logic later
    return Math.random() < 0.25;
}

// Get relevant GIF from backend Giphy API
async function getRelevantGif(searchTerm, botName = null) {
    try {
        // Use the search term as the message, and get bot name from parameter or fallback
        const message = searchTerm || '';
        const botNameToUse = botName || currentPersonality || 'Jim Nantz';

        const response = await fetch('/chatbot/get_giphy_gif', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                bot_name: botNameToUse
            })
        });

        const data = await response.json();

        if (data.success && data.gif_url) {
            return data.gif_url;
        } else {
            console.error('Error from backend Giphy API:', data.error);
        }
    } catch (error) {
        console.error('Error fetching GIF from backend:', error);
    }

    // Fallback to static GIFs if API fails
    const fallbackGifs = [
        "https://media.giphy.com/media/3oriNYQX2lC6dfW2cK/giphy.gif",
        "https://media.giphy.com/media/TqiwHbFBaZ4ti/giphy.gif",
        "https://media.giphy.com/media/l0HlPystfePnAI3G8/giphy.gif"
    ];
    return fallbackGifs[Math.floor(Math.random() * fallbackGifs.length)];
}

// Extract relevant search terms from message and bot name
function extractSearchTerms(message, botName) {
    const golfTerms = ['golf', 'putt', 'drive', 'swing', 'hole', 'birdie', 'eagle', 'par', 'bogey', 'fairway', 'green', 'rough', 'sand', 'club'];
    const emotionTerms = ['amazing', 'great', 'awesome', 'wow', 'incredible', 'fantastic', 'excellent', 'perfect', 'brilliant'];
    const actionTerms = ['shot', 'hit', 'play', 'move', 'turn', 'game', 'match', 'round'];

    // Check for golf-specific terms first
    for (const term of golfTerms) {
        if (message.toLowerCase().includes(term)) {
            return `${term} golf`;
        }
    }

    // Check for emotion terms
    for (const term of emotionTerms) {
        if (message.toLowerCase().includes(term)) {
            return `${term} reaction`;
        }
    }

    // Check for action terms
    for (const term of actionTerms) {
        if (message.toLowerCase().includes(term)) {
            return `${term} golf`;
        }
    }

    // Bot-specific searches
    if (botName) {
        if (botName.includes('Peter Parker')) {
            return 'spiderman reaction';
        } else if (botName.includes('Tiger')) {
            return 'tiger woods golf';
        } else if (botName.includes('Happy')) {
            return 'happy gilmore golf';
        }
    }

    // Default fallback
    return 'golf celebration';
}

// Change chatbot personality
async function changePersonality(personalityType) {
    proactiveCommentSent = false;
    try {
        const response = await fetch('/chatbot/change_personality', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                personality_type: personalityType
            })
        });

        const data = await response.json();

        if (data.success) {
            const chatbotName = document.getElementById('chatbotName');
            if (chatbotName) {
                chatbotName.textContent = data.personality.name;
            }

            currentPersonality = personalityType;
            updateChatInputState();

            // Disable chat input for Jim Nantz
            const chatInput = document.getElementById('chatInput');
            const sendBtn = document.getElementById('sendChatBtn');
            if (personalityType === 'nantz') {
                if (chatInput) chatInput.disabled = true;
                if (sendBtn) sendBtn.disabled = true;
                // Update default message
                const chatMessages = document.getElementById('chatMessages');
                if (chatMessages) {
                    chatMessages.innerHTML = '';
                    // Removed Jim Nantz intro message
                }
            } else {
                if (chatInput) chatInput.disabled = false;
                if (sendBtn) sendBtn.disabled = false;
                // Clear chat and add welcome message
                const chatMessages = document.getElementById('chatMessages');
                if (chatMessages) {
                    chatMessages.innerHTML = '';
                    addMessageToChat('bot', `Hi! I'm ${data.personality.name}. ${data.personality.description}`);
                }
            }
        } else {
            console.error('Failed to change personality:', data.error);
        }
    } catch (error) {
        console.error('Error changing personality:', error);
    }
}



function getAllowedBotsForProactive() {
    console.log('[getAllowedBotsForProactive] function called');
    const allowed = ['Jim Nantz'];
    const chatOpponentSelect = document.getElementById('chatOpponentSelect');
    let dropdownVisible = false;
    let selected = null;
    if (chatOpponentSelect) {
        dropdownVisible = chatOpponentSelect.style.display !== 'none';
        selected = chatOpponentSelect.value;
    }
    console.log('[getAllowedBotsForProactive] Dropdown visible:', dropdownVisible, '| Selected:', selected);
    if (dropdownVisible) {
        if (selected && selected !== 'Jim Nantz') {
            if (selected === 'opponent') {
                console.log('Adding all AI player names to allowed_bots');
                if (currentGameState && currentGameState.players) {
                    for (let i = 1; i < currentGameState.players.length; i++) {
                        console.log('Adding player:', currentGameState.players[i]);
                        allowed.push(currentGameState.players[i].name);
                    }
                } else {
                    console.log('No currentGameState or players found!');
                }
            } else {
                allowed.push(selected);
            }
        }
    }
    console.log('Final allowed_bots:', allowed);
    console.log('[getAllowedBotsForProactive] currentGameStat 2670:', currentGameState);
    if (currentGameState) {
        console.log('[getAllowedBotsForProactive] Players:', currentGameState.players);
    }
    return allowed;
}

// Initialize chatbot when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM Content Loaded - initializing chatbot');

    try {
        // Test if elements exist immediately
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendChatBtn');
        const chatbotPanel = document.querySelector('.chatbot-panel');

        console.log('Initial element check:', {
            chatInput: !!chatInput,
            sendBtn: !!sendBtn,
            chatbotPanel: !!chatbotPanel
        });

        // Try to initialize
        initializeChatbot();

        // Also set up a periodic check for when the game board becomes visible
        const checkForChatbot = setInterval(() => {
            try {
                const gameBoard = document.getElementById('gameBoard');
                const chatInput = document.getElementById('chatInput');

                if (gameBoard && gameBoard.style.display !== 'none' && chatInput) {
                    console.log('🎮 Game board visible - re-initializing chatbot');
                    clearInterval(checkForChatbot);
                    initializeChatbot();

                    // Start periodic proactive comments
                    startPeriodicProactiveComments();
                }
            } catch (error) {
                console.error('❌ Error in chatbot check interval:', error);
            }
        }, 1000);

    } catch (error) {
        console.error('❌ Error in DOMContentLoaded chatbot init:', error);
    }
});

// Start periodic proactive comments
function startPeriodicProactiveComments() {
    // Clear any existing interval.
    console.log('[startPeriodicProactiveComments 2723] proactiveCommentInterval:', proactiveCommentInterval);
    if (proactiveCommentInterval) {
        clearInterval(proactiveCommentInterval);
    }

    // Start new interval - trigger proactive comments every 30-60 seconds
    window.proactiveCommentInterval = setInterval(() => {
        if (gameId && chatbotEnabled && currentGameState && !currentGameState.game_over) {
            const eventTypes = ['general', 'turn_start', 'card_played', 'score_update'];
            const randomEvent = eventTypes[Math.floor(Math.random() * eventTypes.length)];
            requestProactiveComment(randomEvent);
        }
    }, 30000 + Math.random() * 3000000); // 30-60 seconds og
}

// Also initialize chatbot when game board is shown
try {
    const originalStartGame = startGame;
    startGame = async function() {
        proactiveCommentSent = false;
        await originalStartGame();
        console.log('🎮 Game started - re-initializing chatbot');
        setTimeout(initializeChatbot, 100);
    };
} catch (error) {
    console.error('❌ Error setting up startGame override:', error);
}

// Manual test function - you can call this from console
window.testChatbot = function() {
    console.log('🧪 Manual chatbot test');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const chatbotPanel = document.querySelector('.chatbot-panel');

    console.log('Elements found:', {
        chatInput: chatInput,
        sendBtn: sendBtn,
        chatbotPanel: chatbotPanel
    });

    if (chatInput && sendBtn) {
        console.log('✅ Elements found, testing click...');
        sendBtn.click();
        console.log('Click event fired');
    } else {
        console.log('❌ Elements not found');
    }
};

// Add proactive comments to game events
const originalUpdateGameDisplay = updateGameDisplay;
updateGameDisplay = function() {
    originalUpdateGameDisplay();

    if (
        currentGameState &&
        currentGameState.action_history &&
        chatbotEnabled
    ) {
        const currentLength = currentGameState.action_history.length;
        if (currentLength > previousActionHistoryLength) {
            previousActionHistoryLength = currentLength;
            if (proactiveCommentTimeout) clearTimeout(proactiveCommentTimeout);
            proactiveCommentTimeout = setTimeout(() => {
                const now = Date.now();
                if (now - lastNantzCommentTime > 4000) { // 4s cooldown
                    console.log('Proactive comment triggered for new action');
                    requestProactiveComment('card_played');
                    lastNantzCommentTime = now;
                } else {
                    console.log('Skipped comment due to cooldown');
                }
            }, 800); // 800ms debounce window
        }
    }

    // Always trigger a summary comment when the game is over
    if (
        currentGameState &&
        currentGameState.game_over &&
        previousGameState &&
        !previousGameState.game_over &&
        chatbotEnabled
    ) {
        console.log('Proactive comment triggered for game over');
        requestProactiveComment('game_over');
    }
};



function clearChatUI() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
        if (currentPersonality === 'Jim Nantz' || currentPersonality === 'Jim Nantz') {
            // No intro message for Jim Nantz
        } else {
            addMessageToChat('bot', "Hi! I'm your golf assistant. Ask me anything about the game or strategy!");
        }
    }
    updateChatInputState();
}

function setJimNantzDefault() {
    // Jim Nantz is now the automatic commentator, not a chat option
    // So we don't need to set him as default in the dropdown
    // Just ensure chat is enabled by default
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');

    if (chatInput) {
        chatInput.disabled = false;
        chatInput.classList.remove('chat-disabled');
        chatInput.placeholder = "Ask me about the game...";
        chatInput.title = "";
    }
    if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.classList.remove('chat-disabled');
        sendBtn.title = "";
    }

    console.log('Chat enabled by default - Jim Nantz is automatic commentator');
}



function updateChatInputState() {
    console.log('updateChatInputState called. currentPersonality:', currentPersonality);
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');

    // All chat options are now interactive, no need to disable
    if (chatInput) {
        chatInput.disabled = false;
        chatInput.classList.remove('chat-disabled');
        chatInput.placeholder = "Ask me about the game...";
        chatInput.title = "";
    }
    if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.classList.remove('chat-disabled');
        sendBtn.title = "";
    }
}



function onMoveComplete(newGameState, lastAction) {
    previousGameState = deepCopy(currentGameState);
    currentGameState = newGameState;
    updateGameDisplay();

    // Trigger proactive comments based on the action
    if (chatbotEnabled) {
        if (lastAction === 'card_played') {
            requestProactiveComment('card_played');
        } else if (lastAction === 'card_drawn') {
            requestProactiveComment('card_drawn');
        } else if (lastAction === 'turn_start') {
            requestProactiveComment('turn_start');
        }

        // Check for dramatic moments
        if (currentGameState.scores && currentGameState.scores.length > 1) {
            const scoreRange = Math.max(...currentGameState.scores) - Math.min(...currentGameState.scores);
            if (scoreRange <= 2) {
                requestProactiveComment('dramatic_moment');
            }
        }
    }
}

function getSelectedChatbotPersonality() {
    return document.getElementById('chatOpponentSelect').value;
}

function updateChatInputVisibility() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const personality = getSelectedChatbotPersonality();

    // All personalities now support chat
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.style.opacity = '1';
    sendBtn.style.opacity = '1';
    chatInput.style.pointerEvents = 'auto';
    sendBtn.style.pointerEvents = 'auto';

    // Update placeholder based on personality
    const placeholders = {
        'Jim Nantz': 'Ask Jim about the game...',
        'Tiger Woods': 'Ask Tiger for advice...',
        'Happy Gilmore': 'Chat with Happy...',
        'Peter Parker': 'Ask Peter about golf...',
        'Shooter McGavin': 'Talk to Shooter...'
    };

    chatInput.placeholder = placeholders[personality] || 'Type your message...';
}

// Voice system variables
let useElevenLabs = false; // Set to false for free browser TTS
let voiceEnabled = true; // Track if voice is enabled
let speechSynthesis = window.speechSynthesis;

// Initialize voice system
console.log('🎙️ Voice system initialized');
console.log('Speech synthesis available:', !!speechSynthesis);

// Load voices asynchronously
function loadVoices() {
    if (speechSynthesis) {
        const voices = speechSynthesis.getVoices();
        console.log('Available voices:', voices.length);
        voices.forEach(voice => {
            console.log('Voice:', voice.name, voice.lang);
        });
    }
}

// Wait for voices to load
if (speechSynthesis) {
    speechSynthesis.onvoiceschanged = loadVoices;
    // Also try loading immediately in case they're already available
    loadVoices();
}



// Test function to manually test Jim Nantz voice
function testJimNantzVoice() {
    const testText = "Hello everyone, this is Jim Nantz bringing you live coverage of this exciting golf card game. What a beautiful day for golf!";
    console.log('🧪 Testing Jim Nantz voice with:', testText);

    // Check current voice status
    const voices = speechSynthesis.getVoices();
    console.log('🧪 Current available voices:', voices.length);
    voices.forEach((voice, index) => {
        console.log(`🧪 Voice ${index}:`, voice.name, voice.lang, voice.default ? '(DEFAULT)' : '');
    });

    speakJimNantzCommentary(testText);
}

// Toggle voice system on/off
function toggleVoiceSystem() {
    voiceEnabled = !voiceEnabled;
    console.log('Voice enabled:', voiceEnabled);

    // Update UI button
    const voiceToggle = document.getElementById('voiceToggle');
    if (voiceToggle) {
        voiceToggle.textContent = voiceEnabled ? '🔊 Voice: ON' : '🔇 Voice: OFF';
    }
}

// Toggle action history between minimized and expanded
function toggleActionHistory() {
    window.actionHistoryExpanded = !window.actionHistoryExpanded;

    const container = document.querySelector('.action-history-container');
    const toggle = document.querySelector('.action-history-toggle');
    const chatbotPanel = document.querySelector('.chatbot-panel');

    if (container && toggle) {
        if (window.actionHistoryExpanded) {
            container.classList.remove('action-history-minimized');
            container.classList.add('action-history-expanded');
            toggle.textContent = '▲';
            toggle.classList.add('expanded');

            // Make chatbot smaller when action history expands
            if (chatbotPanel) {
                chatbotPanel.classList.add('action-history-expanded');
            }

            // Scroll to bottom when expanding
            setTimeout(() => {
                const actionHistoryList = container.querySelector('.action-history-list');
                if (actionHistoryList) {
                    actionHistoryList.scrollTop = actionHistoryList.scrollHeight;
                }
            }, 100);
        } else {
            container.classList.remove('action-history-expanded');
            container.classList.add('action-history-minimized');
            toggle.textContent = '▼';
            toggle.classList.remove('expanded');

            // Make chatbot larger when action history collapses
            if (chatbotPanel) {
                chatbotPanel.classList.remove('action-history-expanded');
            }
        }
    }

    console.log('Action history:', window.actionHistoryExpanded ? 'expanded' : 'minimized');
}

async function requestProactiveComment(eventType = 'general') {
    console.log('[requestProactiveComment] called with eventType:', eventType);
    const allowed_bots = getAllowedBotsForProactive();
    // Example fetch:
    const payload = {
        game_id: currentGameState.game_id, // or .id, or whatever the correct property is
        event_type: eventType,
        allowed_bots: allowed_bots
    };
    console.log('[requestProactiveComment] Sending payload:', payload);
    const response = await fetch('/chatbot/proactive_comment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await response.json();
    console.log('[requestProactiveComment] Response:', data);
    // ...handle/display comments...
    if (data.comments && data.comments.length > 0) {
        data.comments.forEach(async (comment) => {
            // Add the text message first
            addMessageToChat('bot', comment.message, comment.bot_name);

            // If this is Jim Nantz, speak the commentary
            if (comment.bot_name === 'Jim Nantz' || comment.bot_name === 'jim_nantz') {
                jimNantzCommentVoice(comment.message);
            }

            // Prevent Jim Nantz from sending GIFs
            if (comment.bot_name !== 'Jim Nantz' && comment.bot_name !== 'jim_nantz' && shouldSendGif()) {
                // Extract relevant search terms from the message
                const searchTerms = extractSearchTerms(comment.message, comment.bot_name);
                const relevantGif = await getRelevantGif(searchTerms, comment.bot_name);
                addMessageToChat('bot', relevantGif, comment.bot_name, true); // true = GIF only
            }
        });
    }
}

//geting tts from topmediai api and playing it
fetch('/api/tts', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({text: "Hello Friends!"})
})
.then(response => response.json())
.then(data => {
  if (data.audio_url) {
    const audio = new Audio(data.audio_url);
    audio.play();
  } else {
    alert("TTS failed");
  }
});

// document.getElementById('tts-btn').addEventListener('click', function() {
//   fetch('/api/tts', {
//     method: 'POST',
//     headers: {'Content-Type': 'application/json'},
//     body: JSON.stringify({text: "Hello Friends!"})
//   })
//   .then(response => response.json())
//   .then(data => {
//     if (data.audio_url) {
//       const audio = new Audio(data.audio_url);
//       audio.play();
//     } else {
//       alert("TTS failed");
//     }
//   });
// });

function jimNantzCommentVoice(text) {
  fetch('/api/tts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: text})
  })
  .then(response => response.json())
  .then(data => {
    if (data.audio_url) {
      const audio = new Audio(data.audio_url);
      audio.play();
    } else {
      alert("TTS failed");
    }
  });
}

document.getElementById('sendGifBtn').addEventListener('click', function() {
  document.getElementById('gifModal').style.display = 'block';
  var gifInput = document.getElementById('gifSearchInput');
  if (gifInput && !gifInput._listenerAttached) {
    gifInput.addEventListener('keydown', async function(e) {
      console.log('Key pressed:', e.key);
      if (e.key === 'Enter') {
        e.preventDefault();
        const searchTerm = e.target.value;
        const response = await fetch('/gif/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: searchTerm })
        });
        const data = await response.json();
        const gifResults = document.getElementById('gifResults');
        gifResults.innerHTML = '';
        if (data.success && data.gif_urls && data.gif_urls.length > 0) {
          // Display multiple GIFs in a grid
          data.gif_urls.forEach(gifUrl => {
            const img = document.createElement('img');
            img.src = gifUrl;
            img.style.maxWidth = '120px';
            img.style.maxHeight = '120px';
            img.style.margin = '5px';
            img.style.cursor = 'pointer';
            img.style.borderRadius = '8px';
            img.onclick = function() {
              sendUserGifToChat(gifUrl);
              document.getElementById('gifModal').style.display = 'none';
            };
            gifResults.appendChild(img);
          });
        } else {
          gifResults.textContent = 'No GIFs found.';
        }
      }
    });
    gifInput._listenerAttached = true; // Prevent duplicate listeners
  }
});

document.getElementById('closeGifModal').addEventListener('click', function() {
  document.getElementById('gifModal').style.display = 'none';
});

document.getElementById('gifSearchBtn').addEventListener('click', async function() {
  const searchTerm = document.getElementById('gifSearchInput').value;
  const response = await fetch('/gif/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: searchTerm })
  });
  const data = await response.json();
  const gifResults = document.getElementById('gifResults');
  gifResults.innerHTML = '';
  if (data.success && data.gif_urls && data.gif_urls.length > 0) {
    // Display multiple GIFs in a grid
    data.gif_urls.forEach(gifUrl => {
      const img = document.createElement('img');
      img.src = gifUrl;
      img.style.maxWidth = '120px';
      img.style.maxHeight = '120px';
      img.style.margin = '5px';
      img.style.cursor = 'pointer';
      img.style.borderRadius = '8px';
      img.onclick = function() {
        sendUserGifToChat(gifUrl);
        document.getElementById('gifModal').style.display = 'none';
      };
      gifResults.appendChild(img);
    });
  } else {
    gifResults.textContent = 'No GIFs found.';
  }
});

function sendUserGifToChat(gifUrl) {
  // Add the GIF to the chat as a user GIF-only message
  addMessageToChat('user', gifUrl, null, true);
  // Optionally, send to backend if you want to persist or broadcast
  // fetch('/chatbot/send_user_gif', { ... })
}

document.getElementById('gifSearchInput').addEventListener('keypress', async function(e) {
  console.log('Key pressed:', e.key);
  if (e.key === 'Enter') {
    e.preventDefault();
    const searchTerm = e.target.value;
    const response = await fetch('/gif/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: searchTerm })
    });
    const data = await response.json();
    const gifResults = document.getElementById('gifResults');
    gifResults.innerHTML = '';
    if (data.success && data.gif_urls && data.gif_urls.length > 0) {
      // Display multiple GIFs in a grid
      data.gif_urls.forEach(gifUrl => {
        const img = document.createElement('img');
        img.src = gifUrl;
        img.style.maxWidth = '120px';
        img.style.maxHeight = '120px';
        img.style.margin = '5px';
        img.style.cursor = 'pointer';
        img.style.borderRadius = '8px';
        img.onclick = function() {
          sendUserGifToChat(gifUrl);
          document.getElementById('gifModal').style.display = 'none';
        };
        gifResults.appendChild(img);
      });
    } else {
      gifResults.textContent = 'No GIFs found.';
    }
  }
});

document.addEventListener('DOMContentLoaded', function() {
  var gifInput = document.getElementById('gifSearchInput');
  if (gifInput) {
    gifInput.addEventListener('keydown', async function(e) {
      console.log('Key pressed:', e.key);
      if (e.key === 'Enter') {
        e.preventDefault();
        const searchTerm = e.target.value;
        const response = await fetch('/gif/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: searchTerm })
        });
        const data = await response.json();
        const gifResults = document.getElementById('gifResults');
        gifResults.innerHTML = '';
        if (data.success && data.gif_urls && data.gif_urls.length > 0) {
          // Display multiple GIFs in a grid
          data.gif_urls.forEach(gifUrl => {
            const img = document.createElement('img');
            img.src = gifUrl;
            img.style.maxWidth = '120px';
            img.style.maxHeight = '120px';
            img.style.margin = '5px';
            img.style.cursor = 'pointer';
            img.style.borderRadius = '8px';
            img.onclick = function() {
              sendUserGifToChat(gifUrl);
              document.getElementById('gifModal').style.display = 'none';
            };
            gifResults.appendChild(img);
          });
        } else {
          gifResults.textContent = 'No GIFs found.';
        }
      }
    });
  } else {
    console.log('gifSearchInput not found!');
  }
});

