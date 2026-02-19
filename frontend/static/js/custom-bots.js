// CRITICAL TEST - If you don't see this, the script isn't loading
console.log('=== CUSTOM-BOTS.JS STARTING TO LOAD ===');
console.log('=== CUSTOM-BOTS.JS LOADED ===');
console.log('Timestamp:', new Date().toISOString());
window.customBotsLoaded = true;
console.log('File should be executing now');

// Supabase client setup (using CDN) - MOVED TO TOP
// Updated Supabase credentials - must match .env file
const supabaseUrl = 'https://guhweuzngmccjbttcmgx.supabase.co';
const supabaseKey = 'sb_publishable_RZ4sknNdlE7KLOihq3u4iw_vHuKULvL';

// Wrap in try-catch to catch any immediate errors
try {
  console.log('📦 custom-bots.js script loaded at', new Date().toISOString());
} catch (e) {
  console.error('Error in custom-bots.js initial log:', e);
  throw e; // Re-throw to see the error
}

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// ===== CUSTOM BOT MODAL FUNCTIONALITY =====

let customBotCount = 1;
let placeholderData = null;
let uploadedImagePath = null;


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

  // Populate voice dropdown
  const voiceSelect = document.getElementById('customBotVoiceId');
  if (voiceSelect) {
    voiceSelect.innerHTML = ""; // Clear any existing options
    availableVoices.forEach((voice, idx) => {
      const option = document.createElement('option');
      option.value = voice.id;
      option.textContent = `${voice.name} (${voice.language})`;
      if (idx === 0) option.selected = true; // Default to first voice
      voiceSelect.appendChild(option);
    });
  }
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
  console.log('🎨 renderBotSelectRow() called');
  const row = document.getElementById('botSelectRow');
  const imageContainer = document.getElementById('aiBotImageContainer');
  console.log('🎨 botSelectRow element:', row ? 'found' : 'NOT FOUND');
  console.log('🎨 aiBotImageContainer element:', imageContainer ? 'found' : 'NOT FOUND');
  if (!row) {
    console.error('❌ botSelectRow element not found in DOM!');
    return;
  }

  // Load bots from custom_bot.json
  let allBots = [];

    // Load bots directly from Supabase (no backend needed)
  try {
    console.log('🔍 Attempting to load bots directly from Supabase...');

    // Check if Supabase client is available
    if (!supabase) {
      console.error('❌ Supabase client not initialized');
      console.error('Supabase URL:', typeof supabaseUrl !== 'undefined' ? supabaseUrl : 'undefined');
      console.error('Supabase Key:', typeof supabaseKey !== 'undefined' ? supabaseKey?.substring(0, 20) + '...' : 'undefined');
      // Try to initialize Supabase if not already done
      if (typeof window.supabase !== 'undefined' && typeof supabaseUrl !== 'undefined' && typeof supabaseKey !== 'undefined') {
        console.log('Attempting to initialize Supabase client...');
        supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
        console.log('Supabase client initialized:', !!supabase);
      } else {
        return;
      }
    }

    // Use the Supabase client we set up earlier
    // Try custom_bots_view first (the actual table), fall back to custom_bots
    console.log('🗄️ CALLING DATABASE FOR CUSTOM BOTS...');
    console.log('🗄️ Querying custom_bots_view table from Supabase...');
    let { data, error } = await supabase
      .from('custom_bots_view')
      .select('*')
      .order('created_at', { ascending: false });
    console.log('🗄️ Database query completed. Data:', data ? `${data.length} records` : 'null', 'Error:', error ? 'Yes' : 'No');
    
    // If view doesn't work, try the base table
    if (error && error.message && error.message.includes('could not find the table')) {
      console.log('Trying custom_bots table instead...');
      const result = await supabase
        .from('custom_bots')
        .select('*')
        .order('created_at', { ascending: false });
      data = result.data;
      error = result.error;
    }

    if (error) {
      console.error('❌ Supabase error:', error);
      console.error('Error details:', JSON.stringify(error, null, 2));
    } else {
      console.log(`📊 Found ${data.length} bots from Supabase:`, data);
      // Log image paths for debugging
      data.forEach(bot => {
        const imagePath = bot.image_path || bot.image_url;
        const fallbackName = bot.name.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.png';
        console.log(`Bot "${bot.name}": image_path=${imagePath}, fallback=${fallbackName}`);
      });

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
    console.error('Could not load bots from Supabase:', error);
    // Don't return here - try to continue with empty array or fallback
  }

  // If no bots found, show a helpful message
  if (allBots.length === 0) {
    console.warn('No bots loaded from Supabase. Showing message to user.');
    row.innerHTML = '<div style="text-align: center; color: #ff6b6b; padding: 20px; background: rgba(255, 107, 107, 0.1); border-radius: 8px; margin: 10px;"><p style="font-weight: bold; margin-bottom: 8px;">No bots found</p><p style="font-style: italic; font-size: 0.9em;">Check console for errors. Make sure Supabase is connected.</p></div>';
    return;
  }
  
  console.log(`✅ Successfully loaded ${allBots.length} bots, rendering cards...`);

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
    // Allow 0 bots to be selected - don't auto-select a random bot
  } else {
    // Only pick a random bot for initial selection if this is the first time loading
    // Check if this is the initial load by seeing if selectedBots was never set before
    if (typeof window.selectedBotsInitialized === 'undefined') {
      const randomIdx = Math.floor(Math.random() * allBots.length);
      window.selectedBots = [allBots[randomIdx]];
      window.selectedBotsInitialized = true;
    }
    // If selectedBotsInitialized is true, allow 0 bots to be selected
  }


  // Render all bots
  console.log(`🎨 Rendering ${allBots.length} bot cards...`);
  row.innerHTML = '';
  let cardsRendered = 0;
  allBots.forEach((bot, idx) => {
    const btn = document.createElement('button');
    btn.type = 'button';

    // Determine if this bot is selected
    const isSelected = window.selectedBots.some(sel => sel && (sel.ai_bot_id || sel.id) === (bot.ai_bot_id || bot.id));

    // console.log(`�� Bot ${bot.name} (${bot.value}): selected=${isSelected}`);

    btn.className = 'bot-select-btn' + (isSelected ? ' multi-selected' : '');
    btn.setAttribute('data-bot', bot.ai_bot_id || bot.id);

    // Get image path for the button
    let imgPath = '';
    const imagePath = bot.image_path || bot.image_url;
    if (imagePath) {
      if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
        imgPath = imagePath;
      } else {
        imgPath = `/static/${imagePath}`;
      }
    } else {
      // Fallback to name-based mapping
      const imgName = bot.name.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.png';
      imgPath = `/static/AI_bot_images/${imgName}`;
    }
    
    // Use name, difficulty, description, and image for display
    btn.innerHTML = `
      <div class="bot-image-wrapper">
        <img src="${imgPath}" alt="${bot.name}" class="bot-select-img" onerror="this.style.display='none';" />
      </div>
      <div class="bot-header">
        <span class="bot-name">${bot.name}</span>
        <span class="bot-difficulty ${bot.difficulty}">${bot.difficulty.charAt(0).toUpperCase() + bot.difficulty.slice(1)}</span>
      </div>
      <span class="bot-desc bot-desc-short">${bot.description || 'Custom bot with unique personality.'}</span>
    `;
    btn.onclick = () => selectBotButton(bot.ai_bot_id || bot.id);
    row.appendChild(btn);
    cardsRendered++;
  });
  
  console.log(`✅ Successfully rendered ${cardsRendered} bot selection cards`);

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
  console.log(`Updating AI bot image container with ${allBots.length} bots, ${window.selectedBots.length} selected`);
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
    let imgPath = '';
    // Check both image_path and image_url fields (database uses image_url)
    const imagePath = botObj.image_path || botObj.image_url;
    if (imagePath) {
      // If it's a full URL, use it directly; otherwise treat as relative path
      if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
        imgPath = imagePath;
      } else {
        imgPath = `/static/${imagePath}`;
      }
    } else {
      // Fallback to old name-based mapping
      const imgName = botObj.name.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.png';
      imgPath = `/static/AI_bot_images/${imgName}`;
    }

    // Create a row container for image + text
    const rowDiv = document.createElement('div');
    rowDiv.className = 'ai-bot-row';
    rowDiv.style.cursor = 'pointer'; // Add pointer cursor to indicate clickable

    const img = document.createElement('img');
    img.src = imgPath;
    img.alt = botObj.name;
    img.className = 'ai-bot-img';
    let hasTriedFallback = false; // Flag to prevent infinite loops
    img.onerror = function() {
      if (hasTriedFallback) {
        // Already tried fallback, just hide the image
        console.warn(`Failed to load image for ${botObj.name} after fallback attempt. Hiding image.`);
        this.style.display = 'none';
        this.onerror = null; // Remove error handler to prevent further calls
        return;
      }
      
      console.warn(`Failed to load image for ${botObj.name}: ${imgPath}`);
      // Try fallback path only once
      hasTriedFallback = true;
      const fallbackName = botObj.name.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.png';
      const fallbackPath = `/static/AI_bot_images/${fallbackName}`;
      console.log(`Trying fallback path: ${fallbackPath}`);
      this.src = fallbackPath;
    };
    img.onload = function() {
      console.log(`Successfully loaded image for ${botObj.name}: ${imgPath}`);
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

    // Add click handler to deselect the bot in the ai-image-container
    rowDiv.onclick = function() {
      // Remove the bot from selectedBots
      const index = window.selectedBots.findIndex(sel => (sel.ai_bot_id || sel.id) === (botObj.ai_bot_id || botObj.id));
      if (index > -1) {
        window.selectedBots.splice(index, 1);
        // Update the UI
        renderBotSelectRow();
        updateStartGameButtonState();
        updateAIBotImageContainer(window.allBotsData);
      }
    };

    // Add hover effect
    rowDiv.onmouseenter = function() {
      this.style.opacity = '0.8';
      this.style.transform = 'scale(1.02)';
    };

    rowDiv.onmouseleave = function() {
      this.style.opacity = '1';
      this.style.transform = 'scale(1)';
    };

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

// Simplified initialization - no IIFE wrapper
function initBotSelection() {
  try {
    console.log('📦 custom-bots.js: DOMContentLoaded event fired');
    console.log('📦 Checking Supabase initialization...');
    console.log('📦 typeof supabase:', typeof supabase);
    console.log('📦 typeof window.supabase:', typeof window.supabase);
    
    // Wait a bit for Supabase to initialize
    setTimeout(() => {
      try {
        console.log('📦 After timeout, checking Supabase again...');
        console.log('📦 typeof supabase:', typeof supabase);
        
        if (typeof supabase !== 'undefined' && supabase) {
          console.log('✅ Supabase client ready, rendering bots...');
          renderBotSelectRow();
        } else {
          console.warn('⚠️ Supabase client not ready, checking if we can initialize...');
          // Try to initialize Supabase if window.supabase is available
          if (typeof window.supabase !== 'undefined' && typeof supabaseUrl !== 'undefined' && typeof supabaseKey !== 'undefined') {
            console.log('🔄 Attempting to initialize Supabase client...');
            supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
            console.log('✅ Supabase initialized:', !!supabase);
            renderBotSelectRow();
          } else {
            console.error('❌ Cannot initialize Supabase - missing dependencies');
            console.error('window.supabase:', typeof window.supabase);
            console.error('supabaseUrl:', typeof supabaseUrl !== 'undefined' ? supabaseUrl : 'undefined');
            console.error('supabaseKey:', typeof supabaseKey !== 'undefined' ? supabaseKey.substring(0, 20) + '...' : 'undefined');
            // Still try to render - it will show error message
            console.log('🔄 Attempting to render bots anyway...');
            renderBotSelectRow();
          }
        }
      } catch (e) {
        console.error('❌ Error in bot selection timeout:', e);
        // Still try to render
        try {
          renderBotSelectRow();
        } catch (e2) {
          console.error('❌ Error rendering bots:', e2);
        }
      }
    }, 1000); // Increased delay to 1000ms to give Supabase CDN more time
    
    initializeGameModeButtons();

    // Initialize the opponent display
    updateOpponentDisplay();

    console.log('🎯 Bot selection initialization complete');
  } catch (e) {
    console.error('❌ Error in initBotSelection:', e);
  }
}

// Set up DOMContentLoaded listener
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initBotSelection);
} else {
  // DOM already loaded
  console.log('📦 DOM already loaded, initializing immediately...');
  initBotSelection();
}

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
// Updated Supabase credentials for new project
// Initialize Supabase client - try multiple times if CDN hasn't loaded yet
// Use var (not let/const) to avoid redeclaration errors if script loads multiple times
var supabase;

