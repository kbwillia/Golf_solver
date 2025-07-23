// ===== GAME UI MODULE =====
// UI update and display management functions for the Golf Card Game

// ===== UI UPDATE FUNCTIONS =====

// Track the last game we set background for
let lastBackgroundGame = null;

function updateGameDisplay() {
    // Debug: log the current round and game values
    if (window.currentGameState) {
        console.log('updateGameDisplay: currentGameState.round =', currentGameState.round, 'current_game =', currentGameState.current_game, 'num_games =', currentGameState.num_games);
    }

    // Set background image for current game (not round) - but only when game changes
    if (window.setHoleBackground && currentGameState && currentGameState.current_game) {
        const currentGame = currentGameState.current_game;
        if (lastBackgroundGame !== currentGame) {
            console.log('Game changed from', lastBackgroundGame, 'to', currentGame, '- updating background');
            setHoleBackground(currentGame - 1);
            lastBackgroundGame = currentGame;
        }
    }
    if (!currentGameState || !currentGameState.players) return;

    try {
        // Get custom player names
        const playerNames = currentGameState.players.map(p => p.name);
        const currentPlayer = currentGameState.players[currentGameState.current_turn];
        const isHumanTurn = currentPlayer && currentGameState.current_turn === 0;

        // Show current game number and total games
        const roundDisplay = Math.min(currentGameState.round, currentGameState.max_rounds);
        let infoText = `Hole ${currentGameState.current_game || 1} of ${currentGameState.num_games || 1} | Round ${roundDisplay}/${currentGameState.max_rounds}`;

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

        // Update discard pile
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

            // console.log('🔄 UPDATED DISCARD PILE:', currentGameState.discard_top.rank + currentGameState.discard_top.suit);
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
                // console.log('🎉 Human player won! Showing celebration...');
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
                // Trigger proactive comments for score updates
                if (chatbotEnabled) {
                    requestProactiveComment('score_update');
                }
            }
            previousHumanPairs = publicPairs.slice();
        }
    }

    // console.log('DEBUG: updateGameDisplay called');
    // console.log('DEBUG: currentGameState 561:', currentGameState);
    // console.log('DEBUG: previousGameState:', previousGameState);
    // if (currentGameState && previousGameState) {
    //     console.log('DEBUG: current_player:', currentGameState.current_player, 'previous_player:', previousGameState.current_player);
    // }

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
                // Keep Nantz cooldown for immediate action responses
                if (now - lastNantzCommentTime > 4000) { // 4s cooldown for Nantz
                    // console.log('Proactive comment triggered for new action');
                    requestProactiveComment('card_played');
                    lastNantzCommentTime = now;
                } else {
                    // console.log('Skipped Nantz comment due to cooldown');
                }
                // Backend handles timing for all other bots
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
        // console.log('Proactive comment triggered for game over');
        requestProactiveComment('game_over');
    }

    // console.log('After move, action_history.length:', currentGameState.action_history.length);

    // Update the chat participants header
    updateChatParticipantsHeader();

    // Update previous game state for comparison
    previousGameState = deepCopy(currentGameState);
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

    // 🎯 DEBUG: Log player count and layout decisions
    console.log('🎯 DEBUG: Player count:', currentGameState.players.length);
    console.log('🎯 DEBUG: Player names:', currentGameState.players.map(p => p.name));

    // Add or remove grid classes based on player count
    if (currentGameState.players.length === 4) {
        container.classList.remove('three-player-grid');
        container.classList.add('four-player-grid');
        console.log('🎯 DEBUG: Applied four-player-grid class');
    } else if (currentGameState.players.length === 3) {
        container.classList.remove('four-player-grid');
        container.classList.add('three-player-grid');
        console.log('🎯 DEBUG: Applied three-player-grid class');
    } else {
        container.classList.remove('four-player-grid');
        container.classList.remove('three-player-grid');
        console.log('🎯 DEBUG: Removed all grid classes (default layout)');
    }

    // 🎯 DEBUG: Log final CSS classes
    console.log('🎯 DEBUG: Container classes:', container.className);
    console.log('🎯 DEBUG: Has three-player-grid:', container.classList.contains('three-player-grid'));
    console.log('🎯 DEBUG: Has four-player-grid:', container.classList.contains('four-player-grid'));

    // Only clear timeout and remove animation if turn index changes
    if (lastTurnIndex !== currentTurnIndex) {
        if (turnAnimateTimeout) {
            clearTimeout(turnAnimateTimeout);
            turnAnimateTimeout = null;
        }
        // Remove spinning animation from all grids
        document.querySelectorAll('.player-grid .rotating-background').forEach(bg => {
            bg.style.animation = 'none';
        });
    }

    // Create player grids
    currentGameState.players.forEach((player, playerIndex) => {
        const isCurrentTurn = playerIndex === currentGameState.current_turn;
        const isHuman = playerIndex === 0;
        const playerColor = getPlayerColor(playerIndex);

        const playerGrid = document.createElement('div');
        playerGrid.className = `player-grid ${isHuman ? 'human' : 'ai'} ${isCurrentTurn ? 'current-turn' : ''}`;
        playerGrid.setAttribute('data-player', playerIndex);

        // Add spinning background for current turn
        if (isCurrentTurn) {
            const rotatingBg = document.createElement('div');
            rotatingBg.className = 'rotating-background';
            rotatingBg.style.background = `conic-gradient(from 0deg, transparent, ${playerColor}40, transparent)`;
            playerGrid.appendChild(rotatingBg);

            // Start spinning animation after a short delay
            setTimeout(() => {
                rotatingBg.style.animation = 'spin 2s linear infinite';
            }, 100);
        }

        // Player name and score
        const playerInfo = document.createElement('div');
        playerInfo.className = 'player-info';
        playerInfo.innerHTML = `
            <div class="player-name" style="color: ${playerColor};">${player.name}</div>
            <div class="player-score">Score: ${player.score || 0}</div>
        `;
        playerGrid.appendChild(playerInfo);

        // Grid container
        const gridContainer = document.createElement('div');
        gridContainer.className = 'grid-container';

        // Create 3x3 grid
        for (let i = 0; i < 9; i++) {
            const cardSlot = document.createElement('div');
            cardSlot.className = 'card-slot';
            cardSlot.setAttribute('data-position', i);

            const card = player.grid[i];
            if (card) {
                const cardElement = document.createElement('div');
                cardElement.className = `card ${card.public ? 'face-up' : 'face-down'} ${isHuman ? 'human-card' : 'ai-card'}`;
                cardElement.setAttribute('data-position', i);

                if (card.public) {
                    cardElement.innerHTML = getCardDisplayContent(card, false);
                }

                // Add drop target functionality for human cards
                if (isHuman) {
                    cardElement.classList.add('drop-target');
                    cardElement.addEventListener('dragover', (e) => {
                        e.preventDefault();
                        if (dragActive || drawnCardDragActive) {
                            cardElement.classList.add('drag-over');
                        }
                    });
                    cardElement.addEventListener('dragleave', () => {
                        cardElement.classList.remove('drag-over');
                    });
                    cardElement.addEventListener('drop', (e) => {
                        e.preventDefault();
                        cardElement.classList.remove('drag-over');
                        handleDropOnGrid(i);
                    });
                }

                cardSlot.appendChild(cardElement);
            }

            gridContainer.appendChild(cardSlot);
        }

        playerGrid.appendChild(gridContainer);
        container.appendChild(playerGrid);
    });

    // Update turn index
    lastTurnIndex = currentTurnIndex;

    // 🎯 DEBUG: Log final DOM structure
    console.log('🎯 DEBUG: Total player grids created:', container.children.length);
    console.log('🎯 DEBUG: Player grid elements:', Array.from(container.children).map((el, i) => ({
        index: i,
        classes: el.className,
        playerIndex: el.getAttribute('data-player'),
        playerName: el.querySelector('.player-info .player-name')?.textContent || 'Unknown'
    })));
    console.log('🎯 DEBUG: Container computed style display:', getComputedStyle(container).display);
    console.log('🎯 DEBUG: Container computed grid-template-columns:', getComputedStyle(container).gridTemplateColumns);
    console.log('🎯 DEBUG: Container computed grid-template-rows:', getComputedStyle(container).gridTemplateRows);

    // Update interactivity
    const isMyTurn = currentGameState.current_turn === 0;
    setPlayerInteractivity(isMyTurn);
}

