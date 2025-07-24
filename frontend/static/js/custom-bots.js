function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// ===== CUSTOM BOT MODAL FUNCTIONALITY =====

let customBotCount = 1;
let placeholderData = null;




// Fallback initialization function
function initializeCustomBots() {
    console.log('🔧 Custom bots.js: initializeCustomBots() called');

    const createCustomBotBtn = document.getElementById('createCustomBotBtn');
    const customBotModal = document.getElementById('customBotModal');
    const closeCustomBotBtn = document.getElementById('cancelCustomBotBtn');
    // const saveCustomBotBtn = document.getElementById('saveCustomBotBtn');
    // const gameModeSelect = document.getElementById('gameMode');

    console.log('🔧 Custom bots.js: Elements found:', {
        createCustomBotBtn: !!createCustomBotBtn,
        customBotModal: !!customBotModal,
        // gameModeSelect: !!gameModeSelect
    });

    // Show single bot modal when Create Custom Bot button is clicked
    if (createCustomBotBtn) {
        console.log('🔧 Custom bots.js: Adding click listener to createCustomBotBtn');
        createCustomBotBtn.addEventListener('click', function() {
            console.log('🔧 Custom bots.js: Create Custom Bot button clicked!');
                if (customBotModal) {
                    console.log('🔧 Custom bots.js: Showing single bot modal');
                    customBotModal.style.display = 'block';
                    // Populate single bot modal with random placeholder
                    populateSingleBotForm();
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

    // Debug: Print when Save Bot button is clicked
    const saveCustomBotBtn = document.getElementById('saveCustomBotBtn');
    if (saveCustomBotBtn) {
      saveCustomBotBtn.addEventListener('click', function(e) {
        console.log('Save Bot button clicked');
        // Call the form submit handler directly
        handleCreateBotFormSubmit(e);
      });
    }


    // Initialize holes buttons
    initializeHolesButtons();
}

// Initialize custom bot modal functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Custom bots.js: DOMContentLoaded event fired');
    // Initialize directly since we're loading from Supabase now
        initializeCustomBots();
});

// Fallback: If DOMContentLoaded already fired, initialize immediately
if (document.readyState === 'loading') {
    console.log('🔧 Custom bots.js: DOM still loading, waiting for DOMContentLoaded');
} else {
    console.log('🔧 Custom bots.js: DOM already loaded, initializing immediately');
            initializeCustomBots();
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

    // Load bots directly from Supabase (no backend needed)
  try {
    console.log('🔍 Attempting to load bots directly from Supabase...');

    // Check if Supabase client is available
    if (!supabase) {
      console.error('❌ Supabase client not initialized');
      return;
    }

    // Use the Supabase client we set up earlier
    const { data, error } = await supabase
      .from('custom_bots')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      console.error('❌ Supabase error:', error);
    } else {
      console.log(`📊 Found ${data.length} bots from Supabase:`, data);

      // Store all fields for each bot
      data.forEach(bot => {
          allBots.push(bot); // Keep the full bot object
      });
      window.allBotsData = allBots;

      // Randomize the order of bots for display
      const shuffledBots = [...allBots].sort(() => Math.random() - 0.5);
      allBots.length = 0; // Clear the array
      allBots.push(...shuffledBots); // Add back in random order
    }
  } catch (error) {
    console.log('Could not load bots from Supabase:', error);
  }

  // If no bots found, show a message
  if (allBots.length === 0) {
    row.innerHTML = '<p style="text-align: center; color: #666; font-style: italic;">No bots found. Create some custom bots to get started!</p>';
    return;
  }

  // Initialize selectedBots if not already set
  if (!window.selectedBots) {
    window.selectedBots = [];
  }

  // When initializing or updating selectedBots, always map ids to full objects
  if (window.selectedBots.length > 0) {
    const availableBotIds = allBots.map(bot => bot.ai_bot_id || bot.id);
    window.selectedBots = window.selectedBots
      .map(sel => typeof sel === 'object' ? sel : allBots.find(bot => (bot.ai_bot_id || bot.id) === sel))
      .filter(bot => bot && availableBotIds.includes(bot.ai_bot_id || bot.id));
    if (window.selectedBots.length === 0) {
      // Pick a random bot if none of the previous selection is available
      const randomIdx = Math.floor(Math.random() * allBots.length);
      window.selectedBots = [allBots[randomIdx]];
    }
} else {
    // Pick a random bot for initial selection
    const randomIdx = Math.floor(Math.random() * allBots.length);
    window.selectedBots = [allBots[randomIdx]];
}


  // Render all bots
  row.innerHTML = '';
  allBots.forEach((bot, idx) => {
    const btn = document.createElement('button');
    btn.type = 'button';

    // Determine if this bot is selected
    const isSelected = window.selectedBots.some(sel => sel && (sel.ai_bot_id || sel.id) === (bot.ai_bot_id || bot.id));

    // console.log(`�� Bot ${bot.name} (${bot.value}): selected=${isSelected}`);

    btn.className = 'bot-select-btn' + (isSelected ? ' multi-selected' : '');
    btn.setAttribute('data-bot', bot.ai_bot_id || bot.id);

    // Only use name, difficulty, description for display
    btn.innerHTML = `
      <div class="bot-header">
        <span class="bot-name">${bot.name}</span>
        <span class="bot-difficulty ${bot.difficulty}">${bot.difficulty.charAt(0).toUpperCase() + bot.difficulty.slice(1)}</span>
      </div>
      <span class="bot-desc bot-desc-short">${bot.description || 'Custom bot with unique personality.'}</span>
    `;
    btn.onclick = () => selectBotButton(bot.ai_bot_id || bot.id);
    row.appendChild(btn);
  });

  // Set initial selected bot value for backward compatibility
  window.selectedBotValue = window.selectedBots[0];
  // console.log(`✅ Rendered ${allBots.length} bots total from Supabase`);

  // Update the opponent display to show the initially selected bot
  updateOpponentDisplay();

  // Scroll the selected bot into view
  const selectedBtn = Array.from(row.children).find(btn => btn.classList.contains('selected') || btn.classList.contains('multi-selected'));
  if (selectedBtn) {
    selectedBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  // Show selected bot images and descriptions
  updateAIBotImageContainer(allBots);

  // Update start game button state
  updateStartGameButtonState();
}

// Function to update start game button state based on bot selection
function updateStartGameButtonState() {
  const startGameBtn = document.querySelector('button[onclick="startGame()"]');
  if (!startGameBtn) return;

  const hasSelectedBots = window.selectedBots && window.selectedBots.length > 0;

  if (hasSelectedBots) {
    // Enable the button
    startGameBtn.disabled = false;
    startGameBtn.style.opacity = '1';
    startGameBtn.style.cursor = 'pointer';
    startGameBtn.title = 'Start the game with selected AI opponents';
  } else {
    // Disable the button
    startGameBtn.disabled = true;
    startGameBtn.style.opacity = '0.5';
    startGameBtn.style.cursor = 'not-allowed';
    startGameBtn.title = 'Please select at least 1 AI opponent to start a game';
  }
}

function updateAIBotImageContainer(allBots) {
  const imageContainer = document.getElementById('aiBotImageContainer');
  if (!imageContainer) return;
  imageContainer.innerHTML = '';

  if (!window.selectedBots || window.selectedBots.length === 0) {
    imageContainer.innerHTML = '<div style="color:#888; font-style:italic; margin-top:24px;"></div>';
    return;
  }

  window.selectedBots.forEach(selectedBot => {
    const botObj = allBots.find(b => (b.ai_bot_id || b.id) === (selectedBot.ai_bot_id || selectedBot.id));
    if (!botObj) return;
    // Try to match bot name to image filename
    const imgName = botObj.name.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.png';
    const imgPath = `/static/AI_bot_images/${imgName}`;

    // Create a row container for image + text
    const rowDiv = document.createElement('div');
    rowDiv.className = 'ai-bot-row';

    const img = document.createElement('img');
    img.src = imgPath;
    img.alt = botObj.name;
    img.className = 'ai-bot-img';
    img.onerror = function() {
      this.style.display = 'none';
    };

    // Text container
    const textDiv = document.createElement('div');
    textDiv.className = 'ai-bot-info';

    // Name + difficulty row
    const nameRow = document.createElement('div');
    nameRow.style.display = 'flex';
    nameRow.style.alignItems = 'center';
    nameRow.style.marginBottom = '4px';

    const name = document.createElement('div');
    name.className = 'ai-bot-name';
    name.innerText = botObj.name;
    name.style.marginBottom = '0';
    name.style.marginRight = '8px';

    // Difficulty badge
    const diff = document.createElement('span');
    diff.className = `bot-difficulty ${botObj.difficulty}`;
    diff.innerText = botObj.difficulty.charAt(0).toUpperCase() + botObj.difficulty.slice(1);

    nameRow.appendChild(name);
    nameRow.appendChild(diff);

    const desc = document.createElement('div');
    desc.className = 'ai-bot-desc';
    desc.innerText = botObj.description || 'No description available.';

    textDiv.appendChild(nameRow);
    textDiv.appendChild(desc);
    rowDiv.appendChild(img);
    rowDiv.appendChild(textDiv);
    imageContainer.appendChild(rowDiv);
  });
}



// In selectBotButton, support multi-select (up to 3 bots) with full objects
function selectBotButton(botValue) {
    if (!window.allBotsData) return;
    const botObj = window.allBotsData.find(bot => (bot.ai_bot_id || bot.id) === botValue);
    if (!botObj) return;
    const maxBots = 3;
    // Check if already selected
    const index = window.selectedBots.findIndex(sel => (sel.ai_bot_id || sel.id) === (botObj.ai_bot_id || botObj.id));
    if (index > -1) {
        // Remove if already selected
        window.selectedBots.splice(index, 1);
    } else {
        // Add if not selected (up to max limit)
        if (window.selectedBots.length < maxBots) {
            window.selectedBots.push(botObj);
        } else {
            // If at max, replace the first bot with the new selection
            window.selectedBots.shift();
            window.selectedBots.push(botObj);
        }
    }
    renderBotSelectRow();
    updateStartGameButtonState();
    updateAIBotImageContainer(window.allBotsData);
}

// Listen for game mode changes to update selection behavior. todo might delete because buttons aren't used anymore.
// function initializeGameModeButtons() {
//   const gameMode1v1 = document.getElementById('gameMode1v1');
//   const gameMode1v2 = document.getElementById('gameMode1v2');
//   const gameMode1v3 = document.getElementById('gameMode1v3');



//   if (gameMode1v1 && gameMode1v2 && gameMode1v3) {
//     // Remove any existing listeners to prevent conflicts
//     gameMode1v1.removeEventListener('click', handle1v1Mode);
//     gameMode1v2.removeEventListener('click', handle1v2Mode);
//     gameMode1v3.removeEventListener('click', handle1v3Mode);

//     // Add new listeners
//     gameMode1v1.addEventListener('click', handle1v1Mode);
//     gameMode1v2.addEventListener('click', handle1v2Mode);
//     gameMode1v3.addEventListener('click', handle1v3Mode);

//     // Test if buttons are clickable
//     gameMode1v1.style.pointerEvents = 'auto';
//     gameMode1v2.style.pointerEvents = 'auto';
//     gameMode1v3.style.pointerEvents = 'auto';

//   }
// }

function handle1v1Mode() {

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

    if (!window.selectedBots || window.selectedBots.length === 0) {
        opponentDisplay.textContent = `Select 1-3 AI opponents to start a game`;
    } else {
        const botNames = window.selectedBots.map(selectedBot => {
            // Look up the bot name from the stored bot data
            if (window.allBotsData) {
                const botObj = window.allBotsData.find(b => (b.ai_bot_id || b.id) === (selectedBot.ai_bot_id || selectedBot.id));
                if (botObj) {
                    return botObj.name;
                }
            }
            // Fallback if bot not found
            return 'Unknown Bot';
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
}

// Supabase client setup (using CDN)
// Your actual Supabase credentials
const supabaseUrl = 'https://itnacachbrkpyfgmsziq.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml0bmFjYWNoYnJrcHlmZ21zemlxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NjgxMTQ0MywiZXhwIjoyMDYyMzg3NDQzfQ.anx2ToTI7f3LV1vw7scNki_FToqJnntryriOMTQcMos';

// Initialize Supabase client when the script loads
let supabase;
if (typeof window.supabase !== 'undefined') {
  supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
  console.log('✅ Supabase client initialized successfully');
} else {
  console.error('❌ Supabase client not available - CDN may not have loaded');
}

async function fetchBotsFromSupabase() {
  const { data, error } = await supabase
    .from('custom_bots')
    .select('*')
    .order('created_at', { ascending: false });
  if (error) {
    console.error('Error fetching bots:', error);
    return [];
  }
  return data;
}

// Make function globally available
window.fetchBotsFromSupabase = fetchBotsFromSupabase;



//from create custom ai bot form
function handleCreateBotFormSubmit(event) {
  console.log('handleCreateBotFormSubmit called');
  event.preventDefault();
  const name = document.getElementById('customBotName').value.trim();
  const description = document.getElementById('customBotDescription').value.trim();
  const difficulty = document.getElementById('customBotDifficulty').value;
  console.log('all d data', name, description, difficulty);

  // Generate ai_bot_id
  const ai_bot_id = uuidv4();

  // Send to backend
  fetch('/api/create_custom_bot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ai_bot_id, name, description, difficulty })
  })

  .then(res => res.json())
  .then(data => {
    if (data.success) {
      alert('Bot created!');
      // Close modal and clear form
      const customBotModal = document.getElementById('customBotModal');
      if (customBotModal) customBotModal.style.display = 'none';
      document.getElementById('customBotName').value = '';
      document.getElementById('customBotDifficulty').value = 'easy';
      document.getElementById('customBotDescription').value = '';
      // Refresh the bot list so the new bot appears
      if (typeof renderBotSelectRow === 'function') {
        renderBotSelectRow();
      }
    } else {
      alert('Error: ' + data.error);
    }
  });
}
// TODO: refresh the page to see the new bot  (from supabase)

// TODO: when clicking