function initializeSupabaseClient() {
  console.log('🔄 Attempting to initialize Supabase client...');
  console.log('window.supabase type:', typeof window.supabase);
  
  if (typeof window.supabase !== 'undefined' && window.supabase && window.supabase.createClient) {
      try {
        supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
        console.log('✅ Supabase client initialized successfully');
        return true;
    } catch (error) {
      console.error('❌ Error creating Supabase client:', error);
      return false;
    }
  } else {
    console.warn('⚠️ window.supabase not available yet - CDN may still be loading');
    return false;
  }
}

// Try to initialize immediately
if (!initializeSupabaseClient()) {
  // If it fails, try again after a delay
  setTimeout(() => {
    if (!initializeSupabaseClient()) {
      // Try one more time after another delay
      setTimeout(() => {
        initializeSupabaseClient();
      }, 1000);
    }
  }, 500);
}

async function fetchBotsFromSupabase() {
  // Try custom_bots_view first (the actual table), fall back to custom_bots
  let { data, error } = await supabase
    .from('custom_bots_view')
    .select('*')
    .order('created_at', { ascending: false });
  
  // If view doesn't work, try the base table
  if (error && error.message && error.message.includes('could not find the table')) {
    console.log('Trying custom_bots table instead...');
    const result = await supabase
      .from('custom_bots')
      .select('*')
      .order('created_at', { ascending: false });
    data = result.data;
    error = result.error;
  }
  
  if (error) {
    console.error('Error fetching bots:', error);
    return [];
  }
  return data;
}

