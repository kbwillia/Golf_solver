// ===== GOLF GAME CORE VARIABLES =====
// Core game variables are now defined in game-core.js

// ===== CHATBOT VARIABLES =====
// Chatbot variables are now defined in game-core.js



console.log('🎯 Golf.js loaded successfully!');

// HTML Legend Plugin moved to probabilities.js

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

    // Update custom bot count display when mode changes
    // updateCustomBotCount(); // REMOVED
});

// showSetupViewTimer() and hideSetupViewTimer() functions moved to game-core.js

// startGame() function moved to game-core.js

// refreshGameState() function moved to game-core.js

// updateGameDisplay() function moved to game-ui.js

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

// updateGameAndRoundInfo() function moved to game-ui.js

// updateLastActionPanel() function moved to game-ui.js



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
    playCardFlipSound();
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

// restartGame() function moved to game-core.js
// Periodic polling setup moved to game-core.js

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

        playCardFlipSound();
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

    playCardFlipSound();
    // NO animation for discard->grid, but we want grid->discard animation
    // We'll handle the animation in the backend response processing
    executeAction(pos, 'take_discard');
}

function flipDrawnCardOnGrid(pos) {
    if (!window.flipDrawnMode || !drawnCardData) return;
    // Only allow if the position is not public
    const card = currentGameState.players[0].grid[pos];
    if (!card || card.public) return;
    playCardFlipSound();
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

// updateProbabilitiesPanel() moved to probabilities.js

// Chart functions moved to probabilities.js

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

// pollAITurns() function moved to game-core.js

// replayGame() function moved to game-core.js

// nextGame() function moved to game-core.js
// startGameWithSettings() function moved to game-core.js

// Remove the problematic global scope code that was causing the null reference error
// The pollAITurns() function should only be called from within functions after a game is started

// updateInteractivity() and setPlayerInteractivity() functions moved to game-ui.js
//was causing error before so not sure about this.
// discardCard.onclick = function() {
//     if (!isMyTurn) return;
//     // ...rest of logic...
// };

// handleGameEnd() function moved to game-ui.js

// updateChart() moved to probabilities.js

// Wrap polling interval logic
// pausePolling(), resumePolling(), findAIDiscardedCard(), aiJustMoved(), deepCopy() functions moved to game-core.js

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
// Button and header functions moved to game-ui.js






// Voice system variables (global scope)
let useElevenLabs = false; // Set to false for free browser TTS
// voiceEnabled variable moved to voice.js
// Voice variables moved to voice.js

// Initialize voice system
console.log('🎙️ Voice system initialized');
// Speech synthesis check moved to voice.js

// initializeVoiceStatus() function moved to voice.js

// loadVoices() function moved to voice.js



// toggleVoiceSystem() function moved to voice.js

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



//geting tts from topmediai api and playing it. activate this later. TODO
// fetch('/api/tts', {
//   method: 'POST',
//   headers: {'Content-Type': 'application/json'},
//   body: JSON.stringify({text: "Hello Friends!"})
// })
// .then(response => response.json())
// .then(data => {
//   if (data.audio_url) {
//     const audio = new Audio(data.audio_url);
//     audio.play();
//   } else {
//     alert("TTS failed");
//   }
// });

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



// Wait for chatbot.js to load before setting up GIF functionality
function setupGifFunctionality() {
  const sendGifBtn = document.getElementById('sendGifBtn');
  if (sendGifBtn) {
    sendGifBtn.addEventListener('click', function() {
      document.getElementById('gifModal').style.display = 'block';
      var gifInput = document.getElementById('gifSearchInput');
      // Focus the GIF search input after a short delay to ensure modal is visible
      setTimeout(() => {
        if (gifInput) gifInput.focus();
      }, 100);
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
                  if (window.sendUserGifToChat) {
                    window.sendUserGifToChat(gifUrl);
                  } else {
                    console.error('sendUserGifToChat function not available');
                  }
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
  }
}

// Set up GIF functionality when DOM is ready and chatbot is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupGifFunctionality);
} else {
  setupGifFunctionality();
}

// Set up close GIF modal functionality
function setupCloseGifModal() {
  const closeGifModal = document.getElementById('closeGifModal');
  if (closeGifModal) {
    closeGifModal.addEventListener('click', function() {
      document.getElementById('gifModal').style.display = 'none';
    });
  }
}

// Set up close modal when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupCloseGifModal);
} else {
  setupCloseGifModal();
}

// Set up GIF search button functionality
function setupGifSearchButton() {
  const gifSearchBtn = document.getElementById('gifSearchBtn');
  if (gifSearchBtn) {
    gifSearchBtn.addEventListener('click', async function() {
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
            if (window.sendUserGifToChat) {
              window.sendUserGifToChat(gifUrl);
            } else {
              console.error('sendUserGifToChat function not available');
            }
            document.getElementById('gifModal').style.display = 'none';
          };
          gifResults.appendChild(img);
        });
      } else {
        gifResults.textContent = 'No GIFs found.';
      }
    });
  }
}

// Set up GIF search button when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupGifSearchButton);
} else {
  setupGifSearchButton();
}





// === SOUND EFFECTS ===
function playCardShuffleSound() {
    const audio = document.getElementById('cardShuffleAudio');
    if (audio) {
        audio.currentTime = 0;
        audio.play();
    }
}

function playCardFlipSound() {
    const audios = [
        document.getElementById('cardFlipAudio'),
        document.getElementById('cardFlipAudio2')
    ];
    const audio = audios[Math.floor(Math.random() * audios.length)];
    if (audio) {
        audio.currentTime = 0;
        audio.play();
    }
}



// === CUSTOM BOT MODAL ===
// Custom bot functionality moved to custom-bots.js

// All custom bot functionality moved to custom-bots.js

// Custom bot functions moved to custom-bots.js

// Custom bot functions moved to custom-bots.js

// Custom bot functions moved to custom-bots.js

// Custom bot functions moved to custom-bots.js

// Test Jim Nantz voice directly
jimNantzCommentVoice("Hello friends, what a beautiful day for golf!")

// Check voice settings
// Voice status logging moved to voice.js
