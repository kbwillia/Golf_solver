// ===== CUSTOM BOT MODAL FUNCTIONALITY =====

let customBotCount = 1;
let placeholderData = null;

// Load placeholder data from JSON file
async function loadPlaceholderData() {
    try {
        const response = await fetch('/static/custom_bot.json');
        placeholderData = await response.json();
        console.log('✅ Loaded placeholder bot data:', placeholderData);
    } catch (error) {
        console.log('❌ Could not load placeholder data:', error);
        // Fallback placeholder data
        placeholderData = {
            placeholder_bots: [
                {
                    name: "Karen",
                    description: "Friendly player who loves to chat and make new friends on the course.",
                    difficulty: "easy"
                },
                {
                    name: "Bob",
                    description: "Strategic thinker who carefully considers every move.",
                    difficulty: "medium"
                },
                {
                    name: "Alice",
                    description: "Competitive player who takes the game seriously.",
                    difficulty: "hard"
                }
            ]
        };
    }
}

// Get random placeholder bot data
function getRandomPlaceholderBot() {
    if (!placeholderData || !placeholderData.placeholder_bots) {
        return {
            name: "Bot",
            description: "A custom golf bot with unique personality.",
            difficulty: "medium"
        };
    }

    const randomIndex = Math.floor(Math.random() * placeholderData.placeholder_bots.length);
    return placeholderData.placeholder_bots[randomIndex];
}

// Fallback initialization function
function initializeCustomBots() {
    console.log('🔧 Custom bots.js: initializeCustomBots() called');

    const createCustomBotBtn = document.getElementById('createCustomBotBtn');
    const customBotModal = document.getElementById('customBotModal');
    const multipleBotsModal = document.getElementById('multipleBotsModal');
    const closeCustomBotBtn = document.getElementById('cancelCustomBotBtn');
    const saveCustomBotBtn = document.getElementById('saveCustomBotBtn');
    const addAnotherBotBtn = document.getElementById('addAnotherBotBtn');
    const saveMultipleBotsBtn = document.getElementById('saveMultipleBotsBtn');
    const cancelMultipleBotsBtn = document.getElementById('cancelMultipleBotsBtn');
    const botSectionsContainer = document.getElementById('botSectionsContainer');
    const gameModeSelect = document.getElementById('gameMode');

    console.log('🔧 Custom bots.js: Elements found:', {
        createCustomBotBtn: !!createCustomBotBtn,
        customBotModal: !!customBotModal,
        multipleBotsModal: !!multipleBotsModal,
        gameModeSelect: !!gameModeSelect
    });

    // Show appropriate modal when Create Custom Bot button is clicked
    if (createCustomBotBtn) {
        console.log('🔧 Custom bots.js: Adding click listener to createCustomBotBtn');
        createCustomBotBtn.addEventListener('click', function() {
            console.log('🔧 Custom bots.js: Create Custom Bot button clicked!');
            // Check if we're in 1v3 mode
            const is1v3Mode = gameModeSelect && gameModeSelect.value === '1v3';
            console.log('🔧 Custom bots.js: Is 1v3 mode?', is1v3Mode);

            if (is1v3Mode) {
                // Show multiple bots modal for 1v3 mode
                if (multipleBotsModal) {
                    console.log('🔧 Custom bots.js: Showing multiple bots modal');
                    multipleBotsModal.style.display = 'block';
                    customBotCount = 1;
                    updateMultipleBotsForm();
                }
            } else {
                // Show single bot modal for 1v1 mode
                if (customBotModal) {
                    console.log('🔧 Custom bots.js: Showing single bot modal');
                    customBotModal.style.display = 'block';
                    // Populate single bot modal with random placeholder
                    populateSingleBotForm();
                }
            }
        });
    } else {
        console.error('❌ Custom bots.js: createCustomBotBtn not found!');
    }

    // Close single bot modal when Cancel button is clicked
    if (closeCustomBotBtn) {
        closeCustomBotBtn.addEventListener('click', function() {
            if (customBotModal) {
                customBotModal.style.display = 'none';
                // Clear form
                document.getElementById('customBotName').value = '';
                document.getElementById('customBotDifficulty').value = 'easy';
                document.getElementById('customBotDescription').value = '';
            }
        });
    }

    // Close single bot modal when clicking outside of it
    if (customBotModal) {
        customBotModal.addEventListener('click', function(e) {
            if (e.target === customBotModal) {
                customBotModal.style.display = 'none';
                // Clear form
                document.getElementById('customBotName').value = '';
                document.getElementById('customBotDifficulty').value = 'easy';
                document.getElementById('customBotDescription').value = '';
            }
        });
    }

    // Save single custom bot
    if (saveCustomBotBtn) {
        saveCustomBotBtn.addEventListener('click', function() {
            saveSingleCustomBot();
        });
    }

    // Close multiple bots modal when Cancel button is clicked
    if (cancelMultipleBotsBtn) {
        cancelMultipleBotsBtn.addEventListener('click', function() {
            if (multipleBotsModal) {
                multipleBotsModal.style.display = 'none';
                // Clear form
                if (botSectionsContainer) {
                    botSectionsContainer.innerHTML = '';
                }
                customBotCount = 1;
            }
        });
    }

    // Close multiple bots modal when clicking outside of it
    if (multipleBotsModal) {
        multipleBotsModal.addEventListener('click', function(e) {
            if (e.target === multipleBotsModal) {
                multipleBotsModal.style.display = 'none';
                // Clear form
                if (botSectionsContainer) {
                    botSectionsContainer.innerHTML = '';
                }
                customBotCount = 1;
            }
        });
    }

    // Add another bot section (up to 3 total for 1v3 mode)
    if (addAnotherBotBtn) {
        addAnotherBotBtn.addEventListener('click', function() {
            if (customBotCount < 3) {
                customBotCount++;
                updateMultipleBotsForm();
            }
        });
    }

    // Save multiple custom bots
    if (saveMultipleBotsBtn) {
        saveMultipleBotsBtn.addEventListener('click', function() {
            saveMultipleCustomBots();
        });
    }

    // Load existing custom bots when page loads
    loadExistingCustomBots();

    // Initialize game mode buttons
    initializeGameModeButtons();

    // Initialize holes buttons
    initializeHolesButtons();
}