// Make function globally available
window.fetchBotsFromSupabase = fetchBotsFromSupabase;

// TEST FUNCTION - Call this from browser console to test database connection
window.testSupabaseConnection = async function() {
  console.log('🧪 Testing Supabase connection...');
  console.log('supabaseUrl:', supabaseUrl);
  console.log('supabaseKey:', supabaseKey ? supabaseKey.substring(0, 20) + '...' : 'undefined');
  console.log('typeof window.supabase:', typeof window.supabase);
  console.log('supabase client:', supabase);
  
  if (!supabase) {
    console.error('❌ Supabase client not initialized!');
    console.log('Attempting to initialize...');
    if (typeof window.supabase !== 'undefined' && window.supabase && window.supabase.createClient) {
      try {
        supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
        console.log('✅ Supabase client created:', !!supabase);
      } catch (e) {
        console.error('❌ Failed to create client:', e);
        return;
      }
    } else {
      console.error('❌ window.supabase not available!');
      return;
    }
  }
  
  console.log('🔍 Querying custom_bots_view table...');
  try {
    const { data, error } = await supabase
      .from('custom_bots_view')
      .select('*')
      .limit(5);
    
    if (error) {
      console.error('❌ Database query error:', error);
      console.error('Error details:', JSON.stringify(error, null, 2));
    } else {
      console.log('✅ Database query successful!');
      console.log(`📊 Found ${data.length} bots:`, data);
      return data;
    }
  } catch (e) {
    console.error('❌ Exception during query:', e);
  }
};



