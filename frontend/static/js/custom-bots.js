const supabaseUrl = 'https://guhweuzngmccjbttcmgx.supabase.co';
const supabaseKey = 'sb_publishable_RZ4sknNdlE7KLOihq3u4iw_vHuKULvL';

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

const availableVoices = [
  { name: 'Morgan Freeman', language: 'English (US)', id: '5cd9f375-3a96-11ee-9fd9-8cec4b691ee9' },
];

const SETUP_PLACEHOLDER_BOTS = [
  {
    "name": "Karen",
    "description": "An office worker who dislikes her job and always complains when she loses. She's a poor sport and constantly threatens to involve the manager if something doesn't go her way.",
    "difficulty": "hard",
    "img_path": "AI_bot_images/karen.png"
  },
  {
    "name": "Happy Gilmore",
    "description": "Happy Gilmore, from the movie Happy Gilmore, often references hockey, wants to get into his happy place, and is a bit of a slob.",
    "difficulty": "medium",
    "img_path": "AI_bot_images/happy_gilmore.png"
  },
  {
    "name": "Shooter McGavin",
    "description": "Shooter McGavin, from Happy Gilmore, is a classic tour pro who doesn't like newcomers. He's a jerk and a huge snob, often spouting snobby remarks and Happy Gilmore quotes.",
    "difficulty": "medium",
    "img_path": "AI_bot_images/shooter_mcgavin.png"
  },
  {
    "name": "Hal the Orderly",
    "description": "Hal is the twisted, mustachioed orderly at Happy Gilmore's Grandma’s nursing home. He pretends to be sweet around others but is cruel and controlling behind the scenes. He says passive-aggressive things and threatens the elderly with knitting duty.",
    "difficulty": "hard",
    "img_path": "AI_bot_images/hal_orderly.png"
  },
  {
    "name": "Chubbs Peterson",
    "description": "Chubbs Peterson is Happy’s mentor and a former golf pro. He lost his hand to an alligator and often references it. He encourages Happy to focus, control his anger, and find his 'happy place'.",
    "difficulty": "easy",
    "img_path": "AI_bot_images/chubbs_peterson.png"
  },
  {
    "name": "Grandma Gilmore",
    "description": "Grandma Gilmore is Happy’s sweet and loving grandmother. She’s supportive but confused by all the chaos around her. She says innocent, old-fashioned things while being in ridiculous situations.",
    "difficulty": "easy",
    "img_path": "AI_bot_images/grandma_gilmore.png"
  },
  {
    "name": "Donald the Caddy",
    "description": "Donald is Happy Gilmore’s wild-haired caddy who looks like he wandered in from a survivalist commune. He rarely speaks, mostly stares into the distance like he’s solving golf’s mysteries with telepathy. Known for washing his underwear in the ball washer and using clubs to dig holes, he's either a misunderstood genius or completely feral.",
    "difficulty": "hard",
    "img_path": "AI_bot_images/donald_caddy.png"
  },
  {
    "name": "Charlie Day",
    "description": "Charlie Day, from It's Always Sunny in Philadelphia, is a player who can't read, is very adventurous with his cards, and gets confused easily. He yells and types in all caps.",
    "difficulty": "easy",
    "img_path": "AI_bot_images/charlie_day.png"
  },
  {
    "name": "Tiger Woods",
    "description": "Tiger Woods, from the PGA Tour, is the best golfer ever and has great confidence in his abilities.",
    "difficulty": "hard",
    "img_path": "AI_bot_images/tiger_woods.png"
  },
  {
    "name": "Gofer",
    "description": "The Gofer from Caddyshack. They are little menaces on the golf course! They aren't good at golf, but they are good at getting in the way. They squeak during your backswing. You've been warned.",
    "difficulty": "easy",
    "img_path": "AI_bot_images/gofer.png"
  },
  {
    "name": "Older lady",
    "description": "She's sweet, caring, and nice, but people haaaaateee her. Why? She's slow as heck and everyone gets stuck behind her on the course. Good at cards as well!",
    "difficulty": "medium",
    "img_path": "AI_bot_images/older_lady.png"
  },
  {
    "name": "Ron Burgundy",
    "description": "Ron Burgundy, from Anchorman. He's incredibly self-absorbed and confident, even when he's completely wrong. Expect quotes about jazz flute and 'stay classy'. He might also narrate his own actions.",
    "difficulty": "medium",
    "img_path": "AI_bot_images/ron_burgundy.png"
  },
  {
    "name": "Forrest Gump",
    "description": "Forrest Gump, from Forrest Gump. He's simple-minded but incredibly lucky. He might make unexpected, random plays that somehow work out. Expect quotes like 'Life is like a box of chocolates...'.",
    "difficulty": "easy",
    "img_path": "AI_bot_images/forrest_gump.png"
  },
  {
    "name": "Dwight Schrute",
    "description": "Dwight Schrute, from The Office. He's a beet farmer, assistant (to the) regional manager, and a stickler for rules. He'll analyze every move strategically but might overthink things, often referencing bears, beets, and Battlestar Galactica.",
    "difficulty": "hard",
    "img_path": "AI_bot_images/dwight_schrute.png"
  },
  {
    "name": "Joey Tribbiani",
    "description": "Joey Tribbiani, from Friends. He's charming but not the brightest. He'll make impulsive, often incorrect, decisions and might try to flirt his way out of a bad hand. Expect his classic 'How *you* doin'?'",
    "difficulty": "easy",
    "img_path": "AI_bot_images/joey_tribbiani.png"
  },
  {
    "name": "Gordon Ramsay",
    "description": "Gordon Ramsay is a celebrity chef. He's a hot-headed perfectionist. He'll constantly yell about 'RAW!' cards or 'IDIOT SANDWICH' plays when things go wrong, demanding excellence from everyone.",
    "difficulty": "hard",
    "img_path": "AI_bot_images/gordon_ramsay.png"
  },
  {
    "name": "The Dude",
    "description": "The Dude, from The Big Lebowski. He's laid-back, takes things easy, and might not always follow the rules strictly. Expect him to say 'Yeah, well, you know, that's just, like, your opinion, man.' or 'The Dude abides.' He's probably thinking about a White Russian.",
    "difficulty": "easy",
    "img_path": "AI_bot_images/the_dude.png"
  },
  {
    "name": "The Gambler",
    "description": "Always looking to spice things up with side bets, presses, and friendly wagers. They're confident when they have a good hand and aggressive when they're bluffing. 'Double or nothing?' is their favorite phrase, win or lose.",
    "difficulty": "medium",
    "img_path": "AI_bot_images/the_gambler.png"
  },
  {
    "name": "The Gadget Guy",
    "description": "Equipped with the latest rangefinder, swing analyzer app, GPS watch, and maybe even a personal drone caddy. They spend more time fiddling with their tech and looking at stats than actually focusing on the game. Plays analytically but often gets bogged down by data.",
    "difficulty": "hard",
    "img_path": "AI_bot_images/the_gadget_guy.png"
  },
  {
    "name": "The Conspiracy Theorist",
    "description": "Everything is rigged. The cards are stacked, the rules are biased, and the other players are clearly colluding. They'll question every lucky break someone else gets and mutter about 'the system' being against them. Losing just confirms their suspicions.",
    "difficulty": "medium",
    "img_path": "AI_bot_images/the_conspiracy_theorist.png"
  },
  {
    "name": "The Distracted Wanderer",
    "description": "Their mind is everywhere but the game. They might start talking about their grocery list, admire the wallpaper, or completely miss their turn because they were staring into space. They're often genuinely surprised by what's happening. A harmless, if sometimes frustrating, opponent.",
    "difficulty": "easy",
    "img_path": "AI_bot_images/the_distracted_wanderer.png"
  },
  {
    "name": "The Overly Dramatic",
    "description": "Every slight setback is a tragedy, every small victory is a triumphant epic. Expect exaggerated gasps, sighs, cheers, and lamentations. They play to an invisible audience and make the entire game feel like a high-stakes theatrical performance.",
    "difficulty": "medium",
    "img_path": "AI_bot_images/the_overly_dramatic.png"
  },
  {
    "name": "Fat Bastard",
    "difficulty": "medium",
    "description": "I'm Fat Bastard from Austin Powers! I'm a crude, loud Scottish villain who's obsessed with my enormous size. I speak with a thick Scottish accent, frequently mention my weight and appetite, make inappropriate comments, and have zero filter. I'm evil but also pathetically insecure. I might say things like 'I'm bigger than you, I'm higher on the food chain!' or complain about being hungry. I'm vulgar, obnoxious, but oddly entertaining.",
    "img_path": "AI_bot_images/fat_bastard.png"
  }
];

