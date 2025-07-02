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
const SETUP_VIEW_SECONDS = 1.2; // Change this value for how long to show bottom cards
let setupViewInterval = null; // Interval for setup view timer
const SNAP_THRESHOLD = 30; // pixels
let isMyTurn = false;

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
    const cardPath = `/static/cards/${filename}`;

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
                // .map(gif => gif.images && gif.images.downsized_medium && gif.images.downsized_medium.url)
                .map(gif => gif.images && gif.images.downsized_large && gif.images.downsized_large.url)

                .filter(Boolean);
        }
    });

// Hide opponent selection for 1v3 mode
document.getElementById('gameMode').addEventListener('change', function() {
    const opponentSection = document.getElementById('opponentSection');
    opponentSection.style.display = this.value === '1v1' ? 'block' : 'none';
});

function showSetupViewTimer(seconds) {
    const timerDiv = document.getElementById('setupViewTimer');
    timerDiv.textContent = `Bottom two cards visible for: ${seconds} second${seconds !== 1 ? 's' : ''}`;
}

function hideSetupViewTimer() {
    const timerDiv = document.getElementById('setupViewTimer');
    timerDiv.textContent = '';
}

async function startGame() {
    // Reset turn tracking for new game
    lastTurnIndex = null;

    const gameMode = document.getElementById('gameMode').value;
    const opponentType = document.getElementById('opponentType').value;
    const playerName = document.getElementById('playerName').value || 'Human';
    const numGames = parseInt(document.getElementById('numGames').value) || 1;

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
        // Debug: Response received successfully
        if (data.success && data.game_state && data.game_state.players) {
            gameId = data.game_id;
            currentGameState = data.game_state;
            document.getElementById('gameSetup').style.display = 'none';
            document.getElementById('gameBoard').style.display = 'block';
            setupCardsHidden = false;
            if (setupHideTimeout) clearTimeout(setupHideTimeout);
            if (setupViewInterval) clearInterval(setupViewInterval);
            let secondsLeft = SETUP_VIEW_SECONDS;
            showSetupViewTimer(secondsLeft);
            setupViewInterval = setInterval(() => {
                secondsLeft--;
                if (secondsLeft > 0) {
                    showSetupViewTimer(secondsLeft);
                } else {
                    hideSetupViewTimer();
                    clearInterval(setupViewInterval);
                }
            }, 1000);
            setupHideTimeout = setTimeout(() => {
                setupCardsHidden = true;
                try {
                    updateGameDisplay();
                } catch (error) {
                    console.error('Error in updateGameDisplay (timeout):', error);
                }
                hideSetupViewTimer();
                if (setupViewInterval) clearInterval(setupViewInterval);
            }, SETUP_VIEW_SECONDS * 1000);
            try {
                updateGameDisplay();
            } catch (error) {
                console.error('Error in updateGameDisplay (initial):', error);
                throw error; // Re-throw to see the full error
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
        console.error('Error starting game:', error);
        alert('Error starting game: ' + (error.message || error));
    }
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
                let secondsLeft = SETUP_VIEW_SECONDS;
                showSetupViewTimer(secondsLeft);
                setupViewInterval = setInterval(() => {
                    secondsLeft--;
                    if (secondsLeft > 0) {
                        showSetupViewTimer(secondsLeft);
                    } else {
                        hideSetupViewTimer();
                        clearInterval(setupViewInterval);
                    }
                }, 1000);
                setupHideTimeout = setTimeout(() => {
                    setupCardsHidden = true;
                    updateGameDisplay();
                    hideSetupViewTimer();
                    if (setupViewInterval) clearInterval(setupViewInterval);
                }, SETUP_VIEW_SECONDS * 1000);
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
    if (!currentGameState) return;

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
        document.getElementById('deckSize').textContent = `${currentGameState.deck_size} cards`;

        // Update discard pile
        const discardCard = document.getElementById('discardCard');
        if (currentGameState.discard_top) {
            discardCard.innerHTML = getCardDisplayContent(currentGameState.discard_top, false);
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

        // Game display updated successfully
    } catch (error) {
        console.error('Error in updateGameDisplay:', error);
        throw error;
    }

            // Game display updated successfully
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
}

function updateScoresAndRoundInfo() {
    const container = document.getElementById('ScoresAndRoundInfo');
    if (!container || !currentGameState || !currentGameState.players) {
        return;
    }

    // Info text (round/game info)
    const roundDisplay = Math.min(currentGameState.round, currentGameState.max_rounds);
    let infoText = `<div class="round-info"><b>Game</b> ${currentGameState.current_game || 1} of ${currentGameState.num_games || 1} | <b>Round</b> ${roundDisplay}/${currentGameState.max_rounds}</div>`;

    // Scores
    let scoresHtml = '<div class="scores-panel"><h4>Scores</h4>';
    currentGameState.players.forEach((player, index) => {
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
                turnIndicator = ' <span class="turn-label"></span>';
            }
        }
        scoresHtml += `<div class="score-item ${isCurrentTurn ? 'current-turn-score' : ''}"><strong>${player.name}:</strong> ${scoreText}${winnerIcon}${turnIndicator}</div>`;
    });
    scoresHtml += '</div>';

    // Add game control buttons
    let buttonsHtml = '<div class="game-control-buttons">';
    buttonsHtml += '<button onclick="restartGame()" class="btn btn-secondary game-control-btn">New Game</button>';
    buttonsHtml += '<button onclick="replayGame()" class="btn btn-primary game-control-btn">Replay</button>';
    buttonsHtml += '</div>';

    container.innerHTML = infoText + scoresHtml + buttonsHtml;

    // Handle celebration GIF display when human wins
    const celebrationContainer = document.getElementById('celebrationGif');
    if (celebrationContainer) {
        if (currentGameState.game_over && currentGameState.winner === 0) {
            // Human won! Show celebration GIF
            let gifUrl = '';
            if (celebrationGifs.length > 0) {
                gifUrl = celebrationGifs[Math.floor(Math.random() * celebrationGifs.length)];
            }
            if (gifUrl) {
                celebrationContainer.innerHTML = `
                    <div class="celebration-gif-container">
                        <img src="${gifUrl}" alt="Golf Celebration" class="celebration-gif-img" />
                    </div>
                `;
            }
        } else {
            // Clear celebration GIF when game is not over or human didn't win
            celebrationContainer.innerHTML = '';
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

    // Re-enable deck and discard
    const deckCard = document.getElementById('deckCard');
    const discardCard = document.getElementById('discardCard');
    deckCard.classList.remove('disabled');
    deckCard.onclick = drawFromDeck;
    discardCard.classList.remove('disabled');
    discardCard.onclick = takeDiscard;

    window.flipDrawnMode = false;
    updatePlayerGrids(); // Refresh to remove flip indicators
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
    // Position modal removed - no need to hide it

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

    try {
        const response = await fetch('/make_move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(action)
        });

        const data = await response.json();
        if (data.success) {
            currentGameState = data.game_state;
            updateGameDisplay();
            // Update chart immediately after game state changes
            updateCumulativeScoreChart();
            // Immediately refresh to catch any AI moves or turn changes
            refreshGameState();
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
        }
    } catch (error) {
        console.error('Error executing action:', error);
        alert('Error executing action. Please try again.');
    }
}