//from create custom ai bot form
function handleCreateBotFormSubmit(event) {
  console.log('handleCreateBotFormSubmit called');
  event.preventDefault();
  const name = document.getElementById('customBotName').value.trim();
  const description = document.getElementById('customBotDescription').value.trim();
  const difficulty = document.getElementById('customBotDifficulty').value;
  const ai_bot_id = uuidv4();
  const voice_id = document.getElementById('customBotVoiceId') ? document.getElementById('customBotVoiceId').value : '5cd9f375-3a96-11ee-9fd9-8cec4b691ee9';

  // Build payload
  const payload = { ai_bot_id, name, description, difficulty };
  if (uploadedImagePath) {
    payload.image_path = uploadedImagePath;
  }
  // Always set a default if voice_id is falsy
  payload.voice_id = voice_id || "5cd9f375-3a96-11ee-9fd9-8cec4b691ee9"; //morgan freeman



  fetch('/api/create_custom_bot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
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
      if (document.getElementById('customBotVoiceId')) document.getElementById('customBotVoiceId').value = 'default';
      uploadedImagePath = null;
      // Automatically select the new bot and unselect others
      if (data.bot) {
        window.selectedBots = [data.bot];
      }
      if (typeof renderBotSelectRow === 'function') {
        renderBotSelectRow();
      }
      if (typeof updateAIBotImageContainer === 'function' && window.allBotsData) {
        updateAIBotImageContainer(window.allBotsData);
      }
    } else {
      alert('Error: ' + data.error);
    }
  });
}
// TODO: refresh the page to see the new bot  (from supabase)

