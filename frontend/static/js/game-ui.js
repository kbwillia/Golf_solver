// ===== GAME UI MODULE =====
// Handles all UI updates, display management, and interface control

console.log('🎨 Game UI loaded successfully!');

// ===== MAIN UI UPDATE FUNCTIONS =====

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
                if (now - lastNantzCommentTime > 4000) { // 4s cooldown=4000.
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

    // Update the chat participants header
    updateChatParticipantsHeader();

    // Update previous game state for comparison
    previousGameState = deepCopy(currentGameState);
}

function actuallyUpdateUI() {
    // Main UI update logic - this function is called after animations complete
    // or immediately if no animations are needed
    console.log('🔄 actuallyUpdateUI called');
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
    }, 100);
}

// ===== INTERACTIVITY MANAGEMENT =====

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

// ===== BUTTON AND HEADER MANAGEMENT =====

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

function onGameOver() {
    showReplayButton(true);
}

function onMatchOver() {
    showReplayButton(true);
}

function onGameStart() {
    showReplayButton(false);
}

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

// ===== UTILITY FUNCTIONS =====

function getPlayerColor(playerIndex) {
    const colors = ['#007bff', '#e67e22', '#28a745', '#764ba2', '#f39c12', '#e74c3c'];
    return colors[playerIndex % colors.length];
}

function enableActionHistory() {
    const chat = document.querySelector('.action-history');
    chat.style.pointerEvents = 'auto';
    chat.style.overflow = 'auto';
    chat.style.scrollbarWidth = '';
    chat.style.msOverflowStyle = '';
}

// ===== INITIALIZATION =====

// When showing setup:
showHeaderButtons(false);

// When starting the game:
showHeaderButtons(true);

document.addEventListener('DOMContentLoaded', function() {
    showHeaderButtons(false);
});

showHeaderButtons(true);

// ===== EXPORT FUNCTIONS FOR OTHER MODULES =====
// These functions will be called from other modules but defined here

// These functions will be implemented in other modules but referenced here
function getCardDisplayContent() { /* Will be implemented in cards module */ }
function updateProbabilitiesPanel() { /* Will be implemented in probabilities module */ }
function updateCumulativeScoreChart() { /* Will be implemented in probabilities module */ }
function showCelebrationGif() { /* Will be implemented in notifications module */ }
function updateChatParticipantsHeader() { /* Will be implemented in chatbot module */ }
function requestProactiveComment() { /* Will be implemented in chatbot module */ }
function playGolfClap() { /* Will be implemented in utils module */ }
function takeDiscard() { /* Will be implemented in actions module */ }
function drawFromDeck() { /* Will be implemented in actions module */ }
function flipDrawnCardOnGrid() { /* Will be implemented in actions module */ }
function handleDropOnGrid() { /* Will be implemented in actions module */ }
function animateSnapToGrid() { /* Will be implemented in actions module */ }
function findAIDiscardedCard() { /* Will be implemented in core module */ }
function aiJustMoved() { /* Will be implemented in core module */ }
function deepCopy() { /* Will be implemented in core module */ }
function toggleActionHistory() { /* Will be implemented in chatbot module */ }