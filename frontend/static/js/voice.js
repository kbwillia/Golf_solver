// ===== VOICE MODULE =====
// Voice system functionality for the Golf Card Game

// ===== VOICE VARIABLES =====
let voiceEnabled = false; // Track if voice is enabled - DEFAULT TO OFF
let voiceType = 'browser'; // Fixed to browser-only since out of API credits
let browserVoices = []; // Available browser voices

// ===== VOICE FUNCTIONS =====

function initializeVoiceStatus() {
    const voiceStatus = document.getElementById('voiceStatus');
    if (voiceStatus) {
        voiceStatus.textContent = voiceEnabled ? '🔊 Voice: ON' : '🔇 Voice: OFF';
    }
    console.log('🎤 Voice system initialized with status:', voiceEnabled ? 'enabled' : 'disabled');
}

// Load voices asynchronously
function loadVoices() {
    if (speechSynthesis) {
        const voices = speechSynthesis.getVoices();
        console.log('Available voices:', voices.length);
        voices.forEach(voice => {
            console.log('Voice:', voice.name, voice.lang);
        });
    }
}

// Toggle voice system on/off
function toggleVoiceSystem() {
    voiceEnabled = !voiceEnabled;
    const voiceStatus = document.getElementById('voiceStatus');
    const voiceToggleBtn = document.getElementById('voiceToggleBtn');

    if (voiceStatus) {
        voiceStatus.textContent = voiceEnabled ? '🔊 Voice: ON' : '🔇 Voice: OFF';
    }

    // Update button styling
    if (voiceToggleBtn) {
        if (voiceEnabled) {
            voiceToggleBtn.classList.add('active');
        } else {
            voiceToggleBtn.classList.remove('active');
        }
    }

    console.log('🎤 Voice system:', voiceEnabled ? 'enabled' : 'disabled');
    console.log('🎤 Voice type:', voiceType);
}

// Initialize voice system
function initializeVoiceSystem() {
    // Load browser voices
    loadBrowserVoices();
}

// Load available browser voices
function loadBrowserVoices() {
    if ('speechSynthesis' in window) {
        // Wait for voices to load
        speechSynthesis.onvoiceschanged = function() {
            browserVoices = speechSynthesis.getVoices();
            console.log('🎤 Available voices:', browserVoices.length);
            browserVoices.forEach(voice => {
                console.log('🎤 Voice:', voice.name, voice.lang);
            });
        };

        // Try to get voices immediately (might already be loaded)
        browserVoices = speechSynthesis.getVoices();
        if (browserVoices.length > 0) {
            console.log('🎤 Available voices:', browserVoices.length);
            browserVoices.forEach(voice => {
                console.log('🎤 Voice:', voice.name, voice.lang);
            });
        }
    }
}

// Enhanced TTS function that supports both browser and backend
function speakText(text, voiceName = null) {
    // Check both old and new voice system variables
    if (!voiceEnabled) {
        console.log('🎤 Voice disabled (old system), skipping TTS');
        return;
    }

    console.log('🎤 speakText called with:', { text: text.substring(0, 50) + '...', voiceName, voiceType, voiceEnabled });

    if (voiceType === 'browser') {
        speakWithBrowser(text, voiceName);
    } else {
        speakWithBackend(text, voiceName);
    }
}

