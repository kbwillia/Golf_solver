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
let currentPersonality = 'nantz';

let lastNantzCommentTime = 0; // Place this at the top of your JS file if not already present
let lastNantzTurn = null;
let proactiveCommentTimeout = null;

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
                // .map(gif => gif.images && gif.images.downsized_medium && gif.images.adfdownsized_medium.url)
                .map(gif => gif.images && gif.images.downsized_large && gif.images.downsized_large.url)

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
            `;
            youWonMessage.innerHTML = '🎉 You Won! 🎉';

            // Insert between title and buttons
            const headerButtons = document.getElementById('headerButtons');
            if (headerButtons) {
                header.insertBefore(youWonMessage, headerButtons);
            } else {
                header.appendChild(youWonMessage);
            }
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
        // Update combined scores and round info display
        updateScoresAndRoundInfo();
        // Update probabilities panel
        updateProbabilitiesPanel();

        // Update cumulative score chart (only if game state changed)
        updateCumulativeScoreChart();

        // Update Next Hole button visibility
        updateNextHoleButton();

        // Check if game or match is over and show replay button
        if (currentGameState.game_over) {
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
    console.log('DEBUG: currentGameState:', currentGameState);
    console.log('DEBUG: previousGameState:', previousGameState);
    if (currentGameState && previousGameState) {
        console.log('DEBUG: current_player:', currentGameState.current_player, 'previous_player:', previousGameState.current_player);
    }

    if (
        currentGameState &&
        currentGameState.action_history &&
        currentPersonality === 'nantz'
    ) {
        const currentLength = currentGameState.action_history.length;
        if (currentLength > previousActionHistoryLength) {
            previousActionHistoryLength = currentLength;
            if (proactiveCommentTimeout) clearTimeout(proactiveCommentTimeout);
            proactiveCommentTimeout = setTimeout(() => {
                const now = Date.now();
                if (now - lastNantzCommentTime > 4000) { // 4s cooldown
                    console.log('Jim Nantz: Proactive comment triggered for new action');
                    requestProactiveComment('card_played');
                    lastNantzCommentTime = now;
                } else {
                    console.log('Jim Nantz: Skipped comment due to cooldown');
                }
            }, 800); // 600ms debounce window
        }
    }

    // Always trigger a summary comment when the game is over
    if (
        currentGameState &&
        currentGameState.game_over &&
        previousGameState &&
        !previousGameState.game_over &&
        currentPersonality === 'nantz'
    ) {
        console.log('Jim Nantz: Proactive comment triggered for game over');
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
        // Remove player names and scores from gameplay area - now in notification area
        playerDiv.innerHTML = `
            <div class="grid-container">${gridHtml}</div>
        `;
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

function updateScoresAndRoundInfo() {
    // Debug the game state when game is over
    if (currentGameState.game_over) {
        console.log('🎮 GAME OVER DEBUG:', {
            winner: currentGameState.winner,
            scores: currentGameState.scores,
            public_scores: currentGameState.public_scores,
            match_winner: currentGameState.match_winner,
            players: currentGameState.players.map(p => p.name)
        });
    }
    const container = document.getElementById('ScoresAndRoundInfo');
    if (!container || !currentGameState || !currentGameState.players) {
        return;
    }

    // Info text (round/game info)
    const roundDisplay = Math.min(currentGameState.round, currentGameState.max_rounds);
    let infoText = `<div class="round-info" style="font-weight:bold; font-size:1.1em;">Game ${currentGameState.current_game || 1} of ${currentGameState.num_games || 1} | Round ${roundDisplay}/${currentGameState.max_rounds}&nbsp;&nbsp;Scores</div>`;

    // Scores
    const isMultiGame = (currentGameState.num_games && currentGameState.num_games > 1);
    let scoresHtml = '<div class="scores-panel">';
    scoresHtml += '<table class="scores-table">';
    scoresHtml += '<tr class="scores-subheader">';
    scoresHtml += '<th></th><th>Current</th>';
    if (isMultiGame) {
        scoresHtml += '<th>Total</th>';
    }
    scoresHtml += '</tr>';
    currentGameState.players.forEach((player, index) => {
        let displayName = player.name;
        // Remove agent_type label logic: always use player.name
        let scoreText = 'Hidden';
        let winnerIcon = '';
        if (currentGameState.public_scores && typeof currentGameState.public_scores[index] !== 'undefined') {
            scoreText = currentGameState.public_scores[index];
            if (currentGameState.game_over && index === currentGameState.winner) {
                winnerIcon = ' 🏆🏆🏆';
                // Show celebration GIF if human (player 0) wins the game
                if (index === 0) {
                    console.log(`🎉 GAME WIN: Human won! Winner: ${currentGameState.winner}, Player index: ${index}, Scores: ${JSON.stringify(currentGameState.scores)}`);
                    showCelebrationGif();
                } else {
                    console.log(`🏆 GAME WIN: AI won! Winner: ${currentGameState.winner}, Player index: ${index}, Scores: ${JSON.stringify(currentGameState.scores)}`);
                }
            }
        }
        // Cumulative score (if multi-game)
        let cumulativeText = '';
        if (isMultiGame && currentGameState.cumulative_scores && typeof currentGameState.cumulative_scores[index] !== 'undefined') {
            cumulativeText = currentGameState.cumulative_scores[index];
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
        scoresHtml += `<tr class="score-item${isCurrentTurn ? ' current-turn-score' : ''}">` +
            `<td style="text-align:left;"><strong>${displayName}:</strong>${winnerIcon}${turnIndicator}</td>` +
            `<td style="text-align:right;">${scoreText}</td>`;
        if (isMultiGame) {
            scoresHtml += `<td style="text-align:right;">${cumulativeText}</td>`;
        }
        scoresHtml += `</tr>`;
    });
    scoresHtml += '</table></div>';

    // Check for overall match winner (multi-game) and show celebration
    if (currentGameState.match_winner && currentGameState.match_winner.includes && currentGameState.match_winner.includes(0)) {
        if (currentGameState.match_winner.length === 1 && currentGameState.match_winner[0] === 0) {
            // Human is the sole winner
            console.log(`🏆 MATCH WIN: Human won overall match! Match winner: ${currentGameState.match_winner}`);
            showCelebrationGif();
        } else {
            // It's a tie or human is not the sole winner
            console.log(`🤝 MATCH TIE: Match ended in tie! Match winner: ${currentGameState.match_winner}`);
        }
    }

    // Last action display
    let lastActionHtml = '';
    if (currentGameState.last_action) {
        lastActionHtml = `
            <div class="last-action-panel">
                <div class="last-action-header">Last Action:</div>
                <div class="last-action-text">${currentGameState.last_action}</div>
            </div>
        `;
    }

    // Action history display (scrollable)
    let actionHistoryHtml = '';
    if (currentGameState.action_history && currentGameState.action_history.length > 0) {
        actionHistoryHtml = `
            <div class="action-history-panel">
                <div class="last-action-header">Action History:</div>
                <div class="action-history-list" id="actionHistoryList">
                    ${currentGameState.action_history.map(action => `<div class="action-history-item">${action}</div>`).join('')}
                </div>
            </div>
        `;
    }

    // Auto-scroll action history to bottom
    const actionHistoryPanel = container.querySelector('.action-history-panel');
    if (actionHistoryPanel) {
        actionHistoryPanel.scrollTop = actionHistoryPanel.scrollHeight;
    }

    // Flex row: round info left, scores right
    let flexRowHtml = `<div class="scores-round-flex">${infoText}${scoresHtml}</div>`;

    container.innerHTML = flexRowHtml + actionHistoryHtml; // Remove + buttonsHtml

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
                    position: 'right',
                    labels: {
                        boxWidth: 10,
                        padding: 4,
                        usePointStyle: true,
                        font: {
                            size: 10
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
    if (currentPersonality === 'nantz') {
        addMessageToChat('bot', "Jim Nantz only provides live commentary. Enjoy the broadcast!");
        return;
    }
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
        const data = await response.json();
        console.log('📄 Response data:', data);

        if (data.success) {
            if (data.responses) {
                data.responses.forEach(resp => {
                    addMessageToChat('bot', resp.message, resp.bot); // ✅ CORRECT
                });
            } else if (data.message) {
                addMessageToChat('bot', data.message);
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
function addMessageToChat(sender, message, botName = null) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    // Always use 'bot-message' for all bots
    let messageClass = 'message';
    if (sender === 'bot') {
        messageClass += ' bot-message';
    } else if (sender === 'user') {
        messageClass += ' user-message';
    } else {
        messageClass += ` ${sender}-message`; // Only for other types, if needed
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = messageClass;

    // Optionally show bot name
    if (botName && sender === 'bot') {
        const nameDiv = document.createElement('div');
        nameDiv.className = 'bot-name';
        nameDiv.textContent = botName;
        messageDiv.appendChild(nameDiv);
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = message;

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
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

// Request proactive comment from chatbot
async function requestProactiveComment(eventType = 'general') {
    if (!gameId || !chatbotEnabled) {
        console.log('Proactive comment skipped: gameId or chatbot not enabled');
        return;
    }

    console.log('Requesting proactive comment for event:', eventType);

    try {
        const response = await fetch('/chatbot/proactive_comment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_id: gameId,
                event_type: eventType
            })
        });

        const data = await response.json();
        console.log('Proactive comment response:', data);

        if (data.success && data.comment) {
            addMessageToChat('bot', data.comment, data.bot_name);
        } else if (data.success && !data.comment) {
            console.log('Proactive comment: No comment generated (30% chance)');
        } else {
            console.error('Proactive comment failed:', data.error);
        }
    } catch (error) {
        console.error('Error requesting proactive comment:', error);
    }
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
                }
            } catch (error) {
                console.error('❌ Error in chatbot check interval:', error);
            }
        }, 1000);

    } catch (error) {
        console.error('❌ Error in DOMContentLoaded chatbot init:', error);
    }
});

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
        currentPersonality === 'nantz'
    ) {
        const currentLength = currentGameState.action_history.length;
        if (currentLength > previousActionHistoryLength) {
            previousActionHistoryLength = currentLength;
            if (proactiveCommentTimeout) clearTimeout(proactiveCommentTimeout);
            proactiveCommentTimeout = setTimeout(() => {
                const now = Date.now();
                if (now - lastNantzCommentTime > 4000) { // 4s cooldown
                    console.log('Jim Nantz: Proactive comment triggered for new action');
                    requestProactiveComment('card_played');
                    lastNantzCommentTime = now;
                } else {
                    console.log('Jim Nantz: Skipped comment due to cooldown');
                }
            }, 800); // 600ms debounce window
        }
    }

    // Always trigger a summary comment when the game is over
    if (
        currentGameState &&
        currentGameState.game_over &&
        previousGameState &&
        !previousGameState.game_over &&
        currentPersonality === 'nantz'
    ) {
        console.log('Jim Nantz: Proactive comment triggered for game over');
        requestProactiveComment('game_over');
    }
};

// Final test to ensure script loaded
// try {
//     console.log('🎯 Golf.js initialization complete!');
//     console.log('Type "testChatbot()" in console to test chatbot functionality');
// } catch (error) {
//     console.error('❌ Error in final initialization:', error);
// }

// let proactiveCommentSent = false;

function clearChatUI() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
        if (currentPersonality === 'nantz') {
            // No intro message for Jim Nantz
        } else {
            addMessageToChat('bot', "Hi! I'm your golf assistant. Ask me anything about the game or strategy!");
        }
    }
    updateChatInputState();
}

function setJimNantzDefault() {
    const personalitySelect = document.getElementById('personalitySelect');
    if (personalitySelect) {
        personalitySelect.value = 'nantz';
        currentPersonality = 'nantz'; // Ensure JS variable is in sync
        console.log('Jim Nantz: Set as default personality');
        // Trigger the change event to update UI and logic
        const event = new Event('change');
        personalitySelect.dispatchEvent(event);
    }
    updateChatInputState();
}

// document.addEventListener('DOMContentLoaded', function() {
//     setJimNantzDefault();
// });

function updateChatInputState() {
    console.log('updateChatInputState called. currentPersonality:', currentPersonality);
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    if (currentPersonality === 'nantz') {
        if (chatInput) {
            chatInput.disabled = true;
            chatInput.classList.add('chat-disabled');
            chatInput.placeholder = "Jim Nantz is announcing, not chatting.";
            chatInput.title = "Jim Nantz is announcing, not chatting.";
        }
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.classList.add('chat-disabled');
            sendBtn.title = "Jim Nantz is announcing, not chatting.";
        }
    } else {
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
}

// document.getElementById('chatbot-personality').value = 'nantz';

// const personalitySelect = document.getElementById('personalitySelect');
// if (personalitySelect) {
//     personalitySelect.value = 'nantz';
//     currentPersonality = 'nantz';
// }

function onMoveComplete(newGameState, lastAction) {
    previousGameState = deepCopy(currentGameState);
    currentGameState = newGameState;
    updateGameDisplay();

    // Trigger Jim Nantz commentary based on the action
    if (currentPersonality === 'nantz') {
        if (lastAction === 'card_played') {
            requestProactiveComment('card_played');
        } else if (lastAction === 'card_drawn') {
            requestProactiveComment('card_drawn');
        } else if (lastAction === 'turn_start') {
            requestProactiveComment('turn_start');
        }
        // ...add more as needed
    }
}

function getSelectedChatbotPersonality() {
    return document.getElementById('chatOpponentSelect').value;
}

