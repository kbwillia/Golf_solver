// ===== CHATBOT MODULE =====
// Contains all chatbot functionality, bot interactions, and chat UI management

import { setupChatMicButton } from './voice-input.js';

// Global variables for chatbot state (some are already declared in game-core.js)
let proactiveCommentSent = false;
// let lastNantzCommentTime = 0; // REMOVED - already declared in game-core.js
// let previousActionHistoryLength = 0; // REMOVED - already declared in game-core.js
// let chatbotEnabled = true; // REMOVED - already declared in game-core.js
// let currentPersonality = 'opponent'; // REMOVED - already declared in game-core.js

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
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micChatBtn');
    // const personalitySelect = document.getElementById('personalitySelect'); // REMOVED

    console.log('Chat elements found:', {
        chatInput: !!chatInput,
        sendBtn: !!sendBtn,
        micBtn: !!micBtn,
        // personalitySelect: !!personalitySelect // REMOVED
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

        // Set up speech-to-text mic button
        if (micBtn && chatInput) {
            setupChatMicButton(micBtn, chatInput);
        }

        console.log('✅ Chat event listeners set up');
    } else {
        console.error('❌ Chat elements not found:', {
            chatInput: chatInput,
            sendBtn: sendBtn
        });
    }

    // if (personalitySelect) { // REMOVED
    //     personalitySelect.addEventListener('change', function(e) { // REMOVED
    //         console.log('Personality changed to:', e.target.value); // REMOVED
    //         changePersonality(e.target.value); // REMOVED
    //     }); // REMOVED
    // } // REMOVED
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
    let displayBotName = botName;
    if (sender === 'bot' && botName && !botName.match(/\w+ \w+/)) { // If not already a full name
        displayBotName = getBotNameFromId(botName);
    }

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

// Helper to handle all bot responses (main and proactive)
async function handleAllBotMessages(data, userMessage) {
    let botResponses = [];
    if (data.responses && Array.isArray(data.responses)) {
        botResponses = botResponses.concat(data.responses);
    }
    if (data.proactive_comments && Array.isArray(data.proactive_comments)) {
        botResponses = botResponses.concat(data.proactive_comments);
    }
    // Legacy sequential path
    if (data.response_type === 'sequential' && data.bot_names) {
        let conversationContext = [
            { role: 'user', content: userMessage }
        ];
        for (const botName of data.bot_names) {
            try {
                const botResponse = await fetch('/chatbot/get_bot_response', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        game_id: gameId,
                        message: userMessage,
                        bot_name: botName,
                        conversation_context: conversationContext
                    })
                });
                if (botResponse.ok) {
                    const botData = await botResponse.json();
                    if (botData.success) {
                        botResponses.push(botData);
                        conversationContext.push({
                            role: 'assistant',
                            content: `${botData.bot_name}: ${botData.message}`
                        });
                    } else {
                        addMessageToChat('bot', `Sorry, ${botName} is having trouble responding.`, botName);
                    }
                } else {
                    addMessageToChat('bot', `Sorry, ${botName} is having trouble connecting.`, botName);
                }
            } catch (error) {
                addMessageToChat('bot', `Sorry, ${botName} is having trouble connecting.`, botName);
            }
        }
    }
    // Unified handling for all bot messages (main and proactive)
    for (const botData of botResponses) {
        await handleSingleBotResponse(botData);
    }
}

// Helper to handle extras like Jim Nantz voice and GIFs
async function handleBotExtras(botData, message) {
    const botName = botData.bot_name;
    // If this is Jim Nantz, speak the commentary
    if (botName === 'Jim Nantz' || botName === 'jim_nantz') {
        console.log('🎤 Jim Nantz comment detected:', message);
        console.log('🎤 About to call jimNantzCommentVoice...');
        jimNantzCommentVoice(message);
    } else {
        console.log('🎤 Not Jim Nantz, bot_name is:', botName);
    }
    // Prevent Jim Nantz and Golf Pro from sending GIFs
    if (botName !== 'Jim Nantz' && botName !== 'jim_nantz' && botName !== 'Golf Pro' && botData.should_send_gif) {
        const relevantGif = await getRelevantGif(message, botName);
        addMessageToChat('bot', relevantGif, botName, true); // true = GIF only
    }
}

// Update handleSingleBotResponse to call handleBotExtras
async function handleSingleBotResponse(botData) {
    const botName = botData.bot_name;
    let message = botData.message;
    console.log('Bot response data:', botData);
    // Wait for the reading delay (private, no indicator)
    const readingDelayMs = Math.max(400, Math.round((botData.reading_delay || 1.2) * 1000));
    console.log(`[Bot: ${botName}] Reading delay: ${readingDelayMs}ms`);
    await new Promise(res => setTimeout(res, readingDelayMs));
    // Show typing indicator
    console.log(`[Bot: ${botName}] Typing indicator shown`);
    showBotTypingIndicator(botName);
    // Typing delay based on message length
    const typingDelayMs = Math.max(600, Math.min(3000, 40 * (message ? message.length : 20)));
    console.log(`[Bot: ${botName}] Typing delay: ${typingDelayMs}ms (message length: ${message ? message.length : 0})`);
    await new Promise(res => setTimeout(res, typingDelayMs));
    removeBotTypingIndicator(botName);
    console.log(`[Bot: ${botName}] Message shown:`, message);
    // Add the text message
    addMessageToChat('bot', message, botName);
    // Handle extras (Jim Nantz voice, GIFs)
    await handleBotExtras(botData, message);
}

