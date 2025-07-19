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
    updateCustomBotCount();
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

// ===== CHATBOT FUNCTIONALITY =====

// Chatbot state (already declared at top)

// Parse @ mentions from a message
function parseMentions(message) {
    const mentionRegex = /@(\w+)/g;
    const mentions = [];
    let match;

    while ((match = mentionRegex.exec(message)) !== null) {
        const mentionedName = match[1].toLowerCase();

        // Map mention variations to actual bot names
        const botNameMap = {
            'golfbro': 'Golf Bro',
            'golfpro': 'Golf Pro',
            'golf_bro': 'Golf Bro',
            'golf_pro': 'Golf Pro'
        };

        // Check if it's a valid bot mention
        if (botNameMap[mentionedName]) {
            mentions.push(botNameMap[mentionedName]);
        }
    }

    return mentions;
}

// Setup autocomplete for chat input
function setupAutocomplete(chatInput) {
    const suggestions = ['@golfbro', '@golfpro'];
    let currentSuggestions = [];
    let selectedIndex = -1;

    // Create autocomplete dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'autocomplete-dropdown';
    dropdown.style.cssText = `
        position: absolute;
        background: rgba(11, 80, 27, 0.9);
        border: 1px solid rgba(11, 80, 27, 0.8);
        max-height: 50px;
        overflow-y: auto;
        z-index: 1000;
        display: none;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        font-size: 0.9em;
        padding: 0;
        bottom: 100%;
        left: 0;
        right: 0;
        margin-bottom: 5px;
    `;

    // Make chat input container relative positioned
    const chatInputContainer = chatInput.parentNode;
    chatInputContainer.style.position = 'relative';

    // Insert dropdown inside the chat input container
    chatInputContainer.appendChild(dropdown);

    chatInput.addEventListener('input', function(e) {
        const value = e.target.value;
        const cursorPosition = e.target.selectionStart;

        // Find the word being typed (from @ to cursor position)
        const beforeCursor = value.substring(0, cursorPosition);
        const match = beforeCursor.match(/@(\w*)$/);

        if (match) {
            const partial = match[1].toLowerCase();
            currentSuggestions = suggestions.filter(suggestion =>
                suggestion.toLowerCase().startsWith('@' + partial)
            );

            if (currentSuggestions.length > 0) {
                showSuggestions(currentSuggestions);
            } else {
                hideSuggestions();
            }
        } else {
            hideSuggestions();
        }
    });

    chatInput.addEventListener('keydown', function(e) {
        if (dropdown.style.display === 'block') {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, currentSuggestions.length - 1);
                updateSelection();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                updateSelection();
            } else if (e.key === 'Enter' && selectedIndex >= 0) {
                e.preventDefault();
                selectSuggestion(currentSuggestions[selectedIndex]);
            } else if (e.key === 'Tab') {
                e.preventDefault();
                if (selectedIndex >= 0) {
                    selectSuggestion(currentSuggestions[selectedIndex]);
                } else if (currentSuggestions.length === 1) {
                    // If there's only one suggestion, auto-select it
                    selectSuggestion(currentSuggestions[0]);
                } else if (currentSuggestions.length > 1) {
                    // If multiple suggestions, select the first one
                    selectedIndex = 0;
                    updateSelection();
                }
            } else if (e.key === 'Escape') {
                hideSuggestions();
            }
        }
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!chatInput.contains(e.target) && !dropdown.contains(e.target)) {
            hideSuggestions();
        }
    });

    function showSuggestions(suggestions) {
        dropdown.innerHTML = '';
                suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.textContent = suggestion;
            item.style.cssText = `
                padding: 2px 6px;
                cursor: pointer;
                border-bottom: ${index < suggestions.length - 1 ? '1px solid rgba(255, 255, 255, 0.1)' : 'none'};
                color: white;
                font-size: 1em;
                line-height: 1.2;
            `;

            item.addEventListener('click', () => selectSuggestion(suggestion));
            item.addEventListener('mouseenter', () => {
                selectedIndex = index;
                updateSelection();
            });

            dropdown.appendChild(item);
        });

        // Position dropdown above input using relative positioning
        dropdown.style.display = 'block';

        // Calculate width based on the longest suggestion
        const tempSpan = document.createElement('span');
        tempSpan.style.visibility = 'hidden';
        tempSpan.style.position = 'absolute';
        tempSpan.style.fontSize = '1em';
        tempSpan.style.fontFamily = getComputedStyle(chatInput).fontFamily;
        document.body.appendChild(tempSpan);

        let maxWidth = 0;
        suggestions.forEach(suggestion => {
            tempSpan.textContent = suggestion;
            maxWidth = Math.max(maxWidth, tempSpan.offsetWidth);
        });
        document.body.removeChild(tempSpan);

        // Add a little padding, and set min/max width
        const finalWidth = Math.max(70, Math.min(maxWidth + 24, 140)); // px
        dropdown.style.width = finalWidth + 'px';

        selectedIndex = -1;
    }

    function hideSuggestions() {
        dropdown.style.display = 'none';
        selectedIndex = -1;
    }

    function updateSelection() {
        const items = dropdown.querySelectorAll('.autocomplete-item');
        items.forEach((item, index) => {
            if (index === selectedIndex) {
                item.style.backgroundColor = 'rgba(255, 255, 255, 0.3)';
                item.style.color = 'white';
                item.style.fontWeight = 'bold';
            } else {
                item.style.backgroundColor = 'transparent';
                item.style.color = 'white';
                item.style.fontWeight = 'normal';
            }
        });
    }

    function selectSuggestion(suggestion) {
        const value = chatInput.value;
        const cursorPosition = chatInput.selectionStart;

        // Find the @ symbol position
        const beforeCursor = value.substring(0, cursorPosition);
        const atIndex = beforeCursor.lastIndexOf('@');

        if (atIndex !== -1) {
            // Replace from @ to cursor with the suggestion
            const newValue = value.substring(0, atIndex) + suggestion + value.substring(cursorPosition);
            chatInput.value = newValue;

            // Set cursor position after the suggestion
            const newCursorPosition = atIndex + suggestion.length;
            chatInput.setSelectionRange(newCursorPosition, newCursorPosition);
        }

        hideSuggestions();
        chatInput.focus();
    }
}

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

        // Add autocomplete functionality
        setupAutocomplete(chatInput);

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

    // Removed dropdown event listener - no longer needed since everyone is automatically included
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

    // Re-enable input immediately so user can type while bots respond
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();

    try {
        console.log('🌐 Making API request to /chatbot/send_message');

        // Parse @ mentions in the message
        const mentionedBots = parseMentions(message);
        console.log('Mentioned bots:', mentionedBots);

        // Determine personality type based on mentions
        let personalityType = 'opponent';
        let mentionedBotNames = [];

        if (mentionedBots.length > 0) {
            // If specific bots are mentioned, only send to those bots
            personalityType = 'mentioned';
            mentionedBotNames = mentionedBots;
        }

        // Debug what will be sent
        console.log('Sending to backend:', {
            game_id: gameId,
            message: message,
            personality_type: personalityType,
            mentioned_bots: mentionedBotNames
        });

        console.log('🔄 Awaiting response...');
        const response = await fetch('/chatbot/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: gameId,
                message: message,
                personality_type: personalityType,
                mentioned_bots: mentionedBotNames
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
                    if (shouldBotSendGif(botName)) {
                        // Extract relevant search terms from the message
                        const searchTerms = extractSearchTerms(message, botName);
                        const relevantGif = await getRelevantGif(searchTerms, botName);
                        addMessageToChat('bot', relevantGif, botName, true); // true = GIF only
                    }
                }
            } else if (data.response_type === 'sequential' && data.bot_names) {
                // Handle sequential responses - get each bot's response individually
                console.log('🔄 Handling sequential responses for bots:', data.bot_names);

                // Track conversation context for subsequent bots
                let conversationContext = [
                    { role: 'user', content: message }
                ];

                for (const botName of data.bot_names) {
                    try {
                        console.log(`🤖 Getting response from ${botName}...`);

                        // Add a typing indicator for a bot
                        showBotTypingIndicator(botName);
                        // Simulate delay based on bot's reaction speed (already implemented in backend)
                        // Wait for the backend delay (no need to add extra delay here)
                        const botResponse = await fetch('/chatbot/get_bot_response', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                game_id: gameId,
                                message: message,
                                bot_name: botName,
                                conversation_context: conversationContext
                            })
                        });
                        // Remove typing indicator before showing the real message
                        removeBotTypingIndicator(botName);

                        if (botResponse.ok) {
                            const botData = await botResponse.json();
                            if (botData.success) {
                                // Add the text message
                                addMessageToChat('bot', botData.message, botData.bot_name);

                                // If this is Jim Nantz, speak the commentary
                                if (botData.bot_name === 'Jim Nantz' || botData.bot_name === 'jim_nantz') {
                                    console.log('🎤 Jim Nantz bot response detected:', botData.message);
                                    console.log('🎤 About to call jimNantzCommentVoice...');
                                    jimNantzCommentVoice(botData.message);
                                }

                                // Add this bot's response to conversation context for next bots
                                conversationContext.push({
                                    role: 'assistant',
                                    content: `${botData.bot_name}: ${botData.message}`
                                });

                                // Send GIF as a separate message if needed
                                if (await shouldBotSendGif(botData.bot_name)) {
                                    const searchTerms = extractSearchTerms(botData.message, botData.bot_name);
                                    const relevantGif = await getRelevantGif(searchTerms, botData.bot_name);
                                    addMessageToChat('bot', relevantGif, botData.bot_name, true);
                                }
                            } else {
                                console.error(`❌ Bot ${botName} failed:`, botData.message);
                                addMessageToChat('bot', `Sorry, ${botName} is having trouble responding.`, botName);
                            }
                        } else {
                            console.error(`❌ HTTP error for ${botName}:`, botResponse.status);
                            addMessageToChat('bot', `Sorry, ${botName} is having trouble connecting.`, botName);
                        }
                    } catch (error) {
                        console.error(`❌ Error getting response from ${botName}:`, error);
                        addMessageToChat('bot', `Sorry, ${botName} is having trouble connecting.`, botName);
                    }
                }
            } else if (data.message) {
                // Try both bot and bot_name fields to handle different response formats
                const botName = data.bot || data.bot_name;
                let message = data.message;

                // Add the text message first
                addMessageToChat('bot', message, botName);

                // If this is Jim Nantz, speak the commentary
                if (botName === 'Jim Nantz' || botName === 'jim_nantz') {
                    console.log('🎤 Jim Nantz response detected:', message);
                    console.log('🎤 About to call jimNantzCommentVoice...');
                    jimNantzCommentVoice(message);
                }

                // Send GIF as a separate message if needed
                if (await shouldBotSendGif(botName)) {
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

        // Add onload handler to scroll after GIF loads
        imgElement.onload = function() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        };
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
        // Add onload handler to scroll after image loads
        imgElement.onload = function() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        };
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

    // Always keep focus on chat input unless GIF modal/search is open/focused
    setTimeout(() => {
        const gifModal = document.getElementById('gifModal');
        const gifInput = document.getElementById('gifSearchInput');
        const chatInput = document.getElementById('chatInput');
        // If GIF modal is not visible or GIF input is not focused, focus chat input
        const gifModalOpen = gifModal && gifModal.style.display !== 'none' && gifModal.style.display !== '';
        const gifInputFocused = gifInput && document.activeElement === gifInput;
        if (!gifModalOpen || !gifInputFocused) {
            if (chatInput) chatInput.focus();
        }
    }, 10);
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
    // Only include Jim Nantz and current game opponents for proactive comments
    const allowed = ['Jim Nantz'];

    // Add all AI players from the current game
    if (currentGameState && currentGameState.players) {
        for (let i = 1; i < currentGameState.players.length; i++) {
            console.log('Adding player:', currentGameState.players[i]);
            allowed.push(currentGameState.players[i].name);
        }
    } else {
        console.log('No currentGameState or players found!');
    }

    console.log('Final allowed_bots for proactive:', allowed);
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
    }, 3000 + Math.random() * 3000); // 30-60 seconds og. 30000 is og.
}

