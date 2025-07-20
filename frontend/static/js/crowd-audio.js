/**
 * Crowd Audio Effects for Start Game Button
 * - Ambient crowd noise that gets louder as mouse approaches button
 * - Crowd roar when button is clicked
 */

class CrowdAudio {
    constructor() {
        this.ambientAudio = null;
        this.roarAudio = null;
        this.synthAmbient = null;
        this.isInitialized = false;
        this.baseVolume = 0.01;
        this.maxVolume = 0.73;
        this.roarVolume = 0.5;
        this.proximityThreshold = 350; // pixels
        this.startButton = null;
        this.audioContext = null;
        this.gainNode = null;
        this.useSynthetic = false;
        this.debugElement = null;
        this.consoleLogging = true; // Auto-enable console logging
        this.isEnabled = true; // Track if crowd audio system is enabled
        this.awaitingUserGesture = false; // Track if we need a user gesture
        this.hasTriedAutoStart = false; // Only try auto-start once per session

        this.init();
    }

    async init() {
        try {
            // Try to load real audio files first
            await this.loadRealAudio();
        } catch (error) {
            console.log('Real audio files not found, using synthetic crowd sounds');
            // Fallback to synthetic audio
            await this.initSyntheticAudio();
        }

        // Get the start button - be more specific to avoid multiple matches
        this.startButton = document.querySelector('button[onclick="startGame()"]') ||
                          document.querySelector('.btn-primary');

        console.log('Start button found:', this.startButton);
        if (this.startButton) {
            const rect = this.startButton.getBoundingClientRect();
            console.log('Button position:', {
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
                centerX: rect.left + rect.width / 2,
                centerY: rect.top + rect.height / 2
            });
        }

        if (this.startButton) {
            // this.createDebugElement(); // Debug panel commented out
            this.setupEventListeners();
            this.isInitialized = true;
            console.log('✅ Crowd audio initialized successfully');
        } else {
            console.warn('❌ Start button not found - crowd audio not initialized');
        }
    }

    async loadRealAudio() {
        // Create ambient crowd noise (looping) - using the user's crowd.mp3 file
        this.ambientAudio = new Audio('/static/sounds/crowd.mp3');
        this.ambientAudio.loop = true;
        this.ambientAudio.volume = 0;
        this.ambientAudio.preload = 'auto';

        // Create crowd roar sound - using crowd_woo.mp3
        this.roarAudio = new Audio('/static/sounds/crowd_woo.mp3');
        this.roarAudio.volume = this.roarVolume;
        this.roarAudio.preload = 'auto';

        // Test if ambient audio loads
        return new Promise((resolve, reject) => {
            this.ambientAudio.addEventListener('canplaythrough', resolve, { once: true });
            this.ambientAudio.addEventListener('error', reject, { once: true });

            // Trigger load
            this.ambientAudio.load();

            // Timeout fallback
            setTimeout(() => reject(new Error('Audio load timeout')), 3000);
        });
    }

