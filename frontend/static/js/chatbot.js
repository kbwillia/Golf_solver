// ===== CHATBOT MODULE =====
// Contains all chatbot functionality, bot interactions, and chat UI management

// Global variables for chatbot state (some are already declared in game-core.js)
let proactiveCommentSent = false;
// let lastNantzCommentTime = 0; // REMOVED - already declared in game-core.js
// let previousActionHistoryLength = 0; // REMOVED - already declared in game-core.js
// let chatbotEnabled = true; // REMOVED - already declared in game-core.js
// let currentPersonality = 'opponent'; // REMOVED - already declared in game-core.js

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
            console.log('🎹 Keypress event detected:', e.key);
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                console.log('✅ Enter pressed, calling sendChatMessage');
                sendChatMessage();
            }
        });

        // Send message on button click
        sendBtn.addEventListener('click', function(e) {
            console.log('🖱️ Send button clicked');
            e.preventDefault();
            console.log('✅ Send button clicked, calling sendChatMessage');
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

// Send a message to the chatbot
async function sendChatMessage() {
    console.log('📤 sendChatMessage called');
    console.log('🔍 Checking elements in sendChatMessage...');

    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');

    console.log('📋 Elements in sendChatMessage:', {
        chatInput: chatInput,
        sendBtn: sendBtn,
        chatInputExists: !!chatInput,
        sendBtnExists: !!sendBtn
    });

    if (!chatInput) {
        console.error('❌ Chat input not found in sendChatMessage!');
        return;
    }

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
                if (shouldBotSendGif(botName)) {
                    // Extract relevant search terms from the message
                    const searchTerms = extractSearchTerms(message, botName);
                    const relevantGif = await getRelevantGif(searchTerms, botName);
                    addMessageToChat('bot', relevantGif, botName, true); // true = GIF only
                }
            }
        } else {
            console.error('❌ Chatbot response not successful:', data.error);
            addMessageToChat('bot', 'Sorry, I\'m having trouble responding right now.');
        }
    } catch (error) {
        console.error('❌ Error sending chat message:', error);
        addMessageToChat('bot', 'Sorry, I\'m having trouble connecting to the chat service.');
    }
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

// Export functions globally for backward compatibility
window.parseMentions = parseMentions;
window.setupAutocomplete = setupAutocomplete;
window.initializeChatbot = initializeChatbot;
window.addMessageToChat = addMessageToChat;
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

// Clear chat UI
function clearChatUI() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
        // Add the original helpful message about using @ symbols
        addMessageToChat('bot', "Hi! Chat with your opponents, or type @golfbro or @golfpro to ask specific bots questions!");
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

// Update custom bot count display
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

// Request proactive comment from bots
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

// Update chat participants header
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

// Send user GIF to chat
function sendUserGifToChat(gifUrl) {
    console.log('🎬 sendUserGifToChat called with:', gifUrl);
    // Add the GIF to the chat as a user GIF-only message
    addMessageToChat('user', gifUrl, null, true);
    console.log('✅ GIF added to chat');
    // Optionally, send to backend if you want to persist or broadcast
    // fetch('/chatbot/send_user_gif', { ... })
}

window.sendChatMessage = sendChatMessage;
window.shouldSendGif = shouldSendGif;
window.getRelevantGif = getRelevantGif;
window.extractSearchTerms = extractSearchTerms;
window.changePersonality = changePersonality;
window.getAllowedBotsForProactive = getAllowedBotsForProactive;
window.startPeriodicProactiveComments = startPeriodicProactiveComments;
window.clearChatUI = clearChatUI;
window.setJimNantzDefault = setJimNantzDefault;
window.updateChatInputState = updateChatInputState;
window.updateCustomBotCount = updateCustomBotCount;

// Add missing exports for functions that might be called from other modules
window.requestProactiveComment = requestProactiveComment;
window.updateChatParticipantsHeader = updateChatParticipantsHeader;
window.showBotTypingIndicator = showBotTypingIndicator;
window.removeBotTypingIndicator = removeBotTypingIndicator;
window.shouldBotSendGif = shouldBotSendGif;
window.sendUserGifToChat = sendUserGifToChat;

// Initialize chatbot when DOM is ready
function initChatbotWhenReady() {
    console.log('🚀 Attempting to initialize chatbot...');
    console.log('📋 Document ready state:', document.readyState);
    console.log('🔍 Looking for chat elements...');

    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');

    console.log('📋 Chat elements found:', {
        chatInput: chatInput,
        sendBtn: sendBtn,
        chatInputExists: !!chatInput,
        sendBtnExists: !!sendBtn
    });

    if (chatInput && sendBtn) {
        console.log('✅ Chat elements found, initializing...');
        initializeChatbot();
    } else {
        console.log('⏳ Chat elements not found yet, retrying in 100ms...');
        setTimeout(initChatbotWhenReady, 100);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChatbotWhenReady);
} else {
    initChatbotWhenReady();
}