// Handle proactive comments
async function handleProactiveComments(data) {
    if (data.proactive_comments && Array.isArray(data.proactive_comments)) {
        for (const comment of data.proactive_comments) {
            const botName = comment.bot_name;
            let message = comment.message;
            console.log(`[Proactive][Bot: ${botName}] Typing indicator shown`);
            showBotTypingIndicator(botName);
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
                const indicator = Array.from(chatMessages.children).find(div => div.classList.contains('typing-indicator') && div.textContent.includes(botName));
                console.log(`[Proactive][Bot: ${botName}] Typing indicator in DOM:`, !!indicator);
            }
            const typingDelayMs = Math.max(600, Math.min(3000, 40 * (message ? message.length : 20)));
            console.log(`[Proactive][Bot: ${botName}] Typing delay: ${typingDelayMs}ms (message length: ${message ? message.length : 0})`);
            await new Promise(res => setTimeout(res, typingDelayMs));
            if (chatMessages) {
                const indicator = Array.from(chatMessages.children).find(div => div.classList.contains('typing-indicator') && div.textContent.includes(botName));
                console.log(`[Proactive][Bot: ${botName}] Typing indicator still in DOM before removal:`, !!indicator);
            }
            removeBotTypingIndicator(botName);
            console.log(`[Proactive][Bot: ${botName}] Proactive message shown:`, message);
            addMessageToChat('bot', message, botName);
            if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
}

// Refactored main sendChatMessage function
async function sendChatMessage() {
    console.log('📤 sendChatMessage called');
    console.log('🔍 Checking elements in sendChatMessage...');

    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');

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

    if (!message) {
        console.log('❌ No message to send');
        return; // <-- Add this line to prevent sending the request!
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
        console.log(' Making API request to /chatbot/send_message');
        let mentionedBotNames = [];
        console.log('Sending to backend:', {
            game_id: gameId,
            message: message,
            mentioned_bots: mentionedBotNames
        });
        console.log('🔄 Awaiting response...');
        const response = await fetch('/chatbot/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_id: gameId,
                message: message,
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
            await handleAllBotMessages(data, message);
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
// deleted and replaced with backend logic

// Get relevant GIF from backend Giphy API
async function getRelevantGif(searchTerm, botName = null) {
    try {
        // Use the search term as the message, and get bot name from parameter or fallback
        const message = searchTerm || '';
        const botNameToUse = botName || 'Jim Nantz'; // REMOVED currentPersonality

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


    return fallbackGifs[Math.floor(Math.random() * fallbackGifs.length)];
}

// Helper to get bot name from global bot list
function getBotNameFromId(botId) {
  console.log('getBotNameFromId called with:', botId);
  if (window.allBotsData && botId) {
    console.log('window.allBotsData:', window.allBotsData);
    const bot = window.allBotsData.find(b => b.value === botId);
    if (bot) {
      console.log('Found bot:', bot);
      return bot.name;
    }
  }
  console.log('No match found, returning:', botId);
  return botId;
}

// Export functions globally for backward compatibility
window.setupAutocomplete = setupAutocomplete;
window.initializeChatbot = initializeChatbot;
window.addMessageToChat = addMessageToChat;




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
    const sendBtn = document.getElementById('sendBtn');

    if (chatInput) {
        chatInput.disabled = false;
        chatInput.classList.remove('chat-disabled');
        chatInput.placeholder = 'Chat with opponents';
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
    console.log('updateChatInputState called. currentPersonality:', 'opponent'); // REMOVED
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');

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

    // Create the display text - show actual opponent names instead of static "Opponents"
    let displayText = '';
    if (participants.length > 0) {
        displayText += participants.join(', ');
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
    contentDiv.innerHTML = `<span class="typing-bot-name">${botName}</span> is typing&nbsp;<span class="typing-dots">...</span>`;
    typingDiv.appendChild(contentDiv);
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Remove the typing indicator for a bot. TODO: make a function to imitate 'thinking'
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
// Remove the changePersonality function and all references to it, including any personalitySelect event listeners
// If personalitySelect is not used elsewhere, remove its related code as well
// window.getAllowedBotsForProactive = getAllowedBotsForProactive;
window.requestProactiveComment = requestProactiveComment;
window.clearChatUI = clearChatUI;
window.setJimNantzDefault = setJimNantzDefault;
window.updateChatInputState = updateChatInputState;
// window.updateCustomBotCount = updateCustomBotCount;

// Add missing exports for functions that might be called from other modules
window.requestProactiveComment = requestProactiveComment;
window.updateChatParticipantsHeader = updateChatParticipantsHeader;
window.showBotTypingIndicator = showBotTypingIndicator;
window.removeBotTypingIndicator = removeBotTypingIndicator;
window.sendUserGifToChat = sendUserGifToChat;

// Initialize chatbot when DOM is ready
function initChatbotWhenReady() {
    console.log('🚀 Attempting to initialize chatbot...');
    // console.log('📋 Document ready state:', document.readyState);
    // console.log('🔍 Looking for chat elements...');

    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');

    console.log('📋 Chat elements found:', {
        chatInput: chatInput,
        sendBtn: sendBtn,
        chatInputExists: !!chatInput,
        sendBtnExists: !!sendBtn
    });

    if (chatInput && sendBtn) {
        console.log('✅ Chat elements found, initializing...');
        initializeChatbot();
        // Poll for proactive comments every 10 seconds
        setInterval(requestProactiveComment, 50000);
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

document.addEventListener('DOMContentLoaded', initChatbotWhenReady);