    async initSyntheticAudio() {
        try {
            // Create Web Audio context for synthetic crowd sounds
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.gainNode = this.audioContext.createGain();
            this.gainNode.connect(this.audioContext.destination);
            this.gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);

            // Use crowd_woo.mp3 for roar effect
            this.roarAudio = new Audio('/static/sounds/crowd_woo.mp3');
            this.roarAudio.volume = this.roarVolume;
            this.roarAudio.preload = 'auto';

            this.useSynthetic = true;
            console.log('Synthetic crowd audio initialized');
        } catch (error) {
            console.warn('Could not initialize synthetic audio:', error);
        }
    }

    generateCrowdNoise() {
        if (!this.audioContext || !this.useSynthetic) return;

        // Create multiple noise sources to simulate crowd
        const bufferSize = this.audioContext.sampleRate * 2; // 2 seconds
        const buffer = this.audioContext.createBuffer(2, bufferSize, this.audioContext.sampleRate);

        for (let channel = 0; channel < buffer.numberOfChannels; channel++) {
            const channelData = buffer.getChannelData(channel);
            for (let i = 0; i < bufferSize; i++) {
                // Create filtered noise that sounds like distant crowd
                const noise = (Math.random() * 2 - 1) * 0.1;
                const modulation = Math.sin(i * 0.001) * 0.5 + 0.5;
                channelData[i] = noise * modulation;
            }
        }

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        source.loop = true;
        source.connect(this.gainNode);
        source.start();

        this.synthAmbient = source;
    }

    createDebugElement() {
        // Create a debug element to show volume levels
        this.debugElement = document.createElement('div');
        this.debugElement.id = 'crowdAudioDebug';
        this.debugElement.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 1000;
            cursor: pointer;
            transition: background-color 0.2s;
        `;
        this.debugElement.innerHTML = `
            <div>🎵 Crowd Audio Debug <span style="font-size: 10px;">(console logging auto-enabled)</span></div>
            <div id="crowdDistance">Distance: -- (threshold: ${this.proximityThreshold}px)</div>
            <div id="crowdVolume">Volume: 0%</div>
            <div id="crowdStatus">Status: Inactive</div>
            <div id="crowdAudioType" style="font-size: 10px; color: #888;">Audio: Not loaded</div>
            <div id="crowdConsoleStatus" style="font-size: 10px; color: #44ff44;">Console: ON</div>
        `;
        document.body.appendChild(this.debugElement);

                // Debug panel is now read-only (console logging always enabled)
        this.debugElement.style.backgroundColor = 'rgba(0, 100, 0, 0.8)'; // Green background to show it's active
        console.log('🎵 Crowd audio console logging: AUTO-ENABLED');
    }

    preloadAndStartAudio() {
        // Try to start audio immediately without user interaction
        if (this.ambientAudio && this.ambientAudio.readyState >= 2) {
            console.log('🎵 Attempting to auto-start ambient audio...');
            this.ambientAudio.play().then(() => {
                console.log('✅ Ambient audio auto-started successfully');
                // Pause it immediately so it's ready to play when needed
                this.ambientAudio.pause();
                this.ambientAudio.currentTime = 0;
            }).catch(error => {
                console.log('⚠️ Auto-start failed (will start on first proximity):', error.message);
            });
        }
    }

    setupEventListeners() {
        // Mouse move listener for proximity detection
        document.addEventListener('mousemove', (e) => {
            this.handleMouseMove(e);
        });

        // Click listener for roar effect and system disable
        this.startButton.addEventListener('click', () => {
            this.playRoarAndDisable();
        });

        // Auto-start ambient audio when first needed (no user interaction required)
        this.autoStartReady = true;

        // Try to pre-load and start audio immediately
        this.preloadAndStartAudio();

        // Watch for game setup screen to re-enable crowd audio
        this.watchForGameSetup();
    }

    watchForGameSetup() {
        // Watch for when the game setup screen becomes visible again
        const gameSetup = document.getElementById('gameSetup');
        if (gameSetup) {
            // Use MutationObserver to watch for changes in the game setup visibility
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        const isVisible = gameSetup.style.display !== 'none';
                        if (isVisible && !this.isEnabled) {
                            console.log('🎵 Game setup screen detected - re-enabling crowd audio');
                            this.enableCrowdAudio();
                        }
                    }
                });
            });

            // Also watch for display changes
            const checkVisibility = () => {
                const isVisible = gameSetup.style.display !== 'none' &&
                                gameSetup.offsetParent !== null;
                if (isVisible && !this.isEnabled) {
                    console.log('🎵 Game setup screen detected - re-enabling crowd audio');
                    this.enableCrowdAudio();
                }
            };

            // Check periodically and on DOM changes
            setInterval(checkVisibility, 1000);
            observer.observe(gameSetup, {
                attributes: true,
                attributeFilter: ['style', 'class']
            });

            console.log('👀 Watching for game setup screen to re-enable crowd audio');
        } else {
            console.warn('Game setup element not found for crowd audio re-enabling');
        }
    }

    async startAmbientAudio() {
        if (this.useSynthetic) {
            if (this.audioContext && this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            if (!this.synthAmbient) {
                this.generateCrowdNoise();
            }
            console.log('🎵 Synthetic ambient crowd audio started');
        } else if (this.ambientAudio && this.ambientAudio.readyState >= 2) {
            try {
                await this.ambientAudio.play();
                console.log('🎵 Ambient crowd audio started');
            } catch (error) {
                console.warn('⚠️ Could not start ambient audio:', error);
            }
        }
    }

    handleMouseMove(event) {
        if (!this.isInitialized || !this.startButton || !this.isEnabled) {
            if (this.consoleLogging) {
                console.log('Mouse move ignored: initialized=', this.isInitialized, 'startButton=', !!this.startButton, 'enabled=', this.isEnabled);
            }
            return;
        }

        // Get button position and dimensions
        const buttonRect = this.startButton.getBoundingClientRect();
        const buttonCenterX = buttonRect.left + buttonRect.width / 2;
        const buttonCenterY = buttonRect.top + buttonRect.height / 2;

        // Calculate distance from mouse to button center
        const mouseX = event.clientX;
        const mouseY = event.clientY;
        const distance = Math.sqrt(
            Math.pow(mouseX - buttonCenterX, 2) +
            Math.pow(mouseY - buttonCenterY, 2)
        );

        // Debug logging for position calculations
        if (this.consoleLogging) {
            console.log('Mouse position:', { x: mouseX, y: mouseY });
            console.log('Button center:', { x: buttonCenterX, y: buttonCenterY });
            console.log('Button rect:', buttonRect);
        }

        // Calculate volume based on proximity
        let volume = 0;
        let proximity = 0;
        let inRange = distance <= this.proximityThreshold;

        if (inRange) {
            // Closer = louder (inverse relationship)
            proximity = 1 - (distance / this.proximityThreshold);
            volume = this.baseVolume + (proximity * (this.maxVolume - this.baseVolume));
        }

        // Update debug display
        this.updateDebugDisplay(distance, volume, proximity, inRange);

        // Console logging for debugging (click debug panel to toggle)
        if (this.consoleLogging) {
            console.log(`Distance: ${distance.toFixed(1)}px, Volume: ${(volume * 100).toFixed(1)}%, Proximity: ${(proximity * 100).toFixed(1)}%, InRange: ${inRange}`);
        }

        // Handle audio based on range
        if (inRange && this.isEnabled) {
            // Try to auto-start only once per session
            if (!this.hasTriedAutoStart) {
                this.hasTriedAutoStart = true;
                this.ensureAudioPlaying();
            }
            this.ensureAudioPlaying();
            this.setAmbientVolume(volume);
            if (this.consoleLogging) {
                console.log(`🎵 In range: setting volume to ${(volume * 100).toFixed(1)}%`);
            }
        } else if (!inRange) {
            this.stopAmbientAudio();
            if (this.consoleLogging) {
                console.log('🔇 Out of range: stopping audio');
            }
        }
    }

    updateDebugDisplay(distance, volume, proximity, inRange) {
        if (!this.debugElement) return;

        const distanceEl = document.getElementById('crowdDistance');
        const volumeEl = document.getElementById('crowdVolume');
        const statusEl = document.getElementById('crowdStatus');
        const audioTypeEl = document.getElementById('crowdAudioType');

        if (distanceEl) {
            distanceEl.textContent = `Distance: ${distance.toFixed(1)}px (threshold: ${this.proximityThreshold}px)`;
        }
                if (volumeEl) {
            // Show both target and actual volume
            const targetPercent = (volume * 100).toFixed(1);
            let actualVolume = 0;

            if (this.useSynthetic && this.gainNode) {
                actualVolume = this.gainNode.gain.value;
            } else if (this.ambientAudio) {
                actualVolume = this.ambientAudio.volume;
            }

            const actualPercent = (actualVolume * 100).toFixed(1);
            volumeEl.textContent = `Volume: Target=${targetPercent}% | Actual=${actualPercent}%`;

            // Color code based on actual volume for visual feedback
            const displayVolume = Math.max(volume, actualVolume);
            if (displayVolume > 0.2) {
                volumeEl.style.color = '#ff4444'; // Red for loud
            } else if (displayVolume > 0.1) {
                volumeEl.style.color = '#ffaa44'; // Orange for medium
            } else if (displayVolume > 0) {
                volumeEl.style.color = '#44ff44'; // Green for quiet
            } else {
                volumeEl.style.color = '#888888'; // Gray for silent
            }
        }
        if (statusEl) {
            if (!this.isEnabled) {
                statusEl.textContent = 'Status: 🎮 DISABLED (Game in progress)';
                statusEl.style.color = '#666666';
            } else if (inRange) {
                statusEl.textContent = `Status: Active (${(proximity * 100).toFixed(1)}% proximity)`;
                statusEl.style.color = '#44ff44';
            } else {
                statusEl.textContent = 'Status: Out of range - AUDIO STOPPED';
                statusEl.style.color = '#ff4444';
            }
        }

        // Update audio type display
        if (audioTypeEl) {
            if (this.useSynthetic) {
                const synthState = inRange ? 'active' : 'silent (out of range)';
                audioTypeEl.textContent = `Audio: Synthetic (${synthState})`;
                audioTypeEl.style.color = inRange ? '#ffaa44' : '#888888';
            } else if (this.ambientAudio) {
                let audioState;
                if (!inRange) {
                    audioState = 'stopped (out of range)';
                } else {
                    audioState = this.ambientAudio.paused ? 'paused' : 'playing';
                }
                audioTypeEl.textContent = `Audio: Real (crowd.mp3, ${audioState})`;
                audioTypeEl.style.color = inRange && !this.ambientAudio.paused ? '#44ff44' : '#888888';
            } else {
                audioTypeEl.textContent = 'Audio: Not loaded';
                audioTypeEl.style.color = '#888888';
            }
        }
    }

        ensureAudioPlaying() {
        if (!this.isEnabled) {
            console.log('❌ Audio play ignored - system disabled');
            return;
        }

        if (this.useSynthetic) {
            // Synthetic audio should already be playing if initialized
            if (this.audioContext && this.audioContext.state === 'suspended') {
                this.audioContext.resume().catch(console.warn);
            }
        } else if (this.ambientAudio) {
            // Real audio: make sure it's playing
            if (this.ambientAudio.paused) {
                // Try to play, and if blocked, set up a click listener
                this.ambientAudio.play().then(() => {
                    console.log('✅ Ambient audio started automatically');
                    this.awaitingUserGesture = false;
                    this.removeUserGestureListener();
                }).catch(error => {
                    if (!this.awaitingUserGesture) {
                        console.warn('⚠️ Audio play blocked by browser, waiting for user gesture...');
                        this.awaitingUserGesture = true;
                        this.addUserGestureListener();
                    }
                });
            }
        }
    }

    stopAmbientAudio() {
        if (this.useSynthetic && this.gainNode) {
            // For synthetic audio, just set volume to 0
            const currentTime = this.audioContext.currentTime;
            this.gainNode.gain.linearRampToValueAtTime(0, currentTime + 0.1);
        } else if (this.ambientAudio) {
            // For real audio, pause it completely
            if (!this.ambientAudio.paused) {
                this.ambientAudio.pause();
            }
        }

        if (this.consoleLogging) {
            console.log('Ambient audio stopped - out of range');
        }
    }

        setAmbientVolume(targetVolume) {
        if (!this.isEnabled) {
            console.log('❌ Volume change ignored - system disabled');
            return;
        }

        console.log(`🎵 Setting ambient volume to: ${targetVolume.toFixed(3)} (${(targetVolume * 100).toFixed(1)}%)`);
        console.log(`Using synthetic: ${this.useSynthetic}, Has ambientAudio: ${!!this.ambientAudio}, Has gainNode: ${!!this.gainNode}`);

        if (this.useSynthetic && this.gainNode) {
            // Smooth volume transition for synthetic audio
            const currentTime = this.audioContext.currentTime;
            const currentVolume = this.gainNode.gain.value;
            console.log(`🎵 Synthetic audio: ${currentVolume.toFixed(3)} → ${targetVolume.toFixed(3)}`);
            this.gainNode.gain.linearRampToValueAtTime(targetVolume, currentTime + 0.1);
        } else if (this.ambientAudio) {
            // Direct volume setting for real audio (more responsive)
            const currentVolume = this.ambientAudio.volume;
            console.log(`🎵 Real audio: ${currentVolume.toFixed(3)} → ${targetVolume.toFixed(3)}`);
            console.log(`Audio state: paused=${this.ambientAudio.paused}, readyState=${this.ambientAudio.readyState}, currentTime=${this.ambientAudio.currentTime.toFixed(2)}`);

            // Set volume directly for more immediate response
            this.ambientAudio.volume = Math.max(0, Math.min(1, targetVolume));
        } else {
            console.log('❌ No audio source available for volume control');
        }
    }

        async playRoarAndDisable() {
        console.log('🎮 Start button clicked - playing roar and disabling crowd audio');

        // Play the roar sound first
        await this.playRoar();

        // Fade out the roar sound much sooner (0.1s)
        if (this.roarAudio) {
            const initialVolume = this.roarAudio.volume;
            const fadeSteps = 5;
            const fadeDuration = 2250; // 0.5 seconds
            const volumeStep = initialVolume / fadeSteps;
            for (let i = 1; i <= fadeSteps; i++) {
                setTimeout(() => {
                    if (this.roarAudio) {
                        this.roarAudio.volume = Math.max(0, initialVolume - (volumeStep * i));
                    }
                }, i * (fadeDuration / fadeSteps));
            }
            setTimeout(() => {
                if (this.roarAudio) {
                    this.roarAudio.pause();
                    this.roarAudio.currentTime = 0;
                }
            }, fadeDuration);
        }
        // Then disable the entire crowd audio system immediately
        console.log('🔇 Disabling crowd audio system...');
        this.disableCrowdAudio();
    }

    async playRoar() {
        if (!this.roarAudio) return;

        try {
            // Reset and play roar
            this.roarAudio.currentTime = 0;
            await this.roarAudio.play();

            // Temporarily reduce ambient volume during roar
            const originalVolume = this.useSynthetic ?
                (this.gainNode ? this.gainNode.gain.value : 0) :
                (this.ambientAudio ? this.ambientAudio.volume : 0);

            if (this.useSynthetic && this.gainNode) {
                const currentTime = this.audioContext.currentTime;
                this.gainNode.gain.linearRampToValueAtTime(originalVolume * 0.2, currentTime + 0.1);

                // Restore ambient volume after roar
                setTimeout(() => {
                    if (this.gainNode && this.audioContext) {
                        const restoreTime = this.audioContext.currentTime;
                        this.gainNode.gain.linearRampToValueAtTime(originalVolume, restoreTime + 0.5);
                    }
                }, 1500);
            } else if (this.ambientAudio) {
                this.ambientAudio.volume = originalVolume * 0.3;

                // Restore ambient volume after roar
                setTimeout(() => {
                    if (this.ambientAudio) {
                        this.ambientAudio.volume = originalVolume;
                    }
                }, 2000);
            }

            console.log('Crowd roar played (crowd_woo.mp3)');

            // Update debug display to show roar is playing
            const statusEl = document.getElementById('crowdStatus');
            if (statusEl) {
                statusEl.textContent = 'Status: 🎉 ROAR PLAYING!';
                statusEl.style.color = '#ff44ff';
                // Reset status after roar duration
                setTimeout(() => {
                    if (statusEl) {
                        statusEl.textContent = 'Status: Active';
                        statusEl.style.color = '#44ff44';
                    }
                }, 2000);
            }
        } catch (error) {
            console.warn('Could not play roar audio:', error);
        }
    }

    // Public methods for control
            disableCrowdAudio() {
        console.log('🔇 DISABLING crowd audio system...');
        this.isEnabled = false;

                // Quick fade out over 0.2 seconds
        if (this.useSynthetic && this.gainNode) {
            const currentTime = this.audioContext.currentTime;
            this.gainNode.gain.linearRampToValueAtTime(0, currentTime + 0.2);
            console.log('🔇 Synthetic audio fading out over 0.2 seconds');
        }

        if (this.ambientAudio) {
            // For real audio, we need to fade out manually since we can't ramp
            const currentVolume = this.ambientAudio.volume;
            const fadeSteps = 10; // 10 steps over 0.2 seconds = 20ms per step
            const volumeStep = currentVolume / fadeSteps;

            console.log('🔇 Real audio fading out over 0.2 seconds');

            for (let i = 1; i <= fadeSteps; i++) {
                setTimeout(() => {
                    if (this.ambientAudio && !this.isEnabled) {
                        this.ambientAudio.volume = Math.max(0, currentVolume - (volumeStep * i));
                    }
                }, i * 20); // 20ms intervals
            }

            // Stop completely after fade
            setTimeout(() => {
                if (this.ambientAudio && !this.isEnabled) {
                    this.ambientAudio.pause();
                    this.ambientAudio.currentTime = 0;
                    console.log('🔇 Real audio completely stopped after fade');
                }
            }, 200);
        }

        // Update debug display
        this.updateSystemStatus();

        console.log('✅ Crowd audio system DISABLED - Game started');
    }

    enableCrowdAudio() {
        this.isEnabled = true;

        // Update debug display
        this.updateSystemStatus();

        console.log('🎵 Crowd audio system ENABLED - Back to setup screen');
    }

    updateSystemStatus() {
        const statusEl = document.getElementById('crowdStatus');
        if (statusEl && !this.isEnabled) {
            statusEl.textContent = 'Status: 🎮 DISABLED (Game in progress)';
            statusEl.style.color = '#666666';
        }
    }

    setEnabled(enabled) {
        if (enabled) {
            this.enableCrowdAudio();
        } else {
            this.disableCrowdAudio();
        }
    }

    setVolume(volume) {
        this.maxVolume = Math.max(0, Math.min(1, volume));
    }

    addUserGestureListener() {
        this._userGestureHandler = () => {
            if (this.ambientAudio && this.ambientAudio.paused) {
                this.ambientAudio.play().then(() => {
                    console.log('✅ Ambient audio started after user gesture');
                    this.awaitingUserGesture = false;
                    this.removeUserGestureListener();
                }).catch(error => {
                    console.warn('❌ Still blocked after user gesture:', error);
                });
            }
        };
        document.addEventListener('click', this._userGestureHandler, { once: true });
        document.addEventListener('keydown', this._userGestureHandler, { once: true });
    }
    removeUserGestureListener() {
        if (this._userGestureHandler) {
            document.removeEventListener('click', this._userGestureHandler, { once: true });
            document.removeEventListener('keydown', this._userGestureHandler, { once: true });
            this._userGestureHandler = null;
        }
    }
}

// Initialize crowd audio when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.crowdAudio = new CrowdAudio();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CrowdAudio;
}