// Initialize custom bot modal functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Custom bots.js: DOMContentLoaded event fired');
    // Load placeholder data first
    loadPlaceholderData().then(() => {
        initializeCustomBots();
    });
});

// Fallback: If DOMContentLoaded already fired, initialize immediately
if (document.readyState === 'loading') {
    console.log('🔧 Custom bots.js: DOM still loading, waiting for DOMContentLoaded');
} else {
    console.log('🔧 Custom bots.js: DOM already loaded, initializing immediately');
    loadPlaceholderData().then(() => {
        initializeCustomBots();
    });
}

// Test function to verify button exists
function testCustomBotButton() {
    const btn = document.getElementById('createCustomBotBtn');
    if (btn) {
        console.log('✅ Custom bot button found and clickable');
        // Add a test click handler
        btn.onclick = function() {
            console.log('✅ Custom bot button click test successful');
            // Remove test handler and reinitialize
            btn.onclick = null;
            initializeCustomBots();
        };
    } else {
        console.error('❌ Custom bot button not found in test');
    }
}

// Run test after a short delay
setTimeout(testCustomBotButton, 1000);

function saveSingleCustomBot() {
    const name = document.getElementById('customBotName').value.trim();
    const description = document.getElementById('customBotDescription').value.trim();
    const difficulty = document.getElementById('customBotDifficulty').value;

    if (!name || !description || !difficulty) {
        alert('Please fill in all fields');
        return;
    }

    // Save single bot
    fetch('/save_custom_bots', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            bots: [{
                name: name,
                description: description,
                difficulty: difficulty
            }]
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal without showing success popup
            document.getElementById('customBotModal').style.display = 'none';
            // Clear form
            document.getElementById('customBotName').value = '';
            document.getElementById('customBotDifficulty').value = 'easy';
            document.getElementById('customBotDescription').value = '';

            // Refresh bot selection buttons to show the new bot
            renderBotSelectRow();
        } else {
            alert('Error saving custom bot: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error saving custom bot:', error);
        alert('Error saving custom bot. Please try again.');
    });
}