// Also initialize chatbot when game board is shown
try {
    const originalStartGame = startGame;
    startGame = async function() {
        proactiveCommentSent = false;
        await originalStartGame();
        console.log('🎮 Game started - re-initializing chatbot');
        setTimeout(initializeChatbot, 100);

        // Focus chat input when game starts
        setTimeout(() => {
            const chatInput = document.getElementById('chatInput');
            if (chatInput) {
                chatInput.focus();
                console.log('🎯 Chat input focused on game start');
            }
        }, 200);
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
        chatInput.placeholder = 'Chat with opponents, Golf Pro/Bro...';
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
        chatInput.placeholder = 'Chat with opponents, Golf Pro/Bro...';
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

function updateChatInputVisibility() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');

    // All personalities now support chat
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.style.opacity = '1';
    sendBtn.style.opacity = '1';
    chatInput.style.pointerEvents = 'auto';
    sendBtn.style.pointerEvents = 'auto';

    // Update placeholder to reflect that users can chat with all opponents and approved bots
    chatInput.placeholder = 'Chat with opponents, Golf Pro/Bro...';
}

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
                console.log('🎤 Jim Nantz comment detected:', comment.message);
                console.log('🎤 About to call jimNantzCommentVoice...');
                jimNantzCommentVoice(comment.message);
            } else {
                console.log('🎤 Not Jim Nantz, bot_name is:', comment.bot_name);
            }

            // Prevent Jim Nantz and Golf Pro from sending GIFs
            if (comment.bot_name !== 'Jim Nantz' && comment.bot_name !== 'jim_nantz' && comment.bot_name !== 'Golf Pro' && shouldSendGif()) {
                // Extract relevant search terms from the message
                const searchTerms = extractSearchTerms(comment.message, comment.bot_name);
                const relevantGif = await getRelevantGif(searchTerms, comment.bot_name);
                addMessageToChat('bot', relevantGif, comment.bot_name, true); // true = GIF only
            }
        });
    }
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



