let currentGameState = null; // Holds the current game state from backend
let gameId = null; // Unique game session ID
let drawnCard = null; // Card drawn from deck
let currentAction = null; // Current action type
let dragActive = false; // Drag state for discard
let draggedDiscardCard = null; // Card being dragged from discard
let drawnCardData = null; // Data for the currently drawn card
let drawnCardDragActive = false; // Drag state for drawn card
let turnAnimateTimeout = null; // Timeout for turn animation
let lastTurnIndex = null; // Last turn index to detect turn changes
let setupHideTimeout = null; // Timeout for hiding setup cards
let setupCardsHidden = false; // Whether setup cards are hidden
const SETUP_VIEW_SECONDS = 1.2; // Change this value for how long to show bottom cards
let setupViewInterval = null; // Interval for setup view timer
const SNAP_THRESHOLD = 30; // pixels

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
                .map(gif => gif.images && gif.images.downsized_medium && gif.images.downsized_medium.url)
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
            document.getElementById('restartBtn').style.display = 'inline-block';
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
            currentGameState = data;
            updateGameDisplay();

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

        // Clear notification area elements that exist
        const notificationBanner = document.getElementById('notificationBanner');
        const celebrationGif = document.getElementById('celebrationGif');

        if (celebrationGif) celebrationGif.innerHTML = '';

        // Set up the unified notification banner
        if (notificationBanner) {
            notificationBanner.className = ''; // Reset classes

            if (
                currentGameState.game_over &&
                currentGameState.current_game === currentGameState.num_games
            ) {
                infoText += ' - Game Over!';
                notificationBanner.innerHTML = "Game Over!";
                notificationBanner.style.background = "#dc3545"; // Red for game over
                notificationBanner.style.color = "white";

                // Show celebratory GIF below the banner if human wins
                let iconHtml = '';
                if (currentGameState.winner === 0) {
                    let gifUrl = '';
                    if (celebrationGifs.length > 0) {
                        gifUrl = celebrationGifs[Math.floor(Math.random() * celebrationGifs.length)];
                    }
                    iconHtml = gifUrl ? `<img src="${gifUrl}" alt="Golf Celebration" style="width:100%;max-width:320px;max-height:200px;display:block;margin:0 auto;object-fit:contain;background:transparent;border-radius:0;" />` : '';
                } else if (typeof currentGameState.winner === 'number') {
                    iconHtml = '🏆'; // AI wins
                }
                if (celebrationGif) {
                    celebrationGif.innerHTML = `<div style="text-align:center;margin-top:20px;">${iconHtml}</div>`;
                }

                // Add New Game and Replay buttons
                let buttonHtml = `<div id="gameOverButtons" style="margin-top:12px;text-align:center;">
                    <button id="newGameBtn" class="btn btn-secondary" style="margin-right:10px;">New Game</button>
                    <button id="replayBtn" class="btn btn-primary">Replay</button>
                </div>`;
                notificationBanner.innerHTML += buttonHtml;
                // Attach event listeners after rendering
                setTimeout(() => {
                    const newGameBtn = document.getElementById('newGameBtn');
                    const replayBtn = document.getElementById('replayBtn');
                    if (newGameBtn) newGameBtn.onclick = restartGame;
                    if (replayBtn) replayBtn.onclick = replayGame;
                }, 0);
            } else if (currentGameState.ai_thinking) {
                notificationBanner.innerHTML = "AI is lining up its shot...";
                notificationBanner.style.background = "#28a745"; // Green for AI thinking
                notificationBanner.style.color = "white";
            } else if (currentGameState.current_turn === 0 && !currentGameState.game_over) {
                notificationBanner.innerHTML = "Your Turn!";
                notificationBanner.style.background = "#007bff"; // Blue for your turn
                notificationBanner.style.color = "white";
            } else {
                notificationBanner.innerHTML = "";
                notificationBanner.style.background = "#007bff";
                notificationBanner.style.color = "white";
            }
        }

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

        // Show match summary if match is over
        if (currentGameState.match_winner && currentGameState.current_game === currentGameState.num_games) {
            let summaryHtml = `<div style="background:#f8f9fa;padding:18px 24px;border-radius:12px;box-shadow:0 2px 12px #eee;margin-bottom:18px;max-width:480px;">
                <h2 style="text-align:center;">Match Summary</h2>`;
            summaryHtml += `<div style="margin-bottom:10px;"><b>Final Cumulative Scores:</b></div><ul style="padding-left:18px;">`;
            for (let i = 0; i < currentGameState.players.length; i++) {
                const winnerIcon = (Array.isArray(currentGameState.match_winner) && currentGameState.match_winner.includes(i)) ? ' 🏆' : '';
                summaryHtml += `<li><b>${playerNames[i]}</b>: ${currentGameState.cumulative_scores[i]}${winnerIcon}</li>`;
            }
            summaryHtml += `</ul>`;
            if (Array.isArray(currentGameState.match_winner) && currentGameState.match_winner.length === 1) {
                summaryHtml += `<div style="margin-top:12px;font-size:1.2em;text-align:center;color:#007bff;font-weight:bold;">Winner: ${playerNames[currentGameState.match_winner[0]]} 🏆</div>`;
            } else if (Array.isArray(currentGameState.match_winner)) {
                summaryHtml += `<div style="margin-top:12px;font-size:1.2em;text-align:center;color:#007bff;font-weight:bold;">Winners: ${currentGameState.match_winner.map(i => playerNames[i]).join(', ')} 🏆</div>`;
            }
            summaryHtml += `</div>`;
            document.getElementById('matchupSummary').innerHTML = summaryHtml;
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
        // Update probabilities panel
        updateProbabilitiesPanel();

        // Update cumulative score chart
        updateCumulativeScoreChart();

        // Game display updated successfully
    } catch (error) {
        console.error('Error in updateGameDisplay:', error);
        throw error;
    }
}

