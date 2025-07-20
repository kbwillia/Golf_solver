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

    // Populate opponent dropdown with bots from JSON
    populateOpponentDropdown();

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

            // Update opponent dropdown with new custom bot as default
            updateOpponentDropdown(data.bots[0]);
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

            // Update opponent dropdown with the first custom bot as default
            if (data.bots && data.bots.length > 0) {
                updateOpponentDropdown(data.bots[0]);
            }
        } else {
            alert('Error saving custom bots: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error saving custom bots:', error);
        alert('Error saving custom bots. Please try again.');
    });
}

function updateOpponentDropdown(savedBot) {
    const opponentSelect = document.getElementById('botNameSelect');
    if (!opponentSelect) return;

    // Create the custom bot option
    const customOption = document.createElement('option');
    customOption.value = savedBot.id; // Use the bot_id as the value
    customOption.textContent = `${savedBot.name} (${savedBot.difficulty.charAt(0).toUpperCase() + savedBot.difficulty.slice(1)})`; // Format: "Karen (Easy)"
    customOption.selected = true; // Make it the default selection

    // Add the new custom bot option to the dropdown
    opponentSelect.appendChild(customOption);

    // Trigger change event to update any dependent UI
    const changeEvent = new Event('change', { bubbles: true });
    opponentSelect.dispatchEvent(changeEvent);

    console.log(`✅ Added custom bot "${savedBot.name}" to opponent dropdown as default selection`);
}

// Load existing custom bots when page loads
function loadExistingCustomBots() {
    fetch('/get_custom_bots', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.bots) {
            const opponentSelect = document.getElementById('botNameSelect');
            if (!opponentSelect) return;

            // Add each existing custom bot to the dropdown
            data.bots.forEach(bot => {
                const customOption = document.createElement('option');
                customOption.value = bot.id;
                customOption.textContent = `${bot.name} (${bot.difficulty.charAt(0).toUpperCase() + bot.difficulty.slice(1)})`;
                opponentSelect.appendChild(customOption);
            });

            console.log(`✅ Loaded ${data.bots.length} existing custom bots into opponent dropdown`);
        }
    })
    .catch(error => {
        console.log('No existing custom bots to load or error loading them:', error);
    });
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

// Function to populate the opponent dropdown with bots from JSON
async function populateOpponentDropdown() {
    try {
        const response = await fetch('/static/custom_bot.json');
        const data = await response.json();

        if (!data.placeholder_bots || data.placeholder_bots.length === 0) {
            console.log('🎯 No bots found in JSON for dropdown population');
            return;
        }

        const botNameSelect = document.getElementById('botNameSelect');
        if (!botNameSelect) {
            console.log('🎯 Bot name select dropdown not found');
            return;
        }

        // Clear existing options (keep the first few default ones if they exist)
        const existingOptions = Array.from(botNameSelect.options);
        const defaultOptions = existingOptions.filter(option =>
            ['peter_parker', 'happy_gilmore', 'tiger_woods'].includes(option.value)
        );

        botNameSelect.innerHTML = '';

        // Add default options first
        defaultOptions.forEach(option => {
            botNameSelect.appendChild(option);
        });

        // Add custom bots from JSON
        data.placeholder_bots.forEach(bot => {
            const option = document.createElement('option');
            option.value = 'custom_' + bot.name.toLowerCase().replace(' ', '_').replace('-', '_');
            option.textContent = `${bot.name} (${bot.difficulty.charAt(0).toUpperCase() + bot.difficulty.slice(1)})`;
            botNameSelect.appendChild(option);
        });

        // Randomly select one of the custom bots as default
        if (data.placeholder_bots.length > 0) {
            const randomIndex = Math.floor(Math.random() * data.placeholder_bots.length);
            const randomBot = data.placeholder_bots[randomIndex];
            const randomBotValue = 'custom_' + randomBot.name.toLowerCase().replace(' ', '_').replace('-', '_');

            // Find and select the random bot option
            const randomOption = botNameSelect.querySelector(`option[value="${randomBotValue}"]`);
            if (randomOption) {
                randomOption.selected = true;
                console.log(`🎯 Randomly selected ${randomBot.name} as default opponent`);
            }
        }

        console.log(`🎯 Populated dropdown with ${data.placeholder_bots.length} custom bots from JSON`);
    } catch (error) {
        console.log('🎯 Error populating opponent dropdown:', error);
    }
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
  if (!row) return;

  // Only load bots from custom_bot.json
  let allBots = [];

  try {
    // Load custom bots from JSON
    const response = await fetch('/static/custom_bot.json');
    const data = await response.json();

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
  } catch (error) {
    console.log('Could not load custom bots from JSON:', error);
  }

  // Load existing custom bots from server
  try {
    const serverResponse = await fetch('/get_custom_bots');
    const serverData = await serverResponse.json();

    if (serverData.success && serverData.bots) {
      serverData.bots.forEach(bot => {
        allBots.push({
          value: bot.id,
          name: bot.name,
          difficulty: bot.difficulty.charAt(0).toUpperCase() + bot.difficulty.slice(1),
          difficultyClass: bot.difficulty,
          desc: bot.description || 'Custom bot with unique personality.'
        });
      });
    }
  } catch (error) {
    console.log('Could not load existing custom bots:', error);
  }

  // Add special announcer bots - but don't include them in selectable bots
  // allBots = [...announcerBots, ...allBots];

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
      window.selectedBots = [allBots[0].value]; // Select first available bot
    }
  } else {
    window.selectedBots = [allBots[0].value]; // Select first available bot
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
    btn.innerHTML = `
      <div class="bot-header">
        <span class="bot-name">${bot.name}</span>
        <span class="bot-difficulty ${bot.difficultyClass}">${bot.difficulty}</span>
      </div>
      <span class="bot-desc">${bot.desc}</span>
    `;
    btn.onclick = () => selectBotButton(bot.value);
    row.appendChild(btn);
  });

  // Set initial selected bot value for backward compatibility
  window.selectedBotValue = window.selectedBots[0];
  console.log(`✅ Rendered ${allBots.length} bots from custom_bot.json`);
}