document.getElementById('sendGifBtn').addEventListener('click', function() {
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
        sendUserGifToChat(gifUrl);
        document.getElementById('gifModal').style.display = 'none';
      };
      gifResults.appendChild(img);
    });
  } else {
    gifResults.textContent = 'No GIFs found.';
  }
  });
}

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

function updateChatParticipantsHeader() {
    const chatParticipants = document.getElementById('chatParticipants');
    if (!chatParticipants) return;

    let participants = [];

    // Add current game opponents only
    if (currentGameState && currentGameState.players) {
        for (let i = 1; i < currentGameState.players.length; i++) {
            participants.push(currentGameState.players[i].name);
        }
    }

    // Always add Golf Bro and Golf Pro with @ symbols
    participants.push('@Golf Bro', '@Golf Pro');

    // Create the display text - show actual opponent names instead of static "Opponents"
    let displayText = '';
    if (participants.length > 0) {
        displayText += participants.join(', ');
    } else {
        displayText += '@Golf Bro, @Golf Pro';
    }

    chatParticipants.textContent = displayText;
}

// Add a typing indicator for a bot
function showBotTypingIndicator(botName) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    // Remove any existing typing indicator for this bot
    removeBotTypingIndicator(botName);
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-message bot-message typing-indicator';
    typingDiv.dataset.botName = botName;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `<span class="typing-bot-name">${botName}</span> is typing <span class="typing-dots">...</span>`;
    typingDiv.appendChild(contentDiv);
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Remove the typing indicator for a bot
function removeBotTypingIndicator(botName) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    const indicators = chatMessages.querySelectorAll('.typing-indicator');
    indicators.forEach(div => {
        if (div.dataset.botName === botName) {
            div.remove();
        }
    });
}

