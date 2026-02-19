// Speech-to-text logic for chat input using Web Speech API
export function setupChatMicButton(micBtn, chatInput, enableSpacebarShortcut = true) {
    let recognition;
    let recognizing = false;
    let originalBtnBg = micBtn.style.backgroundColor;
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = function() {
            recognizing = true;
            micBtn.style.background = '#b71c1c';
            micBtn.innerHTML = '<span style="font-size:1.2em;">🎙️</span>';
        };
        recognition.onend = function() {
            recognizing = false;
            micBtn.style.background = originalBtnBg;
            micBtn.innerHTML = '<span style="font-size:1.2em;">🎙️</span>';
        };
        recognition.onerror = function(event) {
            recognizing = false;
            micBtn.style.background = originalBtnBg;
            micBtn.innerHTML = '<span style="font-size:1.2em;">🎙️</span>';
            alert('Speech recognition error: ' + event.error);
        };
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            chatInput.focus();
        };

        micBtn.addEventListener('click', function() {
            if (recognizing) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });

        // Ctrl (push-to-talk) shortcut logic for chat input only
        if (enableSpacebarShortcut && chatInput) {
            let ctrlHeld = false;
            chatInput.addEventListener('keydown', function(e) {
                if ((e.code === 'ControlLeft' || e.code === 'ControlRight') && !ctrlHeld && document.activeElement === chatInput) {
                    ctrlHeld = true;
                    e.preventDefault();
                    if (!micBtn.disabled && micBtn.innerHTML.includes('🎤')) {
                        micBtn.click();
                    }
                }
            });
            chatInput.addEventListener('keyup', function(e) {
                if ((e.code === 'ControlLeft' || e.code === 'ControlRight') && ctrlHeld) {
                    ctrlHeld = false;
                    e.preventDefault();
                    if (!micBtn.disabled && micBtn.innerHTML.includes('🎙️')) {
                        micBtn.click();
                    }
                }
            });
        }

        // Global Ctrl shortcut for voice input (works anywhere)
        let globalCtrlHeld = false;
        window.addEventListener('keydown', function(e) {
            if ((e.code === 'ControlLeft' || e.code === 'ControlRight') && !globalCtrlHeld) {
                globalCtrlHeld = true;
                e.preventDefault();
                if (!recognizing) {
                    recognition.start();
                }
            }
        });
        window.addEventListener('keyup', function(e) {
            if ((e.code === 'ControlLeft' || e.code === 'ControlRight') && globalCtrlHeld) {
                globalCtrlHeld = false;
                e.preventDefault();
                if (recognizing) {
                    recognition.stop();
                }
            }
        });

        let spaceHeld = false;
        let spaceHoldTimeout = null;
        let chatInputPrevValue = '';
        const SPACE_HOLD_THRESHOLD = 400; // ms

        window.addEventListener('keydown', function(e) {
            if (e.code === 'Space' && !spaceHeld) {
                spaceHeld = true;
                // Start a timer to trigger recording only if held long enough
                spaceHoldTimeout = setTimeout(() => {
                    // Only start recording if still held
                    if (spaceHeld) {
                        e.preventDefault();
                        if (chatInput) {
                            chatInputPrevValue = chatInput.value;
                        }
                        if (!recognizing) {
                            recognition.start();
                        }
                    }
                }, SPACE_HOLD_THRESHOLD);
            }
            // If recording is already active, always prevent default
            if (e.code === 'Space' && recognizing) {
                e.preventDefault();
            }
        });

        window.addEventListener('keyup', function(e) {
            if (e.code === 'Space' && spaceHeld) {
                spaceHeld = false;
                clearTimeout(spaceHoldTimeout);
                // Only stop recording if it was started
                if (recognizing) {
                    e.preventDefault();
                    recognition.stop();
                }
            }
        });
        // Patch onresult to restore input value before inserting transcript
        const originalOnResult = recognition.onresult;
        // --- Automated send logic ---
        let sendTimer = null;
        let animationInterval = null;
        const SEND_DELAY = 3000; // ms
        const ANIMATION_INTERVAL = 100; // ms
        // Get the chat input container for animation
        const chatInputContainer = chatInput.closest('.chat-input-container');
        function setFillAnim(percent) {
            if (chatInputContainer) {
                chatInputContainer.classList.add('chat-input-fill-anim');
                // Remove any previous style tag
                if (chatInputContainer._fillAnimStyle) {
                    chatInputContainer._fillAnimStyle.remove();
                }
                // Set width for both ::before and ::after
                const styleSheet = document.createElement('style');
                styleSheet.innerHTML = `
                    .chat-input-fill-anim::before,
                    .chat-input-fill-anim::after {
                        width: ${percent}%;
                    }
                `;
                document.head.appendChild(styleSheet);
                chatInputContainer._fillAnimStyle = styleSheet;
                // Set shimmer duration to match SEND_DELAY
                chatInputContainer.style.setProperty('--shimmer-duration', (SEND_DELAY / 1000) + 's');
            }
        }
        function clearFillAnim() {
            if (chatInputContainer) {
                chatInputContainer.classList.remove('chat-input-fill-anim');
                chatInputContainer.style.removeProperty('--fill-width');
                chatInputContainer.style.removeProperty('--shimmer-duration');
                if (chatInputContainer._fillAnimStyle) {
                    chatInputContainer._fillAnimStyle.remove();
                    chatInputContainer._fillAnimStyle = null;
                }
            }
        }
        function startSendCountdown() {
            let timeLeft = SEND_DELAY / 2000;
            let elapsed = 0;
            chatInput.dataset.originalPlaceholder = chatInput.placeholder;
            chatInput.placeholder = `Sending in ${timeLeft.toFixed(1)}...`;
            setFillAnim(0);
            animationInterval = setInterval(() => {
                elapsed += ANIMATION_INTERVAL;
                timeLeft = (SEND_DELAY - elapsed) / 1000;
                if (timeLeft > 0) {
                    chatInput.placeholder = `Sending in ${timeLeft.toFixed(1)}...`;
                    setFillAnim((elapsed / SEND_DELAY) * 100);
                }
            }, ANIMATION_INTERVAL);
            sendTimer = setTimeout(() => {
                clearInterval(animationInterval);
                chatInput.placeholder = chatInput.dataset.originalPlaceholder || '';
                setFillAnim(100);
                setTimeout(clearFillAnim, 200); // Let the bar fill for a moment
                // Trigger send (simulate send button or call sendChatMessage)
                if (typeof window.sendChatMessage === 'function') {
                    window.sendChatMessage();
                } else {
                    // fallback: try to click send button
                    const sendBtn = document.getElementById('sendChatBtn');
                    if (sendBtn) sendBtn.click();
                }
            }, SEND_DELAY);
        }
        function cancelSendCountdown() {
            clearTimeout(sendTimer);
            clearInterval(animationInterval);
            chatInput.placeholder = chatInput.dataset.originalPlaceholder || '';
            clearFillAnim();
        }
        // Cancel countdown if user types or focuses input
        chatInput.addEventListener('keydown', cancelSendCountdown);
        chatInput.addEventListener('focus', cancelSendCountdown);
        // --- End automated send logic ---
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            if (chatInput) {
                // Restore the value before spacebar was pressed, then insert transcript
                chatInput.value = transcript;
                chatInput.focus();
                chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);
                startSendCountdown();
            }
            if (typeof originalOnResult === 'function') {
                originalOnResult.apply(this, arguments);
            }
        };
    } else {
        micBtn.disabled = true;
        micBtn.title = 'Speech recognition not supported in this browser.';
    }
}