// Browser-based TTS
function speakWithBrowser(text, voiceName = null) {
    console.log('🎤 speakWithBrowser called with:', text.substring(0, 50) + '...');

    if (!('speechSynthesis' in window)) {
        console.log('🎤 Browser TTS not supported');
        return;
    }

    // Cancel any ongoing speech
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    // Set voice if specified or use default Google US English
    if (voiceName && browserVoices.length > 0) {
        const selectedVoice = browserVoices.find(voice =>
            voice.name.includes(voiceName) || voice.name === voiceName
        );
        if (selectedVoice) {
            utterance.voice = selectedVoice;
            console.log('🎤 Using specified browser voice:', selectedVoice.name);
        }
    } else if (browserVoices.length > 0) {
        // Try to find the best Google voice for Jim Nantz commentary
        const preferredVoices = [
            'Google US English',           // Primary choice
            'Google UK English Male',      // Alternative 1
            'Google UK English Female',    // Alternative 2
            'Microsoft David - English (United States)', // Windows alternative
            'Microsoft Zira - English (United States)'  // Windows alternative
        ];

        let selectedVoice = null;
        for (const voiceName of preferredVoices) {
            selectedVoice = browserVoices.find(voice =>
                voice.name === voiceName && voice.lang.startsWith('en-')
            );
            if (selectedVoice) {
                console.log('🎤 Using preferred browser voice:', selectedVoice.name);
                break;
            }
        }

        if (!selectedVoice) {
            // Fallback to any English voice if preferred voices not found
            const englishVoice = browserVoices.find(voice =>
                voice.lang.startsWith('en-')
            );
            if (englishVoice) {
                selectedVoice = englishVoice;
                console.log('🎤 Using fallback English voice:', englishVoice.name);
            }
        }

        if (selectedVoice) {
            utterance.voice = selectedVoice;
        }
    } else {
        console.log('🎤 No browser voices available, using system default');
    }

    // Set default properties
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 0.8;

    // Add event listeners for debugging
    utterance.onstart = () => console.log('🎤 Speech started');
    utterance.onend = () => console.log('🎤 Speech ended');
    utterance.onerror = (event) => console.error('🎤 Speech error:', event.error);

    speechSynthesis.speak(utterance);
    console.log('🎤 Speaking with browser TTS:', text.substring(0, 50) + '...');
}

// Backend-based TTS
function speakWithBackend(text, voiceName = null) {
    fetch('/api/tts', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            text: text,
            voice: voiceName || 'default'
        })
    })
    .then(response => response.blob())
    .then(blob => {
        const audio = new Audio(URL.createObjectURL(blob));
        audio.play();
        console.log('🎤 Speaking with backend TTS:', text.substring(0, 50) + '...');
    })
    .catch(error => {
        console.error('🎤 Backend TTS error:', error);
        // Fallback to browser TTS
        speakWithBrowser(text, voiceName);
    });
}

// ===== SPECIALIZED VOICE FUNCTIONS =====

// Jim Nantz voice function
window.jimNantzCommentVoice = function(text) {
    console.log('🎤 jimNantzCommentVoice called with:', text);
    console.log('🎤 voiceEnabled:', voiceEnabled);
    console.log('🎤 voiceType:', voiceType);
    console.log('🎤 speechSynthesis available:', !!speechSynthesis);
    console.log('🎤 browserVoices loaded:', browserVoices.length);

    speakText(text); // Use default Google US English voice since we're browser-only
};

// ===== DEBUGGING AND TESTING FUNCTIONS =====

// Test function for debugging voice system
window.testVoiceSystem = function() {
    console.log('🎤 Testing voice system...');
    console.log('🎤 voiceEnabled:', voiceEnabled);
    console.log('🎤 voiceType:', voiceType);
    console.log('🎤 speechSynthesis available:', !!speechSynthesis);
    console.log('🎤 browserVoices loaded:', browserVoices.length);

    if (browserVoices.length > 0) {
        console.log('🎤 Available voices:');
        browserVoices.forEach((voice, index) => {
            console.log(`🎤 ${index}: ${voice.name} (${voice.lang})`);
        });
    }

    // Test speech
    speakText("Hello friends, this is a test of the voice system!");
};

// Function to list all available voices (for debugging)
window.listAvailableVoices = function() {
    console.log('🎤 === AVAILABLE VOICES ===');
    if (browserVoices.length === 0) {
        console.log('🎤 No voices loaded yet. Try again in a few seconds.');
        return;
    }

    browserVoices.forEach((voice, index) => {
        const isPreferred = [
            'Google US English',
            'Google UK English Male',
            'Google UK English Female',
            'Microsoft David - English (United States)',
            'Microsoft Zira - English (United States)'
        ].includes(voice.name);

        const marker = isPreferred ? '⭐' : '  ';
        console.log(`🎤 ${marker} ${index}: ${voice.name} (${voice.lang})`);
    });
    console.log('🎤 === END VOICES ===');
};

// ===== INITIALIZATION =====

// Wait for voices to load
if (speechSynthesis) {
    speechSynthesis.onvoiceschanged = loadVoices;
    // Also try loading immediately in case they're already available
    loadVoices();
}

// Call initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeVoiceStatus);
} else {
    initializeVoiceStatus();
}

// Initialize voice system
initializeVoiceSystem();

console.log('🎤 Voice module loaded successfully!');