function restartGame() {
    // Reset turn tracking for restart
    lastTurnIndex = null;

    currentGameState = null;
    gameId = null;
    document.getElementById('gameBoard').style.display = 'none';
    document.getElementById('gameSetup').style.display = 'block';
    setupCardsHidden = false;
    if (setupHideTimeout) clearTimeout(setupHideTimeout);
    if (setupViewInterval) clearInterval(setupViewInterval);
    showSetupViewTimer(SETUP_VIEW_SECONDS);

    // Reset chart data for new match
    window.cumulativeScoreHistory = null;
    window.cumulativeScoreLabels = null;
    window.lastMatchId = null;

    // Destroy existing chart instance to ensure fresh start
    if (cumulativeScoreChart) {
        cumulativeScoreChart.destroy();
        cumulativeScoreChart = null;
    }

    updateGameDisplay();
}

// Modal closing logic removed - no modals in use

// Periodically refresh game state to catch AI moves
setInterval(() => {
    if (gameId && currentGameState && !currentGameState.game_over) {
        refreshGameState();
    }
}, 500); // Reduced from 1000ms to 500ms for more responsive AI turns

// Drawn card drag-and-drop logic
document.addEventListener('DOMContentLoaded', () => {
    const discardCard = document.getElementById('discardCard');
    discardCard.addEventListener('dragstart', (e) => {
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
        } else {
            draggedDiscardCard = null;
        }
    });
    discardCard.addEventListener('dragend', (e) => {
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
    clone.style.transition = 'all 0.2s cubic-bezier(.4,1.4,.6,1)';
    // Hide original
    cardElem.style.visibility = 'hidden';
    // Animate to target
    requestAnimationFrame(() => {
        clone.style.left = targetRect.left + 'px';
        clone.style.top = targetRect.top + 'px';
    });
    // After animation, remove clone and callback
    setTimeout(() => {
        clone.remove();
        cardElem.style.visibility = '';
        if (callback) callback();
    }, 200);
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
        const drawnCardElem = document.getElementById('drawnCardDisplay');
        if (targetElem && drawnCardElem) {
            animateSnapToGrid(drawnCardElem, targetElem, () => {
                executeAction(pos, 'draw_keep');
                hideDrawnCardArea();
            });
        } else {
            executeAction(pos, 'draw_keep');
            hideDrawnCardArea();
        }
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
    const discardCardElem = document.getElementById('discardCard');
    if (targetElem && discardCardElem) {
        animateSnapToGrid(discardCardElem, targetElem, () => {
            executeAction(pos, 'take_discard');
        });
    } else {
        executeAction(pos, 'take_discard');
    }
}

function flipDrawnCardOnGrid(pos) {
    if (!window.flipDrawnMode || !drawnCardData) return;
    // Only allow if the position is not public
    const card = currentGameState.players[0].grid[pos];
    if (!card || card.public) return;
    // Discard the drawn card and flip this position
    executeAction(pos, 'draw_discard');
    hideDrawnCardArea();
}

function updateProbabilitiesPanel() {
    const unknownCardsPanel = document.getElementById('unknownCardsPanel');
    const otherProbabilitiesPanel = document.getElementById('otherProbabilitiesPanel');

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
            otherHtml += '<div class="probabilities-bar-title">🎯 Strategic Recommendation:</div>';
            otherHtml += `<div class="probabilities-bar-main"><b>${ev.recommendation}</b></div>`;
            otherHtml += `<div class="probabilities-bar-detail">Draw: +${ev.draw_expected_value}</div>`;
            otherHtml += `<div class="probabilities-bar-detail">Discard: +${ev.discard_expected_value}</div>`;
            otherHtml += `<div class="probabilities-bar-detail">Advantage: ${ev.draw_advantage > 0 ? '+' : ''}${ev.draw_advantage}</div>`;
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

        otherHtml += '</div>';
        otherProbabilitiesPanel.innerHTML = otherHtml;
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
                    display: true,
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
        plugins: [{
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
    const matchId = `${currentGameState.num_games}_${currentGameState.players.map(p => p.name).join('_')}`;
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

        if (currentGameState.current_game === 1) {
            // First game: show exactly 4 rounds, pad with empty if needed
            const maxRoundsFirstGame = 4;
            if (displayLabels.length > maxRoundsFirstGame) {
                displayLabels = displayLabels.slice(0, maxRoundsFirstGame);
                displayHistory = displayHistory.map(playerHistory =>
                    playerHistory.slice(0, maxRoundsFirstGame)
                );
    } else {
                // Pad with empty rounds if we have fewer than 4
                while (displayLabels.length < maxRoundsFirstGame) {
                    const roundNum = displayLabels.length + 1;
                    displayLabels.push(`G1R${roundNum}`);
                    displayHistory.forEach(playerHistory => {
                        playerHistory.push(null); // null values won't be plotted
                    });
                }
            }
        } else {
            // Multi-game mode: show last 8 rounds
            const maxRoundsMultiGame = 10;
            if (displayLabels.length > maxRoundsMultiGame) {
                displayLabels = displayLabels.slice(-maxRoundsMultiGame);
                displayHistory = displayHistory.map(playerHistory =>
                    playerHistory.slice(-maxRoundsMultiGame)
                );
            }
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
}

// Show timer on initial load
document.addEventListener('DOMContentLoaded', function() {
    showSetupViewTimer(SETUP_VIEW_SECONDS);
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
    console.log('🤖 pollAITurns called - current_turn:', currentGameState?.current_turn, 'game_over:', currentGameState?.game_over);
    while (currentGameState && currentGameState.current_turn !== 0 && !currentGameState.game_over) {
        console.log('🤖 Making AI turn request for player', currentGameState.current_turn);
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
        } else {
            console.log('🤖 AI turn failed or game over:', data.error);
            break; // error or game over
        }
        await new Promise(res => setTimeout(res, 100)); // small delay to avoid hammering server
    }
    console.log('🤖 pollAITurns finished - current_turn:', currentGameState?.current_turn);
}

// Add the replayGame function
function replayGame() {
    // Reset turn tracking for replay
    lastTurnIndex = null;

    // Reset chart data for replay
    window.cumulativeScoreHistory = null;
    window.cumulativeScoreLabels = null;
    window.lastMatchId = null;

    // Destroy existing chart instance to ensure fresh start
    if (cumulativeScoreChart) {
        cumulativeScoreChart.destroy();
        cumulativeScoreChart = null;
    }

    // Use the last selected settings
    const gameMode = currentGameState.mode || '1v1';
    const opponentType = currentGameState.players && currentGameState.players[1] ? currentGameState.players[1].agent_type : 'random';
    const playerName = currentGameState.players && currentGameState.players[0] ? currentGameState.players[0].name : 'Human2';
    const numGames = currentGameState.num_games || 1;
    // Start a new game with the same settings
    startGameWithSettings(gameMode, opponentType, playerName, numGames);
}

// Add a helper to start a game with specific settings
async function startGameWithSettings(gameMode, opponentType, playerName, numGames) {
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
            let secondsLeft = SETUP_VIEW_SECONDS;
            showSetupViewTimer(secondsLeft);
            setupViewInterval = setInterval(() => {
                secondsLeft--;
                if (secondsLeft > 0) {
                    showSetupViewTimer(secondsLeft);
                } else {
                    hideSetupViewTimer();
                    clearInterval(setupViewInterval);
                }
            }, 1000);
            setupHideTimeout = setTimeout(() => {
                setupCardsHidden = true;
                updateGameDisplay();
                hideSetupViewTimer();
                if (setupViewInterval) clearInterval(setupViewInterval);
            }, SETUP_VIEW_SECONDS * 1000);
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
    if (discard) discard.classList.toggle('disabled', !isMyTurn);

    // All your cards
    document.querySelectorAll('.player-grid.human .card').forEach(card => {
        card.classList.toggle('disabled', !isMyTurn);
    });

    // Block drag events for discard and cards
    if (discard) discard.draggable = isMyTurn;
    document.querySelectorAll('.player-grid.human .card').forEach(card => {
        card.draggable = isMyTurn;
    });
}

discardCard.onclick = function() {
    if (!isMyTurn) return;
    // ...rest of logic...
};

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