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
let cardDrawnFromDeck = false; // Track if a card was drawn from deck and needs to be resolved
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

// (setDefaultBackground moved to game-ui.js)

async function startGame() {
    // Hide setup columns and AI bot image container
    const setupColumns = document.getElementById('setupColumns');
    if (setupColumns) setupColumns.style.display = 'none';
    const aiBotImageContainer = document.getElementById('aiBotImageContainer');
    if (aiBotImageContainer) aiBotImageContainer.style.display = 'none';
    // Set background for first hole
    if (window.setHoleBackground) setHoleBackground(0);
    // Reset turn tracking for new game
    lastTurnIndex = null;

    // Reset AI turn flag
    aiTurnInProgress = false;

    // Clear any existing celebrations when starting new game
    clearCelebration();

    // Hide replay button when starting new game
    onGameStart();

    // Reset chart data for new game
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

    // Get game mode from buttons instead of dropdown
    const gameMode = getCurrentGameMode();

    // Validate that at least one bot is selected
    if (!gameMode || !window.selectedBots || window.selectedBots.length === 0) {
        alert('Please select at least 1 AI opponent to start a game!');
        return;
    }

    const playerName = document.getElementById('playerName').value || 'Human';
    const numGames = getCurrentHoles();
    cardVisibilityDuration = parseFloat(document.getElementById('cardVisibilityDuration').value) || 1.5;

    console.log('🎯 Frontend: Starting game with mode:', gameMode);
    console.log('🎯 Frontend: Selected bots:', window.selectedBots);
    console.log('🎯 Frontend: Auto-detected mode from', window.selectedBots?.length || 0, 'selected bots');

    // Prepare game data
    const gameData = {
        player_name: playerName,
        num_games: numGames,
        selected_bots: window.selectedBots // Each is a full bot object from Supabase
    };

    // Debug: Log all attributes of selected_bots being sent to backend
    console.log('🚀 Sending selected_bots to backend:', JSON.stringify(gameData.selected_bots, null, 2));

    console.log('🎯 Frontend: Final gameData being sent to backend:', gameData);

    try {
        const response = await fetch('/create_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(gameData)
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
            // Trigger proactive comments for turn start - Nantz responds immediately, others via backend timing
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
    console.log('🔄 restartGame: New Game button pressed. turn tracking');
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

    // Reset background to default setup background
    if (window.setDefaultBackground) window.setDefaultBackground();

    // ===== NEW: Reset all setup fields to defaults =====
    window.selectedBots = [];
    setGameMode('1v1'); // Default game mode
    document.getElementById('playerName').value = 'Kyle';
    document.getElementById('cardVisibilityDuration').value = 1.5;
    setHoles(1); // Default to 1 hole
    // Update bot selection UI
    if (typeof renderBotSelectRow === 'function') renderBotSelectRow();
    // Update game mode buttons UI
    if (typeof setGameMode === 'function') setGameMode('1v1');
    // Update holes buttons UI
    if (typeof setHoles === 'function') setHoles(1);
    // Optionally reset any other setup fields here

    // Show setup columns and AI bot image container
    const setupColumns = document.getElementById('setupColumns');
    if (setupColumns) setupColumns.style.display = 'flex';
    const aiBotImageContainer = document.getElementById('aiBotImageContainer');
    if (aiBotImageContainer) aiBotImageContainer.style.display = 'block';

    // Re-initialize setup UI
    if (typeof renderBotSelectRow === 'function') renderBotSelectRow();
    if (typeof initializeGameModeButtons === 'function') initializeGameModeButtons();
    if (typeof initializeHolesButtons === 'function') initializeHolesButtons();
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

    // ===== NEW: Restore last game settings for replay =====
    if (currentGameState) {
        // Restore selected bots
        if (currentGameState.selected_bots) {
            window.selectedBots = [...currentGameState.selected_bots];
        }
        // Restore game mode
        if (currentGameState.mode) {
            setGameMode(currentGameState.mode);
        }
        // Restore player name
        if (currentGameState.players && currentGameState.players[0] && currentGameState.players[0].name) {
            document.getElementById('playerName').value = currentGameState.players[0].name;
        }
        // Restore number of holes
        if (currentGameState.num_games) {
            setHoles(currentGameState.num_games);
        }
        // Restore card visibility duration if available
        if (typeof currentGameState.card_visibility_duration !== 'undefined') {
            document.getElementById('cardVisibilityDuration').value = currentGameState.card_visibility_duration;
        }
        // Update bot selection UI
        if (typeof renderBotSelectRow === 'function') renderBotSelectRow();
    }

    // Start a new game with the same settings
    startGame();

    // Clear chat for single game mode
    if (currentGameState && (currentGameState.num_games === 1 || !currentGameState.num_games)) {
        clearChatUI();
    }
    // else: multi-hole match, do NOT clear chat

    previousActionHistoryLength = 0;
    lastNantzCommentTime = 0;
    if (proactiveCommentTimeout) clearTimeout(proactiveCommentTimeout);
    proactiveCommentTimeout = null;
}

async function nextGame() {
    clearCelebration(); // Hide You Won banner and celebration gif at the start of next game
    if (!gameId) {
        console.error('No game ID available');
        return;
    }

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
        // Prepare game data
        const gameData = {
            mode: gameMode,
            opponent: opponentType,
            player_name: playerName,
            num_games: numGames
        };

        // Add custom bot information for 1v3 mode
        if (gameMode === '1v3') {
            // For 1v3 mode, get all saved custom bots and use them
            try {
                const response = await fetch('/get_custom_bots');
                const data = await response.json();

                console.log('🎯 Frontend: get_custom_bots response:', data);

                if (data.success && data.bots && data.bots.length > 0) {
                    // Use up to 3 custom bots for 1v3 mode
                    const customBots = data.bots.slice(0, 3).map(bot => ({
                        id: bot.id,
                        name: bot.name,
                        difficulty: bot.difficulty
                    }));

                    gameData.custom_bots_1v3 = customBots;
                    console.log('🎯 Frontend: Using saved custom bots for 1v3 mode:', customBots);
                } else {
                    console.log('🎯 Frontend: No custom bots found, using default AI opponents for 1v3 mode');
                }
            } catch (error) {
                console.log('🎯 Frontend: Error loading custom bots, using default AI opponents:', error);
            }
        } else {
            // 1v1 mode - handle single opponent using bot selection buttons
            const selectedBots = window.selectedBots || ['peter_parker'];
            const selectedBotValue = selectedBots[0]; // Use first selected bot for 1v1

            console.log('🎯 Frontend: Selected bot for 1v1:', selectedBotValue);

            // Check if it's a custom bot
            let botName = selectedBotValue;
            let customBotInfo = null;

            if (selectedBotValue.startsWith('custom_')) {
                // It's a custom bot - get its data from JSON
                try {
                    const response = await fetch('/static/custom_bot.json');
                    const data = await response.json();

                    // Check placeholder_bots first
                    if (data.placeholder_bots) {
                        console.log('🎯 Frontend: Searching placeholder_bots for:', selectedBotValue);
                        const selectedBot = data.placeholder_bots.find(bot => {
                            const generatedId = 'custom_' + bot.name.toLowerCase().replace(' ', '_').replace('-', '_');
                            console.log('🎯 Frontend: Checking bot:', bot.name, 'generated ID:', generatedId, 'matches:', generatedId === selectedBotValue);
                            return generatedId === selectedBotValue;
                        });

                        if (selectedBot) {
                            customBotInfo = {
                                name: selectedBot.name,
                                difficulty: selectedBot.difficulty,
                                description: selectedBot.description
                            };
                            botName = selectedBot.name;
                            // Map custom difficulty to opponent type
                            const difficultyToType = {
                                'easy': 'random',
                                'medium': 'heuristic',
                                'hard': 'ev_ai'
                            };
                            opponentType = difficultyToType[selectedBot.difficulty] || 'random';
                            console.log('🎯 Frontend: Found custom bot in placeholder_bots:', selectedBot.name);
                        }
                    }

                    // Check custom_bots if not found in placeholder_bots
                    if (!customBotInfo && data.custom_bots) {
                        console.log('🎯 Frontend: Searching custom_bots for:', selectedBotValue);
                        console.log('🎯 Frontend: Available custom_bots keys:', Object.keys(data.custom_bots));
                        const selectedBot = data.custom_bots[selectedBotValue];
                        if (selectedBot) {
                            customBotInfo = {
                                name: selectedBot.name,
                                difficulty: selectedBot.difficulty,
                                description: selectedBot.description
                            };
                            botName = selectedBot.name;
                            // Map custom difficulty to opponent type
                            const difficultyToType = {
                                'easy': 'random',
                                'medium': 'heuristic',
                                'hard': 'ev_ai'
                            };
                            opponentType = difficultyToType[selectedBot.difficulty] || 'random';
                            console.log('🎯 Frontend: Found custom bot in custom_bots:', selectedBot.name);
                        } else {
                            console.log('🎯 Frontend: Custom bot not found in custom_bots object');
                        }
                    }

                    if (!customBotInfo) {
                        console.log('🎯 Frontend: Custom bot not found, falling back to random');
                        await useRandomBotFor1v1(gameData);
                        return;
                    }
                } catch (error) {
                    console.log('🎯 Frontend: Error loading custom bot for 1v1:', error);
                    await useRandomBotFor1v1(gameData);
                    return;
                }
            } else {
                // It's a built-in bot
                const botNameToDifficulty = {
                    'peter_parker': 'random',
                    'happy_gilmore': 'heuristic',
                    'tiger_woods': 'ev_ai'
                };
                opponentType = botNameToDifficulty[selectedBotValue] || 'random';
                const botNames = {
                    'peter_parker': 'Peter Parker',
                    'happy_gilmore': 'Happy Gilmore',
                    'tiger_woods': 'Tiger Woods'
                };
                botName = botNames[selectedBotValue] || 'AI Opponent';
            }

            gameData.opponent = opponentType;
            gameData.bot_name = botName;
            if (customBotInfo) {
                gameData.custom_bot_info = customBotInfo;
            }

            console.log('🎯 Frontend: Final 1v1 gameData:', {
                opponent: gameData.opponent,
                bot_name: gameData.bot_name,
                custom_bot_info: gameData.custom_bot_info
            });
        }

        console.log('🎯 Frontend: Final gameData being sent to backend:', gameData);

        const response = await fetch('/create_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(gameData)
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
    // console.log('🤖 pollAITurns called - current_turn:', currentGameState?.current_turn, 'game_over:', currentGameState?.game_over, 'aiTurnInProgress:', aiTurnInProgress);

    // Prevent multiple concurrent AI turn polling
    if (aiTurnInProgress) {
        // console.log('🤖 AI turn already in progress, skipping...');
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
                // console.log('🤖 AI turn successful, updating game state');
                currentGameState = data.game_state;
                updateGameDisplay();

                // If there's another AI turn needed, schedule it after a delay
                if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
                    // console.log('🤖 Scheduling next AI turn after delay...');
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
    // console.log('🤖 pollAITurns finished - current_turn:', currentGameState?.current_turn, 'aiTurnInProgress:', aiTurnInProgress);
}

// Helper function to use a random bot for 1v1 mode
async function useRandomBotFor1v1(gameData) {
    try {
        const randomBots = await getRandomBotsFromJSON(1);

        if (randomBots.length > 0) {
            const randomBot = randomBots[0];

            // Map custom difficulty to opponent type
            const difficultyToType = {
                'easy': 'random',
                'medium': 'heuristic',
                'hard': 'ev_ai'
            };
            const opponentType = difficultyToType[randomBot.difficulty] || 'random';

            gameData.opponent = opponentType;
            gameData.bot_name = randomBot.name;
            gameData.custom_bot_info = {
                name: randomBot.name,
                difficulty: randomBot.difficulty,
                description: randomBot.description
            };

            // console.log('🎯 Frontend: Using random bot for 1v1 mode:', randomBot.name);
        } else {
            // Fallback to default bot if no random bots found
            const selectedBots = window.selectedBots || ['peter_parker'];
            const botValue = selectedBots[0];

            const botNameToDifficulty = {
                'peter_parker': 'random',
                'happy_gilmore': 'heuristic',
                'tiger_woods': 'ev_ai'
            };
            const opponentType = botNameToDifficulty[botValue] || 'random';

            const botNames = {
                'peter_parker': 'Peter Parker',
                'happy_gilmore': 'Happy Gilmore',
                'tiger_woods': 'Tiger Woods'
            };

            gameData.opponent = opponentType;
            gameData.bot_name = botNames[botValue] || 'AI Opponent';

            // console.log('🎯 Frontend: Using default bot for 1v1 mode:', gameData.bot_name);
        }
    } catch (error) {
        console.log('🎯 Frontend: Error loading random bot for 1v1, using default:', error);

        // Fallback to default bot
        const selectedBots = window.selectedBots || ['peter_parker'];
        const botValue = selectedBots[0];

        const botNameToDifficulty = {
            'peter_parker': 'random',
            'happy_gilmore': 'heuristic',
            'tiger_woods': 'ev_ai'
        };
        const opponentType = botNameToDifficulty[botValue] || 'random';

        const botNames = {
            'peter_parker': 'Peter Parker',
            'happy_gilmore': 'Happy Gilmore',
            'tiger_woods': 'Tiger Woods'
        };

        gameData.opponent = opponentType;
        gameData.bot_name = botNames[botValue] || 'AI Opponent';
    }
}

// Function to randomly select bots from custom_bot.json
async function getRandomBotsFromJSON(count = 3) {
    try {
        const response = await fetch('/static/custom_bot.json');
        const data = await response.json();

        if (!data.placeholder_bots || data.placeholder_bots.length === 0) {
            console.log('🎯 No placeholder bots found in JSON, using default AI opponents');
            return [];
        }

        // Shuffle the array and take the first 'count' bots
        const shuffled = [...data.placeholder_bots].sort(() => 0.5 - Math.random());
        const selectedBots = shuffled.slice(0, count);

        console.log(`🎯 Randomly selected ${selectedBots.length} bots from JSON:`, selectedBots);
        return selectedBots;
    } catch (error) {
        console.log('🎯 Error loading random bots from JSON:', error);
        return [];
    }
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

// Initialize game mode buttons
function initializeGameModeButtons() {
    const gameMode1v1 = document.getElementById('gameMode1v1');
    const gameMode1v2 = document.getElementById('gameMode1v2');
    const gameMode1v3 = document.getElementById('gameMode1v3');

    console.log('🔍 Button check:', {
        '1v1': !!gameMode1v1,
        '1v2': !!gameMode1v2,
        '1v3': !!gameMode1v3
    });

    if (gameMode1v1) {
        gameMode1v1.addEventListener('click', function() { setGameMode('1v1'); });
    }
    if (gameMode1v2) {
        gameMode1v2.addEventListener('click', function() {
            console.log('🎯 1v2 mode button clicked!');
            setGameMode('1v2');
        });
    }
    if (gameMode1v3) {
        gameMode1v3.addEventListener('click', function() { setGameMode('1v3'); });
    }
}

// Set game mode and update button states
function setGameMode(mode) {
    const gameMode1v1Btn = document.getElementById('gameMode1v1');
    const gameMode1v2Btn = document.getElementById('gameMode1v2');
    const gameMode1v3Btn = document.getElementById('gameMode1v3');

    // Update button states
    if (gameMode1v1Btn && gameMode1v2Btn && gameMode1v3Btn) {
        gameMode1v1Btn.classList.remove('active');
        gameMode1v2Btn.classList.remove('active');
        gameMode1v3Btn.classList.remove('active');

        if (mode === '1v1') {
            gameMode1v1Btn.classList.add('active');
        } else if (mode === '1v2') {
            gameMode1v2Btn.classList.add('active');
        } else if (mode === '1v3') {
            gameMode1v3Btn.classList.add('active');
        }
    }

    console.log('🎯 Game mode set to:', mode);
}

// Get current game mode based on selected bots
function getCurrentGameMode() {
    const selectedCount = window.selectedBots ? window.selectedBots.length : 0;

    if (selectedCount === 0) {
        return null; // No game mode if no bots selected
    } else if (selectedCount === 1) {
        return '1v1';
    } else if (selectedCount === 2) {
        return '1v2';
    } else if (selectedCount >= 3) {
        return '1v3';
    } else {
        return '1v1'; // Default fallback
    }
}

// Initialize holes buttons
function initializeHolesButtons() {
    const holes1Btn = document.getElementById('holes1');
    const holes3Btn = document.getElementById('holes3');
    const holes9Btn = document.getElementById('holes9');
    const holes18Btn = document.getElementById('holes18');

    if (holes1Btn && holes3Btn && holes9Btn && holes18Btn) {
        holes1Btn.addEventListener('click', function() {
            setHoles(1);
        });

        holes3Btn.addEventListener('click', function() {
            setHoles(3);
        });

        holes9Btn.addEventListener('click', function() {
            setHoles(9);
        });

        holes18Btn.addEventListener('click', function() {
            setHoles(18);
        });
    }
}

// Set number of holes and update button states
function setHoles(holes) {
    const holes1Btn = document.getElementById('holes1');
    const holes3Btn = document.getElementById('holes3');
    const holes9Btn = document.getElementById('holes9');
    const holes18Btn = document.getElementById('holes18');

    // Update button states
    if (holes1Btn && holes3Btn && holes9Btn && holes18Btn) {
        holes1Btn.classList.remove('active');
        holes3Btn.classList.remove('active');
        holes9Btn.classList.remove('active');
        holes18Btn.classList.remove('active');

        if (holes === 1) {
            holes1Btn.classList.add('active');
        } else if (holes === 3) {
            holes3Btn.classList.add('active');
        } else if (holes === 9) {
            holes9Btn.classList.add('active');
        } else if (holes === 18) {
            holes18Btn.classList.add('active');
        }
    }

    console.log('🎯 Number of holes set to:', holes);
}

// Get current number of holes
function getCurrentHoles() {
    const activeBtn = document.querySelector('.holes-btn.active');
    return activeBtn ? parseInt(activeBtn.getAttribute('data-holes')) : 1;
}

const holeBackgrounds = [
  '/static/masters_images/H_hole1__Hole_1_-_Tea_Olive.jpg',
  '/static/masters_images/H_hole2__Hole_2_-_Pink_Dogwood.jpg',
  '/static/masters_images/H_hole3__Hole_3_-_Flowering_Peach.jpg',
  '/static/masters_images/H_hole4__Hole_4_-_Flowering_Crab_Apple.jpg',
  '/static/masters_images/H_hole5__Hole_5_-_Magnolia.jpg',
  '/static/masters_images/H_hole6__Hole_6_-_Juniper.jpg',
  '/static/masters_images/H_hole7__Hole_7_-_Pampas.jpg',
  '/static/masters_images/H_hole8__Hole_8_-_Yellow_Jasmine.jpg',
  '/static/masters_images/H_hole9__Hole_9_-_Carolina_Cherry.jpg',
  '/static/masters_images/H_hole10__Hole_10_-_Camellia.jpg',
  '/static/masters_images/H_hole11__Hole_11_-_White_Dogwood.jpg',
  '/static/masters_images/H_hole12__Hole_12_-_Golden_Bell.jpg',
  '/static/masters_images/H_hole13__Hole_13_-_Azalea.jpg',
  '/static/masters_images/H_hole14__Hole_14_-_Chinese_Fir.jpg',
  '/static/masters_images/H_hole15__Hole_15_-_Firethorn.jpg',
  '/static/masters_images/H_hole16__Hole_16_-_Redbud.jpg',
  '/static/masters_images/H_hole17__Hole_17_-_Nandina.jpg',
  '/static/masters_images/H_hole18__Hole_18_-_Holly.jpg',
];

function setHoleBackground(holeIndex) {
    const img = holeBackgrounds[holeIndex % holeBackgrounds.length];
    const body = document.body;
    const html = document.documentElement;
    // Set background image directly, no transition
    body.style.backgroundImage = `url('${img}')`;
    body.style.backgroundSize = 'cover';
    body.style.backgroundPosition = 'center';
    body.style.backgroundRepeat = 'no-repeat';
    body.style.backgroundAttachment = 'fixed';
    html.style.backgroundImage = `url('${img}')`;
    html.style.backgroundSize = 'cover';
    html.style.backgroundPosition = 'center';
    // Remove any backgrounds from containers that might cover it
    document.querySelectorAll('.gameBoard, .gameplay-area, .main-content, .container, .content').forEach(el => {
        el.style.background = 'none';
        el.style.backgroundColor = 'transparent';
    });
    console.log('Background should now be set to:', img);
}