function updateMultipleBotsForm() {
    const container = document.getElementById('botSectionsContainer');
    const addAnotherBtn = document.getElementById('addAnotherBotBtn');

    if (!container) return;

    // Clear existing bot sections
    container.innerHTML = '';

    // Create bot sections
    for (let i = 0; i < customBotCount; i++) {
        const botSection = document.createElement('div');
        botSection.className = 'custom-bot-section';
        botSection.innerHTML = `
            <div class="bot-section-header">
                <h4 class="bot-section-title">Custom Bot ${i + 1}</h4>
                ${customBotCount > 1 ? `<button type="button" class="remove-bot-btn" onclick="removeBotSection(${i})">×</button>` : ''}
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="botName${i}" class="form-label">Bot Name:</label>
                    <input type="text" id="botName${i}" placeholder="Enter bot name" required class="form-input" value="">
                </div>
                <div class="form-group">
                    <label for="botDifficulty${i}" class="form-label">Difficulty:</label>
                    <select id="botDifficulty${i}" required class="form-select">
                        <option value="">Select difficulty</option>
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label for="botDescription${i}" class="form-label">Description:</label>
                <textarea id="botDescription${i}" placeholder="Enter bot description" required class="form-textarea"></textarea>
            </div>
        `;
        container.appendChild(botSection);
    }

    // Show/hide add button based on bot count (max 3 for 1v3 mode)
    if (addAnotherBtn) {
        if (customBotCount >= 3) {
            addAnotherBtn.style.display = 'none';
            addAnotherBtn.textContent = 'Maximum 3 bots reached';
        } else {
            addAnotherBtn.style.display = 'block';
            addAnotherBtn.textContent = `Add Another Bot (${customBotCount}/3)`;
        }
    }
}

// Function to remove a bot section
function removeBotSection(index) {
    if (customBotCount > 1) {
        customBotCount--;
        updateMultipleBotsForm();
    }
}

function saveMultipleCustomBots() {
    const bots = [];
    let isValid = true;

    // Collect all bot data
    for (let i = 0; i < customBotCount; i++) {
        const name = document.getElementById(`botName${i}`).value.trim();
        const description = document.getElementById(`botDescription${i}`).value.trim();
        const difficulty = document.getElementById(`botDifficulty${i}`).value;

        if (!name || !description || !difficulty) {
            alert(`Please fill in all fields for Custom Bot ${i + 1}`);
            isValid = false;
            break;
        }

        bots.push({
            name: name,
            description: description,
            difficulty: difficulty
        });
    }

    if (!isValid) return;

    // Save bots to backend
    fetch('/save_custom_bots', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bots: bots })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close modal without showing success popup
            document.getElementById('multipleBotsModal').style.display = 'none';
            // Clear form
            const container = document.getElementById('botSectionsContainer');
            if (container) {
                container.innerHTML = '';
            }
            customBotCount = 1;

            // Refresh bot selection buttons to show the new bots
            renderBotSelectRow();
        } else {
            alert('Error saving custom bots: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error saving custom bots:', error);
        alert('Error saving custom bots. Please try again.');
    });
}

// Load existing custom bots when page loads
function loadExistingCustomBots() {
    // This function is now handled by renderBotSelectRow() which loads from JSON
    console.log('✅ Custom bots are now loaded automatically from JSON via renderBotSelectRow()');
}

function loadOpponents() {
    // This function should be called to refresh the opponent dropdown
    // after custom bots are saved
    const opponentSelect = document.getElementById('botNameSelect');
    if (opponentSelect) {
        // Trigger a refresh of the opponent list
        // This might need to be implemented based on how opponents are loaded
        console.log('Opponents should be refreshed');
    }
}