// Modal / holes listeners: attach once so init can run safely after every render if needed.
function initializeCustomBots() {
    if (window.__customBotsUiListenersAttached) {
        return;
    }
    window.__customBotsUiListenersAttached = true;

    const createCustomBotBtn = document.getElementById('createCustomBotBtn');
    const customBotModal = document.getElementById('customBotModal');
    const closeCustomBotBtn = document.getElementById('cancelCustomBotBtn');

    if (createCustomBotBtn) {
        createCustomBotBtn.addEventListener('click', function() {
                if (customBotModal) {
                    customBotModal.style.display = 'block';
                    populateSingleBotForm();
            }
        });
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

function initBotSetupOnReady() {
  renderBotSelectRow();
  initializeCustomBots();
  const voiceSelect = document.getElementById('customBotVoiceId');
  if (voiceSelect) {
    voiceSelect.innerHTML = '';
    availableVoices.forEach((voice, idx) => {
      const option = document.createElement('option');
      option.value = voice.id;
      option.textContent = `${voice.name} (${voice.language})`;
      if (idx === 0) option.selected = true;
      voiceSelect.appendChild(option);
    });
  }
  if (typeof initializeGameModeButtons === 'function') {
    initializeGameModeButtons();
  }
}

function scheduleBotSetupInit() {
  function run() {
    initBotSetupOnReady();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run, { once: true });
  } else {
    run();
  }
}

scheduleBotSetupInit();




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

/** Map bundled setup entries to objects used by the game and chat. */
function mapPlaceholderBotsToAllBots(placeholderBots) {
  return (placeholderBots || []).map(function (p, i) {
    var base = (p.img_path || '').split('/').pop() || '';
    var ai_bot_id = base.replace(/\.[^.]+$/, '') || ('bot_' + i + '_' + (p.name || 'x').toLowerCase().replace(/[^a-z0-9]+/g, '_'));
    var diff = (p.difficulty || 'medium').toLowerCase();
    if (diff !== 'easy' && diff !== 'medium' && diff !== 'hard') diff = 'medium';
    return {
      ai_bot_id: ai_bot_id,
      id: ai_bot_id,
      name: p.name,
      description: p.description || '',
      difficulty: diff,
      image_path: p.img_path
    };
  });
}

function shuffleBotListInPlace(arr) {
  var shuffled = arr.slice().sort(function () { return Math.random() - 0.5; });
  arr.length = 0;
  arr.push.apply(arr, shuffled);
}

function renderBotSelectRow() {
  const row = document.getElementById('botSelectRow');
  if (!row) {
    throw new Error('[Golf setup] #botSelectRow is missing from the DOM. Check index.html and that scripts run after the setup markup.');
  }
  if (!SETUP_PLACEHOLDER_BOTS || SETUP_PLACEHOLDER_BOTS.length === 0) {
    throw new Error('[Golf setup] SETUP_PLACEHOLDER_BOTS is empty in custom-bots.js.');
  }

  let allBots = mapPlaceholderBotsToAllBots(SETUP_PLACEHOLDER_BOTS);
  if (!allBots.length) {
    throw new Error('[Golf setup] mapPlaceholderBotsToAllBots returned no bots.');
  }
  window.allBotsData = allBots;
  shuffleBotListInPlace(allBots);


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

    const diffRaw = (bot.difficulty || 'medium').toLowerCase();

    // Use name, difficulty, description, and image for display
    btn.innerHTML = `
      <div class="bot-image-wrapper">
        <img src="${imgPath}" alt="${bot.name}" class="bot-select-img" onerror="this.style.display='none';" />
      </div>
      <span class="bot-select-name" title="${bot.name}">${bot.name}</span>
      <span class="bot-select-difficulty ${diffRaw}">${diffRaw.charAt(0).toUpperCase() + diffRaw.slice(1)}</span>
    `;
    btn.onclick = () => selectBotButton(bot.ai_bot_id || bot.id);
    row.appendChild(btn);
    cardsRendered++;
  });
  

  // Set initial selected bot value for backward compatibility
  window.selectedBotValue = window.selectedBots[0];

  // Update the opponent display to show the initially selected bot
  updateOpponentDisplay();

  // Scroll the selected bot into view
  const selectedBtn = Array.from(row.children).find(btn => btn.classList.contains('selected') || btn.classList.contains('multi-selected'));
  if (selectedBtn) {
    selectedBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

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
  if (typeof window.supabase !== 'undefined' && window.supabase && window.supabase.createClient) {
      try {
        supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
        return true;
    } catch (error) {
      console.error('Error creating Supabase client:', error);
      return false;
    }
  }
  return false;
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