// Check if a specific bot should send a GIF based on their personality
function shouldBotSendGif(botName) {
    // Prevent Jim Nantz and Golf Pro from sending GIFs
    if (botName === 'Jim Nantz' || botName === 'jim_nantz' || botName === 'Golf Pro') {
        return false;
    }
    // For other bots, use random chance (can be adjusted per bot later)
    return Math.random() < 0.25;
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

function updateCustomBotCount() {
    const countElement = document.getElementById('customBotCount');
    if (!countElement) return;

    const gameMode = document.getElementById('gameMode').value;
    const customBotCount = window.customBots ? Object.keys(window.customBots).length : 0;

    if (gameMode === '1v3') {
        if (customBotCount === 0) {
            countElement.textContent = '';
        } else if (customBotCount === 1) {
            countElement.textContent = '';
        } else if (customBotCount === 2) {
            countElement.textContent = '';
        } else if (customBotCount >= 3) {
            countElement.textContent = '';
        }
    } else {
        // 1v1 mode
        if (customBotCount === 0) {
            countElement.textContent = '';
        } else {
            countElement.textContent = `${customBotCount} custom bot${customBotCount > 1 ? 's' : ''} available`;
        }
    }
}







// === CUSTOM BOT MODAL ===
document.addEventListener('DOMContentLoaded', function() {
    console.log('🟢 MODAL: Setting up custom bot modal...');

    const createBtn = document.getElementById('createCustomBotBtn');
    const modal = document.getElementById('customBotModal');
    const multipleModal = document.getElementById('multipleBotsModal');
    const cancelBtn = document.getElementById('cancelCustomBotBtn');
    const saveBtn = document.getElementById('saveCustomBotBtn');
    const cancelMultipleBtn = document.getElementById('cancelMultipleBotsBtn');
    const saveMultipleBtn = document.getElementById('saveMultipleBotsBtn');
    const addAnotherBotBtn = document.getElementById('addAnotherBotBtn');

    // Make the Create Custom AI Bot button dark green
    if (createBtn) {
        createBtn.style.background = '#217a3a';
        createBtn.style.color = '#fff';
        createBtn.style.border = 'none';
    }

            // Initialize custom bot count display
    updateCustomBotCount();

// Voice system functions moved to voice.js





        // Placeholder bot templates (loaded directly in frontend)
    const placeholderBots = [
        {
            "name": "Golf Guru",
            "difficulty": "easy",
            "description": "A friendly golf enthusiast who loves to chat about the game and gives encouraging advice. Always optimistic and supportive."
        },
        {
            "name": "Strategy Master",
            "difficulty": "medium",
            "description": "A calculated player who thinks several moves ahead. Analyzes the game carefully and makes strategic decisions."
        },
        {
            "name": "Tiger Clone",
            "difficulty": "hard",
            "description": "An aggressive, competitive player who plays to win. Uses advanced strategies and takes calculated risks."
        },
        {
            "name": "Happy Gilmore",
            "difficulty": "easy",
            "description": "A fun-loving player who doesn't take the game too seriously. Makes jokes and keeps the mood light."
        },
        {
            "name": "Course Pro",
            "difficulty": "medium",
            "description": "A knowledgeable player who understands the nuances of the game. Gives helpful tips and explains strategies."
        },
        {
            "name": "Pressure Player",
            "difficulty": "hard",
            "description": "Thrives under pressure and makes bold moves when it counts. Confident and decisive in critical moments."
        },
        {
            "name": "Rookie Golfer",
            "difficulty": "easy",
            "description": "A beginner who's still learning the game. Makes mistakes but is eager to improve and learn from others."
        },
        {
            "name": "Veteran Player",
            "difficulty": "medium",
            "description": "An experienced player who has seen it all. Calm under pressure and shares wisdom from years of playing."
        },
        {
            "name": "Champion Mindset",
            "difficulty": "hard",
            "description": "A winner who knows how to close out games. Focused, determined, and always looking for the winning edge."
        }
    ];

    // Track which templates have been used in the current session
    let usedTemplateIndices = new Set();

    console.log('📋 Loaded', placeholderBots.length, 'placeholder bots');

        // Function to get a random unused template
    function getRandomUnusedTemplate() {
        // Get available template indices (not used yet)
        const availableIndices = [];
        for (let i = 0; i < placeholderBots.length; i++) {
            if (!usedTemplateIndices.has(i)) {
                availableIndices.push(i);
            }
        }

        // If all templates are used, reset the used set and start over
        if (availableIndices.length === 0) {
            usedTemplateIndices.clear();
            for (let i = 0; i < placeholderBots.length; i++) {
                availableIndices.push(i);
            }
            console.log('📋 Reset template pool - all templates used');
        }

        // Pick a random available template
        const randomIndex = availableIndices[Math.floor(Math.random() * availableIndices.length)];
        usedTemplateIndices.add(randomIndex);

        return placeholderBots[randomIndex];
    }

    // Function to load template into single bot form
    function loadTemplateIntoSingleForm() {
        if (placeholderBots.length === 0) {
            alert('No templates available.');
            return;
        }

        // Get a random unused template
        const template = getRandomUnusedTemplate();

        document.getElementById('customBotName').value = template.name;
        document.getElementById('customBotDifficulty').value = template.difficulty;
        document.getElementById('customBotDescription').value = template.description;

        console.log('📋 Loaded template:', template.name);
    }

            // Function to load template into a specific bot section
    function loadTemplateIntoBotSection(botSection, botIndex) {
        if (placeholderBots.length === 0) return;

        // Get a random unused template
        const template = getRandomUnusedTemplate();

        // Fill with template data
        const nameInput = botSection.querySelector('input[type="text"]');
        const difficultySelect = botSection.querySelector('select');
        const descTextarea = botSection.querySelector('textarea');

        nameInput.value = template.name;
        difficultySelect.value = template.difficulty;
        descTextarea.value = template.description;

        console.log('📋 Loaded template for bot', botIndex + 1, ':', template.name);
    }

    // Function to create a bot section
    function createBotSection(botNumber) {
        const difficulties = ['Easy', 'Medium', 'Hard'];
        const defaultDifficulty = difficulties[Math.min(botNumber - 1, 2)]; // Default to Hard if more than 3

        const botSection = document.createElement('div');
        botSection.className = 'bot-section';
        botSection.style.cssText = 'border:1px solid #ddd; padding:15px; border-radius:5px; min-width:280px; max-width:320px; flex:1;';
        botSection.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <h4 style="margin:0;">Bot ${botNumber}</h4>
                ${botNumber > 1 ? `<button type="button" class="remove-bot-btn" style="background:#dc3545; color:white; border:none; padding:2px 8px; border-radius:3px; cursor:pointer;">Remove</button>` : ''}
            </div>
            <div style="display:flex; gap:10px; margin-bottom:10px;">
                <div style="flex:2;">
                    <label for="multiBot${botNumber}Name">Name:</label>
                    <input type="text" id="multiBot${botNumber}Name" style="width:100%;" placeholder="Bot Name" />
                </div>
                <div style="flex:1;">
                    <label for="multiBot${botNumber}Difficulty">Difficulty:</label>
                    <select id="multiBot${botNumber}Difficulty" style="width:100%;">
                        <option value="easy" ${defaultDifficulty === 'Easy' ? 'selected' : ''}>Easy</option>
                        <option value="medium" ${defaultDifficulty === 'Medium' ? 'selected' : ''}>Medium</option>
                        <option value="hard" ${defaultDifficulty === 'Hard' ? 'selected' : ''}>Hard</option>
                    </select>
                </div>
            </div>
            <label for="multiBot${botNumber}Description">Personality/Description:</label>
            <textarea id="multiBot${botNumber}Description" style="width:100%; margin-bottom:10px;" rows="2" placeholder="Describe this bot's personality..."></textarea>
        `;

        // Add remove button functionality
        const removeBtn = botSection.querySelector('.remove-bot-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', function() {
                botSection.remove();
                updateBotNumbers();
            });
        }

        return botSection;
    }

        // Function to update bot numbers after removal
    function updateBotNumbers() {
        const botSections = document.querySelectorAll('.bot-section');
        botSections.forEach((section, index) => {
            const botNumber = index + 1;

            const title = section.querySelector('h4');
            title.textContent = `Bot ${botNumber}`;

            const nameInput = section.querySelector('input[type="text"]');
            nameInput.id = `multiBot${botNumber}Name`;
            nameInput.placeholder = 'Bot Name';

            const difficultySelect = section.querySelector('select');
            difficultySelect.id = `multiBot${botNumber}Difficulty`;

            const descTextarea = section.querySelector('textarea');
            descTextarea.id = `multiBot${botNumber}Description`;

            // Update remove button (first bot can't be removed)
            const removeBtn = section.querySelector('.remove-bot-btn');
            if (botNumber === 1) {
                if (removeBtn) removeBtn.remove();
            } else {
                if (!removeBtn) {
                    const newRemoveBtn = document.createElement('button');
                    newRemoveBtn.type = 'button';
                    newRemoveBtn.className = 'remove-bot-btn';
                    newRemoveBtn.style.cssText = 'background:#dc3545; color:white; border:none; padding:2px 8px; border-radius:3px; cursor:pointer;';
                    newRemoveBtn.textContent = 'Remove';
                    newRemoveBtn.addEventListener('click', function() {
                        section.remove();
                        updateBotNumbers();
                    });
                    title.parentNode.appendChild(newRemoveBtn);
                }
            }
        });
    }

    // Debug: Check if elements exist
    console.log('🟢 MODAL: Elements found:', {
        createBtn: !!createBtn,
        modal: !!modal,
        multipleModal: !!multipleModal,
        cancelBtn: !!cancelBtn,
        saveBtn: !!saveBtn,
        cancelMultipleBtn: !!cancelMultipleBtn,
        saveMultipleBtn: !!saveMultipleBtn
    });

            // Show smart modal based on game mode
    if (createBtn) {
        createBtn.addEventListener('click', function() {
            const gameMode = document.getElementById('gameMode').value;
            console.log('🔥 MODAL: Create button clicked! Game mode:', gameMode);

            if (gameMode === '1v3') {
                // Show multiple bots modal for 1v3 mode
                multipleModal.style.display = 'flex';

                // Initialize with one bot section and load template
                const container = document.getElementById('botSectionsContainer');
                container.innerHTML = '';
                const botSection = createBotSection(1);
                container.appendChild(botSection);

                // Load random template for the first bot
                loadTemplateIntoBotSection(botSection, 0);

                console.log('🔥 MODAL: Multiple Modal display set to flex');
            } else {
                // Show single bot modal for 1v1 mode
                modal.style.display = 'flex';

                // Load random template for single bot
                loadTemplateIntoSingleForm();

                console.log('🔥 MODAL: Single Modal display set to flex');
            }
        });
    }

            // Add Another Bot button functionality
    if (addAnotherBotBtn) {
        addAnotherBotBtn.addEventListener('click', function() {
            const container = document.getElementById('botSectionsContainer');
            const currentBotCount = container.children.length;

            if (currentBotCount >= 3) {
                alert('Maximum 3 bots allowed for 1v3 mode.');
                return;
            }

            const botSection = createBotSection(currentBotCount + 1);
            container.appendChild(botSection);

            // Load random template for the new bot
            loadTemplateIntoBotSection(botSection, currentBotCount);

            console.log('🔥 MODAL: Added bot section', currentBotCount + 1);
        });
    }



    // Hide single bot modal on cancel
    if (cancelBtn && modal) {
        cancelBtn.addEventListener('click', function() {
            console.log('🔥 MODAL: Cancel button clicked!');
            modal.style.display = 'none';
        });
    }

    // Hide multiple bots modal on cancel
    if (cancelMultipleBtn && multipleModal) {
        cancelMultipleBtn.addEventListener('click', function() {
            console.log('🔥 MODAL: Cancel Multiple button clicked!');
            multipleModal.style.display = 'none';
        });
    }

    // Hide single bot modal on outside click
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                console.log('🔥 MODAL: Clicked outside, closing...');
                modal.style.display = 'none';
            }
        });
    }

    // Hide multiple bots modal on outside click
    if (multipleModal) {
        multipleModal.addEventListener('click', function(e) {
            if (e.target === multipleModal) {
                console.log('🔥 MODAL: Clicked outside multiple modal, closing...');
                multipleModal.style.display = 'none';
            }
        });
    }

    // Save custom bot
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            console.log('🔥 MODAL: Save button clicked!');
            const name = document.getElementById('customBotName').value.trim();
            const difficulty = document.getElementById('customBotDifficulty').value;
            const description = document.getElementById('customBotDescription').value.trim();

            if (!name) {
                alert('Please enter a name for your custom bot.');
                return;
            }

            // Send to backend
            fetch('/api/create_custom_bot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, difficulty, description })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Add to dropdown
                    const botSelect = document.getElementById('botNameSelect');
                    const option = document.createElement('option');
                    option.value = data.bot_id;
                    option.textContent = `${data.bot.name} (Custom)`;
                    option.dataset.difficulty = data.bot.difficulty;
                    option.dataset.description = data.bot.description;
                    botSelect.appendChild(option);
                    botSelect.value = data.bot_id;

                    // Store globally
                    if (!window.customBots) window.customBots = {};
                    window.customBots[data.bot_id] = data.bot;

                    // Update custom bot count display
                    updateCustomBotCount();

                    // Clear the form
                    document.getElementById('customBotName').value = '';
                    document.getElementById('customBotDifficulty').value = 'easy';
                    document.getElementById('customBotDescription').value = '';

                    // Hide modal
                    modal.style.display = 'none';

                    console.log('✅ MODAL: Bot created successfully!', data.bot);
                } else {
                    alert('Error creating bot: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error creating bot:', error);
                alert('Error creating bot. Please try again.');
            });
        });
    }

            // Save multiple custom bots
    if (saveMultipleBtn) {
        saveMultipleBtn.addEventListener('click', function() {
            console.log('🔥 MODAL: Save Multiple button clicked!');

            // Get all bot sections
            const botSections = document.querySelectorAll('.bot-section');
            const botsToCreate = [];

                        // Validate and collect bot data
            for (let i = 0; i < botSections.length; i++) {
                const botNumber = i + 1;
                const nameInput = document.getElementById(`multiBot${botNumber}Name`);
                const difficultySelect = document.getElementById(`multiBot${botNumber}Difficulty`);
                const descInput = document.getElementById(`multiBot${botNumber}Description`);

                if (!nameInput || !nameInput.value.trim()) {
                    alert(`Please enter a name for Bot ${botNumber}.`);
                    return;
                }

                if (!difficultySelect || !difficultySelect.value) {
                    alert(`Please select a difficulty for Bot ${botNumber}.`);
                    return;
                }

                botsToCreate.push({
                    name: nameInput.value.trim(),
                    difficulty: difficultySelect.value,
                    description: descInput ? descInput.value.trim() : ''
                });
            }

            if (botsToCreate.length === 0) {
                alert('Please add at least one bot.');
                return;
            }

            let createdCount = 0;
            const totalBots = botsToCreate.length;

            botsToCreate.forEach((botData, index) => {
                fetch('/api/create_custom_bot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(botData)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Add to dropdown
                        const botSelect = document.getElementById('botNameSelect');
                        const option = document.createElement('option');
                        option.value = data.bot_id;
                        option.textContent = `${data.bot.name} (Custom)`;
                        option.dataset.difficulty = data.bot.difficulty;
                        option.dataset.description = data.bot.description;
                        botSelect.appendChild(option);

                        // Store globally
                        if (!window.customBots) window.customBots = {};
                        window.customBots[data.bot_id] = data.bot;

                        createdCount++;

                                                                        if (createdCount === totalBots) {
                            // All bots created successfully
                            updateCustomBotCount();
                            multipleModal.style.display = 'none';

                            // Clear the form - only clear fields that exist
                            const botSections = document.querySelectorAll('.bot-section');
                            botSections.forEach((section, index) => {
                                const botNumber = index + 1;
                                const nameInput = document.getElementById(`multiBot${botNumber}Name`);
                                const descInput = document.getElementById(`multiBot${botNumber}Description`);
                                if (nameInput) nameInput.value = '';
                                if (descInput) descInput.value = '';
                            });

                            console.log(`✅ MODAL: All ${totalBots} bots created successfully!`);
                        }
                    } else {
                        alert(`Error creating bot ${index + 1}: ${data.error || 'Unknown error'}`);
                    }
                })
                .catch(error => {
                    console.error(`Error creating bot ${index + 1}:`, error);
                    alert(`Error creating bot ${index + 1}. Please try again.`);
                });
            });
        });
    }
});

// Test Jim Nantz voice directly
jimNantzCommentVoice("Hello friends, what a beautiful day for golf!")

// Check voice settings
// Voice status logging moved to voice.js