function isMultiSelectionMode() {
  // Check if we're in 1v3 mode
  const gameMode1v3 = document.getElementById('gameMode1v3');
  return gameMode1v3 && gameMode1v3.classList.contains('active');
}

function selectBotButton(botValue) {
  const row = document.getElementById('botSelectRow');
  if (!row) return;

  const isMultiMode = isMultiSelectionMode();

  if (isMultiMode) {
    // Multi-selection mode (1v3)
    const index = window.selectedBots.indexOf(botValue);
    if (index > -1) {
      // Remove if already selected (but keep at least 1)
      if (window.selectedBots.length > 1) {
        window.selectedBots.splice(index, 1);
      }
    } else {
      // Add if not selected (but limit to 3)
      if (window.selectedBots.length < 3) {
        window.selectedBots.push(botValue);
      }
    }
  } else {
    // Single selection mode (1v1) - allow deselection by clicking again
    const index = window.selectedBots.indexOf(botValue);
    if (index > -1 && window.selectedBots.length > 1) {
      // If already selected and there are other bots, deselect it
      window.selectedBots.splice(index, 1);
    } else if (index === -1) {
      // If not selected, select it
      window.selectedBots = [botValue];
    }
    // If it's the only selected bot, keep it selected (no deselection)
  }

  // Update visual state
  Array.from(row.children).forEach(btn => {
    const btnValue = btn.getAttribute('data-bot');
    const isSelected = window.selectedBots.includes(btnValue);

    btn.classList.remove('selected', 'multi-selected');
    if (isSelected) {
      btn.classList.add(isMultiMode ? 'multi-selected' : 'selected');
    }
  });

  // Update backward compatibility
  window.selectedBotValue = window.selectedBots[0];

  console.log(`Selected bots: ${window.selectedBots.join(', ')}`);
}

// Listen for game mode changes to update selection behavior
function initializeGameModeButtons() {
  const gameMode1v1 = document.getElementById('gameMode1v1');
  const gameMode1v3 = document.getElementById('gameMode1v3');

  console.log('🎯 Initializing game mode buttons:', {
    '1v1 found': !!gameMode1v1,
    '1v3 found': !!gameMode1v3,
    '1v1 onclick': gameMode1v1 ? gameMode1v1.onclick : 'none',
    '1v3 onclick': gameMode1v3 ? gameMode1v3.onclick : 'none'
  });

  if (gameMode1v1 && gameMode1v3) {
    // Remove any existing listeners to prevent conflicts
    gameMode1v1.removeEventListener('click', handle1v1Mode);
    gameMode1v3.removeEventListener('click', handle1v3Mode);

    // Add new listeners
    gameMode1v1.addEventListener('click', handle1v1Mode);
    gameMode1v3.addEventListener('click', handle1v3Mode);

    // Test if buttons are clickable
    gameMode1v1.style.pointerEvents = 'auto';
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

  // Switch to multi-selection mode
  if (window.selectedBots.length === 1) {
    // Get available bots from the rendered buttons
    const row = document.getElementById('botSelectRow');
    if (row) {
      const availableBots = Array.from(row.children).map(btn => btn.getAttribute('data-bot'));
      const currentBot = window.selectedBots[0];
      const otherBots = availableBots.filter(bot => bot !== currentBot);

      // Add up to 2 more bots
      for (let i = 0; i < Math.min(2, otherBots.length); i++) {
        if (!window.selectedBots.includes(otherBots[i])) {
          window.selectedBots.push(otherBots[i]);
        }
      }
      renderBotSelectRow();
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  console.log('🎯 Custom bots: DOMContentLoaded - initializing bot selection');
  renderBotSelectRow();
  initializeGameModeButtons();

  // Debug: Check if game mode buttons exist
  const gameMode1v1 = document.getElementById('gameMode1v1');
  const gameMode1v3 = document.getElementById('gameMode1v3');
  console.log('🎯 Game mode buttons found:', {
    '1v1': !!gameMode1v1,
    '1v3': !!gameMode1v3,
    '1v1 classes': gameMode1v1 ? gameMode1v1.className : 'not found',
    '1v3 classes': gameMode1v3 ? gameMode1v3.className : 'not found'
  });
});