// TODO: when clicking

//adding for uploading bot image
document.addEventListener('DOMContentLoaded', function() {
  // Upload button triggers file input
  const uploadBtn = document.getElementById('uploadBotImageBtn');
  const fileInput = document.getElementById('customBotImage');
  const previewImg = document.getElementById('customBotImagePreview');

  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener('click', function() {
      fileInput.click();
    });

    fileInput.addEventListener('change', async function(event) {
      const file = event.target.files[0];
      if (file) {
        // Preview
        const reader = new FileReader();
        reader.onload = function(e) {
          previewImg.src = e.target.result;
          previewImg.style.display = 'block';
        };
        reader.readAsDataURL(file);

        // Upload to backend
        const formData = new FormData();
        formData.append('image', file);
        try {
          const response = await fetch('/api/upload_bot_image', {
            method: 'POST',
            body: formData
          });
          const data = await response.json();
          if (data.success) {
            uploadedImagePath = data.image_path;
            console.log('Image uploaded, path:', uploadedImagePath);
          } else {
            uploadedImagePath = null;
            alert('Image upload failed: ' + (data.error || 'Unknown error'));
          }
        } catch (err) {
          uploadedImagePath = null;
          alert('Image upload failed: ' + err.message);
        }
      }
    });
  }
});

const availableVoices = [
  { name: "Morgan Freeman", language: "English (US)", id: "5cd9f375-3a96-11ee-9fd9-8cec4b691ee9" },
  // { name: "Firey", language: "English (US)", id: "8da96304-..." },
  // { name: "Morpheus", language: "English (US)", id: "bf924282-..." },
  // { name: "SUGA", language: "English (US)", id: "00156bfc-..." },
  // { name: "Will Smith", language: "English (US)", id: "5cb4f88b-..." },
  // { name: "Lionel Messi", language: "English (US)", id: "00157155-..." },
  // { name: "Nayeon", language: "English (US)", id: "5ccf7354-..." }
];