function updateGameAndRoundInfo() {
    const container = document.getElementById('GameAndRoundInfo');
    if (!container || !currentGameState) {
        return;
    }

    // Game and round info for header
    const roundDisplay = Math.min(currentGameState.round, currentGameState.max_rounds);
    const gameText = `Hole ${currentGameState.current_game || 1} of ${currentGameState.num_games || 1} | Round ${roundDisplay}/${currentGameState.max_rounds}`;

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

// ===== INTERACTIVITY FUNCTIONS =====

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

// ===== BUTTON AND HEADER FUNCTIONS =====

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

function showReplayButton(show) {
    document.getElementById('replayContainer').style.display = show ? 'block' : 'none';
}

// ===== GAME STATE UI FUNCTIONS =====

function handleGameEnd() {
    // Immediately fetch new game state, don't wait for polling
    fetch(`/game_state/${gameId}`)
        .then(response => response.json())
        .then(newState => {
            currentGameState = newState;
            updateGameDisplay(); // Force immediate UI update
        });
}

function onGameOver() {
    showReplayButton(true);
}

function onMatchOver() {
    showReplayButton(true);
}

function onGameStart() {
    showReplayButton(false);
}

// ===== UTILITY UI FUNCTIONS =====

function getPlayerColor(playerIndex) {
    const colors = ['#007bff', '#28a745', '#dc3545', '#ffc107'];
    return colors[playerIndex % colors.length];
}

function enableActionHistory() {
  const chat = document.querySelector('.action-history');
  chat.style.pointerEvents = 'auto';
  chat.style.overflow = 'auto';
  chat.style.scrollbarWidth = '';
  chat.style.msOverflowStyle = '';
}

function playGolfClap() {
    const audio = document.getElementById('golfClapAudio');
    if (audio) {
        audio.currentTime = 0;
        audio.play();
    }
}

function setDefaultBackground() {
    // Set the default background image for setup screen
    document.body.style.backgroundImage = '';
    document.body.offsetHeight; // Force reflow
    document.body.style.backgroundImage = "url('/static/4k-golf-1.jpg')";
    document.body.style.backgroundSize = 'cover';
    document.body.style.backgroundPosition = 'center';
    document.body.style.backgroundRepeat = 'no-repeat';
    document.body.style.backgroundAttachment = 'fixed';

    document.documentElement.style.backgroundImage = "url('/static/4k-golf-1.jpg')";
    document.documentElement.style.backgroundSize = 'cover';
    document.documentElement.style.backgroundPosition = 'center';

    // Remove any backgrounds from containers that might cover it
    const containers = document.querySelectorAll('.container, .setup-and-board, .header, .game-board, .main, .wrapper');
    containers.forEach(el => {
        el.style.background = 'none';
        el.style.backgroundColor = 'transparent';
    });
}
window.setDefaultBackground = setDefaultBackground;

// ===== PLACEHOLDER FUNCTIONS FOR CROSS-MODULE DEPENDENCIES =====

function getCardDisplayContent() { /* Will be implemented in cards module */ }
// updateProbabilitiesPanel() and updateCumulativeScoreChart() implemented in probabilities.js
// function showCelebrationGif() { /* Will be implemented in notifications module */ }
function updateChatParticipantsHeader() { /* Will be implemented in chatbot module */ }
function requestProactiveComment() { /* Will be implemented in chatbot module */ }
function takeDiscard() { /* Will be implemented in actions module */ }
function animateSnapToGrid() { /* Will be implemented in actions module */ }
function handleDropOnGrid() { /* Will be implemented in actions module */ }
function findAIDiscardedCard() { /* Will be implemented in core module */ }
function aiJustMoved() { /* Will be implemented in core module */ }
function deepCopy() { /* Will be implemented in core module */ }
function toggleActionHistory() { /* Will be implemented in chatbot module */ }