function updatePlayerGrids() {
    const container = document.getElementById('playerGrids');
    container.innerHTML = '';
    // Add or remove four-player-grid class
    if (currentGameState.players.length === 4) {
        container.classList.add('four-player-grid');
    } else {
        container.classList.remove('four-player-grid');
    }
    // Only clear timeout and remove animation if turn index changes
    const currentTurnIndex = currentGameState.current_turn;
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
        // Show only the public score for each player, and private score for human
        let scoreText = '';
        let badgeHtml = '';
        if (currentGameState.public_scores && typeof currentGameState.public_scores[index] !== 'undefined') {
            scoreText = ` - Score: ${currentGameState.public_scores[index]}`;
            if (currentGameState.cumulative_scores && typeof currentGameState.cumulative_scores[index] !== 'undefined') {
                scoreText += ` (Cumulative: ${currentGameState.cumulative_scores[index]})`;
            }
            if (currentGameState.game_over && index === currentGameState.winner) {
                scoreText += '';
            }
        }
        playerDiv.innerHTML = `
            <h3>${player.name}${scoreText}</h3> /
            ${badgeHtml}
            <div class="grid-container">${gridHtml}</div>
        `; //this is where Human (human) and AI (AI) are displayed
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

    showPositionModal('Take Discard Card', 'Choose position to place the discard card:', availablePositions, 'take_discard');
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
    display.innerHTML = getCardDisplayContent(card, false);
    area.style.display = 'flex';
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

function showPositionModal(title, message, positions, actionType) {
    currentAction = actionType;
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalMessage').textContent = message;

    const buttonsContainer = document.getElementById('positionButtons');
    buttonsContainer.innerHTML = '';

    // Get the human player's grid
    const humanPlayer = currentGameState.players[0];

    // Create a 2x2 grid of buttons (positions 0-3)
    for (let row = 0; row < 2; row++) {
        for (let col = 0; col < 2; col++) {
            const pos = row * 2 + col;
            if (positions.includes(pos)) {
                let cardLabel = '?';
                const card = humanPlayer.grid[pos];
                if (card) {
                    if (card.visible) {
                        cardLabel = `${card.rank}${card.suit}`;
                    } else {
                        cardLabel = '?';
                    }
                }
                const button = document.createElement('button');
                button.className = 'btn btn-primary';
                button.textContent = cardLabel;
                button.onclick = () => executeAction(pos, actionType);
                buttonsContainer.appendChild(button);
            } else {
                // Add an invisible placeholder to keep grid shape
                const placeholder = document.createElement('div');
                placeholder.style.visibility = 'hidden';
                buttonsContainer.appendChild(placeholder);
            }
        }
    }

    document.getElementById('positionModal').style.display = 'block';
}

async function executeAction(position, actionType = null) {
    document.getElementById('positionModal').style.display = 'none';

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
            // Immediately refresh to catch any AI moves or turn changes
            refreshGameState();
            if (data.game_state.game_over) {
                // Game over - no modal needed
            }
            // If it's now an AI's turn, start polling for AI turns
            if (currentGameState.current_turn !== 0 && !currentGameState.game_over) {
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
    currentGameState = null;
    gameId = null;
    document.getElementById('gameBoard').style.display = 'none';
    document.getElementById('gameSetup').style.display = 'block';
    document.getElementById('restartBtn').style.display = 'none';
    setupCardsHidden = false;
    if (setupHideTimeout) clearTimeout(setupHideTimeout);
    if (setupViewInterval) clearInterval(setupViewInterval);
    showSetupViewTimer(SETUP_VIEW_SECONDS);
}

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.getElementsByClassName('modal');
    for (let modal of modals) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    }
}

