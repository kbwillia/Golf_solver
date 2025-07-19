// ===== GAME CORE MODULE =====
// Core game functions and variables for the Golf Card Game

// ===== GAME CORE VARIABLES =====
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

// ===== CORE GAME FUNCTIONS =====

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
    let botValue = botNameSelect ? botNameSelect.value : 'peter_parker';

    // In 1v3 mode, if no custom bot is selected, default to peter_parker
    if (gameMode === '1v3' && (!botValue || botValue === '')) {
        botValue = 'peter_parker';
    }

    // Check if it's a custom bot
    let botName = botValue;
    let opponentType = 'random';
    let customBotInfo = null;

    if (botValue.startsWith('custom_') && window.customBots && window.customBots[botValue]) {
        // It's a custom bot
        customBotInfo = window.customBots[botValue];
        botName = customBotInfo.name;
        // Map custom difficulty to opponent type
        const difficultyToType = {
            'easy': 'random',
            'medium': 'basic_logic',
            'hard': 'ev_ai'
        };
        opponentType = difficultyToType[customBotInfo.difficulty] || 'random';
    } else {
        // It's a built-in bot
        const botNameToDifficulty = {
            'peter_parker': 'random',
            'happy_gilmore': 'basic_logic',
            'tiger_woods': 'ev_ai'
        };
        opponentType = botNameToDifficulty[botValue] || 'random';
    }

    const playerName = document.getElementById('playerName').value || 'Human';
    const numGames = parseInt(document.getElementById('numGames').value) || 1;
    cardVisibilityDuration = parseFloat(document.getElementById('cardVisibilityDuration').value) || 1.5;

    // For 1v3 mode, collect all custom bots
    let customBots1v3 = [];
    if (gameMode === '1v3' && window.customBots) {
        // Get all custom bots for 1v3 mode
        Object.values(window.customBots).forEach(bot => {
            customBots1v3.push(bot);
        });
    }

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
                num_games: numGames,
                custom_bot_info: customBotInfo,
                custom_bots_1v3: customBots1v3
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
                updateGameDisplay();
                hideSetupViewTimer();
                if (setupViewInterval) clearInterval(setupViewInterval);
            }, cardVisibilityDuration * 1000);
            updateGameDisplay();

            // Update chat participants header for new game
            updateChatParticipantsHeader();

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
    playCardShuffleSound();
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
    playCardShuffleSound();
}

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

// ===== UTILITY FUNCTIONS =====

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

// ===== TIMER FUNCTIONS =====

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

// ===== PERIODIC POLLING SETUP =====

// Periodically refresh game state to catch AI moves
setInterval(() => {
    if (gameId && currentGameState && !currentGameState.game_over && !pollingPaused) {
        refreshGameState();
    }
}, 500); // Reduced from 1000ms to 500ms for more responsive AI turns

// ===== PLACEHOLDER FUNCTIONS FOR CROSS-MODULE DEPENDENCIES =====

function clearCelebration() { /* Will be implemented in notifications module */ }
function updateGameDisplay() { /* Will be implemented in UI module */ }
// updateCumulativeScoreChart() implemented in probabilities.js
function updateChatParticipantsHeader() { /* Will be implemented in chatbot module */ }
function clearChatUI() { /* Will be implemented in chatbot module */ }
function updateChatInputState() { /* Will be implemented in chatbot module */ }
function requestProactiveComment() { /* Will be implemented in chatbot module */ }
function setJimNantzDefault() { /* Will be implemented in chatbot module */ }
function playCardShuffleSound() { /* Will be implemented in utils module */ }
function showHeaderButtons() { /* Will be implemented in UI module */ }
function hideDrawnCardArea() { /* Will be implemented in actions module */ }
function onGameStart() { /* Will be implemented in UI module */ }
