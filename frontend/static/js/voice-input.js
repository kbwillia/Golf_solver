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
            micBtn.style.background = '#2e7d32';
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

        // Ctrl (push-to-talk) shortcut logic
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
    } else {
        micBtn.disabled = true;
        micBtn.title = 'Speech recognition not supported in this browser.';
    }
}