// Populate single bot form with random placeholder data
function populateSingleBotForm() {
    const nameInput = document.getElementById('customBotName');
    const difficultySelect = document.getElementById('customBotDifficulty');
    const descriptionTextarea = document.getElementById('customBotDescription');

    if (nameInput) nameInput.value = '';
    if (difficultySelect) difficultySelect.value = '';
    if (descriptionTextarea) descriptionTextarea.value = '';
}



// Bot selection button logic for setup screen

// Special announcer bots (not selectable opponents)
const announcerBots = [
  {
    value: 'jim_nantz',
    name: 'Jim Nantz',
    role: 'announcer',
    desc: 'Professional golf commentator who provides expert analysis and commentary throughout your game.'
  }
];

// Track selected bots for multi-selection mode
window.selectedBots = []; // Will be populated when bots are loaded

async function renderBotSelectRow() {
  const row = document.getElementById('botSelectRow');
  const imageContainer = document.getElementById('aiBotImageContainer');
  if (!row) return;

  // Load bots from custom_bot.json
  let allBots = [];

  try {
    // Load custom bots from JSON
    const response = await fetch('/static/custom_bot.json');
    const data = await response.json();

    // Add placeholder bots from JSON
    if (data.placeholder_bots && data.placeholder_bots.length > 0) {
      data.placeholder_bots.forEach(bot => {
        allBots.push({
          value: 'custom_' + bot.name.toLowerCase().replace(' ', '_').replace('-', '_'),
          name: bot.name,
          difficulty: bot.difficulty.charAt(0).toUpperCase() + bot.difficulty.slice(1),
          difficultyClass: bot.difficulty,
          desc: bot.description || 'Custom bot with unique personality.'
        });
      });
    }

    // Add custom bots from JSON (user-created bots)
    if (data.custom_bots && Object.keys(data.custom_bots).length > 0) {
      Object.entries(data.custom_bots).forEach(([bot_id, bot_data]) => {
        allBots.push({
          value: bot_id, // e.g., "custom_fat_bastard"
          name: bot_data.name,
          difficulty: bot_data.difficulty.charAt(0).toUpperCase() + bot_data.difficulty.slice(1),
          difficultyClass: bot_data.difficulty,
          desc: bot_data.description || 'Custom bot with unique personality.'
        });
      });
    }
  } catch (error) {
    console.log('Could not load custom bots from JSON:', error);
  }

  // Load existing custom bots from server (for backward compatibility)
  try {
    const serverResponse = await fetch('/get_custom_bots');
    const serverData = await serverResponse.json();

    if (serverData.success && serverData.bots) {
      serverData.bots.forEach(bot => {
        // Check if this bot is already in allBots (from JSON)
        const existingBot = allBots.find(existing => existing.value === bot.id);
        if (!existingBot) {
          allBots.push({
            value: bot.id,
            name: bot.name,
            difficulty: bot.difficulty.charAt(0).toUpperCase() + bot.difficulty.slice(1),
            difficultyClass: bot.difficulty,
            desc: bot.description || 'Custom bot with unique personality.'
          });
        }
      });
    }
  } catch (error) {
    console.log('Could not load existing custom bots from server:', error);
  }

  // If no bots found, show a message
  if (allBots.length === 0) {
    row.innerHTML = '<p style="text-align: center; color: #666; font-style: italic;">No bots found. Create some custom bots to get started!</p>';
    return;
  }

  // Update selected bots if current selection is not in available bots
  if (window.selectedBots.length > 0) {
    const availableBotValues = allBots.map(bot => bot.value);
    window.selectedBots = window.selectedBots.filter(bot => availableBotValues.includes(bot));
    if (window.selectedBots.length === 0) {
      // Pick a random bot if none of the previous selection is available
      const randomIdx = Math.floor(Math.random() * allBots.length);
      window.selectedBots = [allBots[randomIdx].value];
    }
  } else {
    // Pick a random bot for initial selection
    const randomIdx = Math.floor(Math.random() * allBots.length);
    window.selectedBots = [allBots[randomIdx].value];
  }

  // Render all bots
  row.innerHTML = '';
  allBots.forEach((bot, idx) => {
    const btn = document.createElement('button');
    btn.type = 'button';

    // Determine if this bot is selected
    const isSelected = window.selectedBots.includes(bot.value);
    const isMultiMode = isMultiSelectionMode();

    btn.className = 'bot-select-btn' +
      (isSelected ? (isMultiMode ? ' multi-selected' : ' selected') : '');
    btn.setAttribute('data-bot', bot.value);

    // No JS truncation, let CSS handle it
    btn.innerHTML = `
      <div class="bot-header">
        <span class="bot-name">${bot.name}</span>
        <span class="bot-difficulty ${bot.difficultyClass}">${bot.difficulty}</span>
      </div>
      <span class="bot-desc bot-desc-short">${bot.desc}</span>
    `;
    btn.onclick = () => selectBotButton(bot.value);
    row.appendChild(btn);
  });

  // Set initial selected bot value for backward compatibility
  window.selectedBotValue = window.selectedBots[0];
  console.log(`✅ Rendered ${allBots.length} bots from custom_bot.json (placeholder + custom)`);

  // Update the opponent display to show the initially selected bot
  updateOpponentDisplay();

  // Scroll the selected bot into view
  const selectedBtn = Array.from(row.children).find(btn => btn.classList.contains('selected') || btn.classList.contains('multi-selected'));
  if (selectedBtn) {
    selectedBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  // Show selected bot images and descriptions
  updateAIBotImageContainer(allBots);
}

function updateAIBotImageContainer(allBots) {
  const imageContainer = document.getElementById('aiBotImageContainer');
  if (!imageContainer) return;
  imageContainer.innerHTML = '';

  if (!window.selectedBots || window.selectedBots.length === 0) {
    imageContainer.innerHTML = '<div style="color:#888; font-style:italic; margin-top:24px;"></div>';
    return;
  }

  window.selectedBots.forEach(botValue => {
    const bot = allBots.find(b => b.value === botValue);
    if (!bot) return;
    // Try to match bot name to image filename
    const imgName = bot.name.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.png';
    const imgPath = `/static/AI_bot_images/${imgName}`;

    // Create a row container for image + text
    const rowDiv = document.createElement('div');
    rowDiv.className = 'ai-bot-row';

    const img = document.createElement('img');
    img.src = imgPath;
    img.alt = bot.name;
    img.className = 'ai-bot-img';
    img.onerror = function() {
      this.style.display = 'none';
    };

    // Text container
    const textDiv = document.createElement('div');
    textDiv.className = 'ai-bot-info';

    const name = document.createElement('div');
    name.className = 'ai-bot-name';
    name.innerText = bot.name;

    const desc = document.createElement('div');
    desc.className = 'ai-bot-desc';
    desc.innerText = bot.desc;

    textDiv.appendChild(name);
    textDiv.appendChild(desc);
    rowDiv.appendChild(img);
    rowDiv.appendChild(textDiv);
    imageContainer.appendChild(rowDiv);
  });
}

function isMultiSelectionMode() {
  // Always allow multi-selection now (1-3 bots)
  return true;
}

function selectBotButton(botValue) {
  const row = document.getElementById('botSelectRow');
  if (!row) return;

  const currentCount = window.selectedBots.length;
  const index = window.selectedBots.indexOf(botValue);
  const maxBots = 3; // Allow up to 3 bots for 1v3 mode

  if (index > -1) {
    // Remove if already selected (now allow removing even the last bot)
    window.selectedBots.splice(index, 1);
  } else {
    // Add if not selected (up to max limit)
    if (currentCount < maxBots) {
      window.selectedBots.push(botValue);
    } else {
      // If at max, replace the first bot with the new selection
      window.selectedBots.shift();
      window.selectedBots.push(botValue);
    }
  }

  // Update visual state - always use multi-selected style now
  Array.from(row.children).forEach(btn => {
    const btnValue = btn.getAttribute('data-bot');
    const isSelected = window.selectedBots.includes(btnValue);

    btn.classList.remove('selected', 'multi-selected');
    if (isSelected) {
      btn.classList.add('multi-selected');
    }
  });

  // Update backward compatibility
  window.selectedBotValue = window.selectedBots[0];

  console.log(`Selected bots: ${window.selectedBots.join(', ')}`);

  // Update the opponent display
  updateOpponentDisplay();

  // Update the AI bot image container
  // Find allBots from the current botSelectRow render
  const allBots = Array.from(row.children).map(btn => {
    return {
      value: btn.getAttribute('data-bot'),
      name: btn.querySelector('.bot-name')?.innerText || '',
      desc: btn.querySelector('.bot-desc')?.innerText || '',
      difficulty: btn.querySelector('.bot-difficulty')?.innerText || '',
      difficultyClass: btn.querySelector('.bot-difficulty')?.className?.replace('bot-difficulty', '').trim() || ''
    };
  });
  updateAIBotImageContainer(allBots);
}

// Listen for game mode changes to update selection behavior
function initializeGameModeButtons() {
  const gameMode1v1 = document.getElementById('gameMode1v1');
  const gameMode1v2 = document.getElementById('gameMode1v2');
  const gameMode1v3 = document.getElementById('gameMode1v3');

  console.log('🎯 Initializing game mode buttons:', {
    '1v1 found': !!gameMode1v1,
    '1v2 found': !!gameMode1v2,
    '1v3 found': !!gameMode1v3,
    '1v1 onclick': gameMode1v1 ? gameMode1v1.onclick : 'none',
    '1v2 onclick': gameMode1v2 ? gameMode1v2.onclick : 'none',
    '1v3 onclick': gameMode1v3 ? gameMode1v3.onclick : 'none'
  });

  if (gameMode1v1 && gameMode1v2 && gameMode1v3) {
    // Remove any existing listeners to prevent conflicts
    gameMode1v1.removeEventListener('click', handle1v1Mode);
    gameMode1v2.removeEventListener('click', handle1v2Mode);
    gameMode1v3.removeEventListener('click', handle1v3Mode);

    // Add new listeners
    gameMode1v1.addEventListener('click', handle1v1Mode);
    gameMode1v2.addEventListener('click', handle1v2Mode);
    gameMode1v3.addEventListener('click', handle1v3Mode);

    // Test if buttons are clickable
    gameMode1v1.style.pointerEvents = 'auto';
    gameMode1v2.style.pointerEvents = 'auto';
    gameMode1v3.style.pointerEvents = 'auto';

    console.log('🎯 Game mode button listeners attached successfully');
  } else {
    console.error('❌ Game mode buttons not found!');
  }
}

function handle1v1Mode() {
  console.log('🎯 1v1 mode button clicked!');

  // Set the button to active state
  const gameMode1v1 = document.getElementById('gameMode1v1');
  const gameMode1v3 = document.getElementById('gameMode1v3');

  if (gameMode1v1 && gameMode1v3) {
    gameMode1v1.classList.add('active');
    gameMode1v3.classList.remove('active');
    console.log('🎯 1v1 button set to active state');
  }

  // Call the setGameMode function to properly register the mode
  if (typeof setGameMode === 'function') {
    setGameMode('1v1');
  }

  // Switch to single selection mode
  if (window.selectedBots.length > 1) {
    window.selectedBots = [window.selectedBots[0]];
    renderBotSelectRow();
  }
}

function handle1v2Mode() {
  console.log('🎯 1v2 mode button clicked!');
  const gameMode1v1 = document.getElementById('gameMode1v1');
  const gameMode1v2 = document.getElementById('gameMode1v2');
  const gameMode1v3 = document.getElementById('gameMode1v3');

  if (gameMode1v1 && gameMode1v2 && gameMode1v3) {
    gameMode1v1.classList.remove('active');
    gameMode1v2.classList.add('active');
    gameMode1v3.classList.remove('active');
  }

  // Call the setGameMode function to properly register the mode
  if (typeof setGameMode === 'function') {
    setGameMode('1v2');
  }

  // Switch to 2-bot selection mode
  if (window.selectedBots.length > 2) {
    // If more than 2 bots selected, keep only the first 2
    window.selectedBots = window.selectedBots.slice(0, 2);
  } else if (window.selectedBots.length === 1) {
    // If only 1 bot selected, add one more random bot
    const allBots = Array.from(document.querySelectorAll('.bot-select-btn')).map(btn => btn.getAttribute('data-bot'));
    const availableBots = allBots.filter(bot => !window.selectedBots.includes(bot));
    if (availableBots.length > 0) {
      const randomBot = availableBots[Math.floor(Math.random() * availableBots.length)];
      window.selectedBots.push(randomBot);
    }
  } else if (window.selectedBots.length === 0) {
    // If no bots selected, select 2 random bots
    const allBots = Array.from(document.querySelectorAll('.bot-select-btn')).map(btn => btn.getAttribute('data-bot'));
    if (allBots.length >= 2) {
      const shuffled = allBots.sort(() => 0.5 - Math.random());
      window.selectedBots = shuffled.slice(0, 2);
    }
  }

  // Re-render to update visual state
  renderBotSelectRow();
}

function handle1v3Mode() {
  console.log('🎯 1v3 mode button clicked!');

  // Set the button to active state
  const gameMode1v1 = document.getElementById('gameMode1v1');
  const gameMode1v3 = document.getElementById('gameMode1v3');

  if (gameMode1v1 && gameMode1v3) {
    gameMode1v1.classList.remove('active');
    gameMode1v3.classList.add('active');
    console.log('🎯 1v3 button set to active state');
  }

  // Call the setGameMode function to properly register the mode
  if (typeof setGameMode === 'function') {
    setGameMode('1v3');
  }

  // Clear all selections when switching to 1v3 mode
  window.selectedBots = [];
  renderBotSelectRow();
}

document.addEventListener('DOMContentLoaded', () => {
  console.log('🎯 Custom bots: DOMContentLoaded - initializing bot selection');
  renderBotSelectRow();
  initializeGameModeButtons();

  // Initialize the opponent display
  updateOpponentDisplay();

  console.log('🎯 Bot selection and opponent display initialized');
});

// Update opponent display based on selected bots
function updateOpponentDisplay() {
    const opponentDisplay = document.getElementById('opponentDisplay');
    if (!opponentDisplay) return;

    // Use the value from the playerName input, fallback to 'You'
    const playerNameInput = document.getElementById('playerName');
    const playerName = playerNameInput && playerNameInput.value.trim() ? playerNameInput.value.trim() : 'You';

    if (window.selectedBots.length === 0) {
        opponentDisplay.textContent = `Select 1-3 AI opponents to start a game`;
    } else {
        const botNames = window.selectedBots.map(botId => {
            // Get bot name from loaded bot data
            const bot = window.loadedBotData?.placeholder_bots?.find(b => b.id === botId) ||
                       window.loadedBotData?.custom_bots?.find(b => b.id === botId);
            return bot
              ? bot.name
              : botId
                  .replace('custom_', '')
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, c => c.toUpperCase());
        });

        let displayText;
        if (botNames.length === 1) {
            displayText = `${playerName} vs ${botNames[0]}`;
        } else if (botNames.length === 2) {
            displayText = `${playerName} vs ${botNames[0]} & ${botNames[1]}`;
        } else if (botNames.length === 3) {
            displayText = `${playerName} vs ${botNames[0]}, ${botNames[1]} & ${botNames[2]}`;
        } else {
            displayText = `${playerName} vs ${botNames.length} AI opponents`;
        }

        opponentDisplay.textContent = displayText;
    }

    console.log('🎯 Updated opponent display:', opponentDisplay.textContent);
}