// Periodically refresh game state to catch AI moves
setInterval(() => {
    if (gameId && currentGameState && !currentGameState.game_over) {
        refreshGameState();
    }
}, 1000);

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
        let unknownHtml = '<div style="background:#f8f9fa;padding:12px 18px;border-radius:10px;box-shadow:0 1px 4px #eee;">';
        unknownHtml += '<h4 style="margin-top:0;">Cards Left</h4>';

        // Desired order: J, A, 2-10, Q, K
        const order = ['J', 'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Q', 'K'];
        const maxCount = Math.max(...Object.values(probs.deck_counts));

        unknownHtml += '<table style="font-size:13px;margin-top:4px;margin-bottom:6px;width:100%;border-collapse:collapse;">';
        unknownHtml += '<thead><tr><th style="text-align:left;padding-right:5px;width:25px;">Rank</th><th style="text-align:left;">Count</th></tr></thead><tbody>';

        for (const rank of order) {
            if (probs.deck_counts[rank] !== undefined) {
                const count = probs.deck_counts[rank];
                const barWidth = maxCount > 0 ? (count / maxCount) * 100 : 0;

                // Color based on count
                let barColor;
                if (count === 0) {
                    barColor = '#dc3545'; // Red for 0 (cards are out)
                } else if (count === 1) {
                    barColor = '#fd7e14'; // Orange for 1 (low availability)
                } else if (count <= 2) {
                    barColor = '#ffc107'; // Yellow for 2 (medium-low)
                } else if (count <= 3) {
                    barColor = '#20c997'; // Teal for 3 (medium)
                } else {
                    barColor = '#28a745'; // Green for 4 (high availability)
                }

                unknownHtml += `<tr><td style="padding-right:5px;padding:2px 0;">${rank}</td>`;
                unknownHtml += `<td style="padding:2px 0;">`;
                unknownHtml += `<div class="card-count-bar-container">`;
                unknownHtml += `<div class="card-count-bar" style="width:${Math.max(barWidth, 8)}%;background-color:${barColor};">`;
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
        let otherHtml = '<div style="background:#f8f9fa;padding:12px 18px;border-radius:10px;box-shadow:0 1px 4px #eee;">';
        otherHtml += '<h4 style="margin-top:0;">Probabilities</h4>';

        // Expected Value Comparison (most important - show first)
        if (probs.expected_value_draw_vs_discard && currentGameState.current_turn === 0 && !currentGameState.game_over) {
            const ev = probs.expected_value_draw_vs_discard;
            otherHtml += '<div style="margin-bottom:12px;padding:8px 12px;background:#e8f4fd;border-radius:6px;border-left:4px solid #007bff;">';
            otherHtml += '<div style="font-weight:bold;color:#007bff;margin-bottom:4px;">🎯 Strategic Recommendation:</div>';
            otherHtml += `<div style="font-size:14px;margin-bottom:2px;"><b>${ev.recommendation}</b></div>`;
            otherHtml += `<div style="font-size:12px;color:#666;">Draw: +${ev.draw_expected_value} | Discard: +${ev.discard_expected_value} | Advantage: ${ev.draw_advantage > 0 ? '+' : ''}${ev.draw_advantage}</div>`;
            if (ev.discard_card) {
                otherHtml += `<div style="font-size:12px;color:#666;">Discard: ${ev.discard_card} (score: ${ev.discard_score})</div>`;
            }
            otherHtml += '</div>';
        }

        // Probability statistics
        if (probs.prob_draw_pair && probs.prob_draw_pair.length > 0) {
            otherHtml += `<div style="margin-top:4px;">`;
            otherHtml += `<b>Prob. next card matches your grid:</b> <span style="color:#007bff;">${probs.prob_draw_pair[0]}</span>`;
            otherHtml += '</div>';
        }
        // Probability of drawing a card that improves your hand (for human)
        if (probs.prob_improve_hand && probs.prob_improve_hand.length > 0) {
            otherHtml += `<div style="margin-top:4px;">`;
            otherHtml += `<b>Prob. next card improves your hand:</b> <span style="color:#007bff;">${probs.prob_improve_hand[0]}</span>`;
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
function updateCumulativeScoreChart() {
    const canvas = document.getElementById('cumulativeScoreChart');
    if (!canvas) {
        console.log('Canvas element not found');
        return;
    }
    const ctx = canvas.getContext('2d');
    if (!currentGameState || !currentGameState.cumulative_scores || !currentGameState.current_game) {
        console.log('Missing game state data for chart');
        return;
    }
    // Build score history for each player, per round
    if (!window.cumulativeScoreHistory || lastChartGameId !== gameId) {
        // Reset history if new game session
        window.cumulativeScoreHistory = [];
        for (let i = 0; i < currentGameState.players.length; i++) {
            window.cumulativeScoreHistory.push([]);
        }
        window.cumulativeScoreLabels = [];
        lastChartGameId = gameId;
        lastChartRound = null;
    }
    // Always add a point for the first round of the first game if not present
    if (window.cumulativeScoreLabels.length === 0 && currentGameState.round === 1) {
        for (let i = 0; i < currentGameState.players.length; i++) {
            window.cumulativeScoreHistory[i].push(currentGameState.cumulative_scores[i]);
        }
        window.cumulativeScoreLabels.push('G1R1');
        lastChartRound = 'G1R1';
    }
    // Only update if new round or game over
    const roundKey = `G${currentGameState.current_game}R${currentGameState.round}`;
    if (window.cumulativeScoreLabels[window.cumulativeScoreLabels.length - 1] !== roundKey && (currentGameState.round > 1 || currentGameState.current_game > 1 || currentGameState.game_over)) {
        for (let i = 0; i < currentGameState.players.length; i++) {
            window.cumulativeScoreHistory[i].push(currentGameState.cumulative_scores[i]);
        }
        window.cumulativeScoreLabels.push(roundKey);
        lastChartRound = roundKey;
    } else if (window.cumulativeScoreLabels[window.cumulativeScoreLabels.length - 1] === roundKey) {
        // No new round, don't update chart
        return;
    }
    // X axis: per round (G1R1, G1R2, ...)
    const labels = window.cumulativeScoreLabels;
    // Colors for each player
    const colors = ['#007bff', '#e67e22', '#28a745', '#764ba2', '#f39c12', '#e74c3c'];
    const datasets = currentGameState.players.map((player, i) => ({
        label: player.name,
        data: window.cumulativeScoreHistory[i],
        borderColor: colors[i % colors.length],
        backgroundColor: colors[i % colors.length],
        fill: false,
        tension: 0.2,
        pointRadius: 1,
        pointHoverRadius: 5
    }));
    if (cumulativeScoreChart) {
        cumulativeScoreChart.data.labels = labels;
        cumulativeScoreChart.data.datasets = datasets;
        cumulativeScoreChart.update();
    } else {
        cumulativeScoreChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: true, position: 'bottom' },
                    title: { display: true, text: 'Cumulative Scores by Round' }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Game & Round' },
                        ticks: { autoSkip: false }
                    },
                    y: {
                        title: { display: true, text: 'Score' },
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

// Show timer on initial load
document.addEventListener('DOMContentLoaded', function() {
    showSetupViewTimer(SETUP_VIEW_SECONDS);
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
    while (currentGameState && currentGameState.current_turn !== 0 && !currentGameState.game_over) {
        const response = await fetch('/run_ai_turn', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ game_id: gameId })
        });
        const data = await response.json();
        if (data.success) {
            currentGameState = data.game_state;
            updateGameDisplay();
        } else {
            break; // error or game over
        }
        await new Promise(res => setTimeout(res, 100)); // small delay to avoid hammering server
    }
}

// Add the replayGame function
function replayGame() {
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
            document.getElementById('restartBtn').style.display = 'inline-block';
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
        } else {
            alert('Error starting game: ' + (data.error || JSON.stringify(data)));
        }
    } catch (error) {
        alert('Error starting game: ' + (error.message || error));
    }
}

// Remove the problematic global scope code that was causing the null reference error
// The pollAITurns() function should only be called from within functions after a game is started