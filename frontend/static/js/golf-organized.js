// ===== GOLF GAME ORGANIZED FOR MODULARIZATION =====
// This file is organized into clear sections for easy extraction to modular files

// ===== GOLF GAME CORE VARIABLES =====
let currentGameState = null; // Holds the current game state from backend
let gameId = null; // Unique game session ID
let drawnCard = null; // Card drawn from deck
let currentAction = null; // Current action type
let dragActive = false; // Drag state for discard
let draggedDiscardCard = null; // Card being dragged from discard
let drawnCardData = null; // Data for the currently drawn card
let drawnCardDragActive = false; // Drag state for drawn card
let lastGameSetupReset = 0; // Track which game we last reset the setup for
let turnAnimateTimeout = null; // Timeout for turn animation
let lastTurnIndex = null; // Last turn index to detect turn changes
let setupHideTimeout = null; // Timeout for hiding setup cards
let setupCardsHidden = false; // Whether setup cards are hidden
let setupViewInterval = null; // Interval for setup view timer
let cardVisibilityDuration = 1.5; // Default duration, updated from user input
const SNAP_THRESHOLD = 30; // pixels
let isMyTurn = false;
let actionInProgress = false; // Prevents multiple simultaneous actions
let pollingPaused = false; // Used to pause polling during actions
let isDrawingFromDeck = false; // Track if deck is being drawn from for fade effect
let previousGameState = null;
let aiTurnInProgress = false; // Prevents multiple concurrent AI turn polling
let humanDiscardPosition = null; // Track position for human discard animation
let humanDiscardAction = null; // Track action type for human discard animation
let humanDrawnCardPosition = null; // Track position for drawn card replacement animation
let previousActionHistory = []; // Place this at the top of your JS file
let previousHumanPairs = [];
let previousActionHistoryLength = 0;

// ===== CHATBOT VARIABLES =====
let chatbotEnabled = true;
let currentPersonality = 'Jim Nantz';
let lastNantzCommentTime = 0; // Place this at the top of your JS file if not already present
let lastNantzTurn = null;
let proactiveCommentTimeout = null;
let proactiveCommentInterval = null;

// ===== NOTIFICATION VARIABLES =====
// Celebration GIFs for human win (now loaded from JSON)
let celebrationGifs = [];
fetch('/static/golf_celebration_gifs.json')
    .then(response => response.json())
    .then(data => {
        if (data && data.data) {
            celebrationGifs = data.data
                .map(gif => {
                    if (gif.images && gif.images.downsized_large && gif.images.downsized_large.url) {
                        const url = gif.images.downsized_large.url;
                        // Clean the URL by removing tracking parameters
                        return url.split('?')[0];
                    }
                    return null;
                })
                .filter(Boolean);
        }
    });

// Hurry up timer for slow play
let hurryUpTimer = null;
const HURRY_UP_DELAY = 150000; // 150 seconds
let lastHurryUpGifIndex = -1; // Track last shown GIF to avoid repeats
const hurryUpGifs = [
    "https://media.giphy.com/media/3oriNYQX2lC6dfW2cK/giphy.gif", // Hurry up
    "https://media.giphy.com/media/TqiwHbFBaZ4ti/giphy.gif", // Time's up
    "https://media.giphy.com/media/l0HlPystfePnAI3G8/giphy.gif", // Waiting
    "https://media.giphy.com/media/26tPplGWjN0xLybiU/giphy.gif" ,// Tap tap tap
    "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3cXh4bnI2YjNzcDR2azZ0cmt0M2FxOGJqdWxibmg1OHlxOGpoMDhkbSZlcD12MV9naWZzX3JlbGF0ZWQmY3Q9Zw/M2EazvA5Fyu8U/giphy.gif" // well we're waiting
];

console.log('🎯 Golf.js loaded successfully!');

// ===== PROBABILITIES MODULE =====
// Custom HTML legend plugin for Chart.js
const htmlLegendPlugin = {
  id: 'htmlLegend',
  afterUpdate(chart, args, options) {
    const legendContainer = document.getElementById('customLegend');
    if (!legendContainer) return;
    const items = chart.options.plugins.legend.labels.generateLabels(chart);
    legendContainer.innerHTML = items.map(item => `
      <div class="legend-item-box">
        <span class="legend-color-box" style="background:${item.fillStyle};"></span>
        <span>${item.text}</span>
      </div>
    `).join('');
  }
};

// ===== GAME CORE MODULE =====
// Core game functions: startGame, refreshGameState, restartGame, replayGame, nextGame, startGameWithSettings, pollAITurns
// Utility functions: pausePolling, resumePolling, findAIDiscardedCard, aiJustMoved, deepCopy
// Timer functions: showSetupViewTimer, hideSetupViewTimer

async function startGame() {
    // [FULL startGame FUNCTION GOES HERE]
}

async function refreshGameState() {
    // [FULL refreshGameState FUNCTION GOES HERE]
}

function restartGame() {
    // [FULL restartGame FUNCTION GOES HERE]
}

function replayGame() {
    // [FULL replayGame FUNCTION GOES HERE]
}

async function nextGame() {
    // [FULL nextGame FUNCTION GOES HERE]
}

async function startGameWithSettings(gameMode, opponentType, playerName, numGames) {
    // [FULL startGameWithSettings FUNCTION GOES HERE]
}

async function pollAITurns() {
    // [FULL pollAITurns FUNCTION GOES HERE]
}

function pausePolling() { pollingPaused = true; }
function resumePolling() { pollingPaused = false; }

function findAIDiscardedCard(prev, curr) {
    // [FULL findAIDiscardedCard FUNCTION GOES HERE]
}

function aiJustMoved() {
    // [FULL aiJustMoved FUNCTION GOES HERE]
}

function deepCopy(obj) {
    return JSON.parse(JSON.stringify(obj));
}

function showSetupViewTimer(seconds) {
    // [FULL showSetupViewTimer FUNCTION GOES HERE]
}

function hideSetupViewTimer() {
    // [FULL hideSetupViewTimer FUNCTION GOES HERE]
}

// ===== GAME UI MODULE =====
// UI update functions: updateGameDisplay, actuallyUpdateUI, updatePlayerGrids, updateGameAndRoundInfo, updateLastActionPanel
// Interactivity functions: updateInteractivity, setPlayerInteractivity
// Button functions: updateNextHoleButton, showHeaderButtons, showReplayButton
// Game state UI: onGameOver, onMatchOver, onGameStart, handleGameEnd, updateChart
// Utility functions: getPlayerColor, enableActionHistory

function updateGameDisplay() {
    // [FULL updateGameDisplay FUNCTION GOES HERE]
}

function actuallyUpdateUI() {
    // [FULL actuallyUpdateUI FUNCTION GOES HERE]
}

function updatePlayerGrids() {
    // [FULL updatePlayerGrids FUNCTION GOES HERE]
}

function updateGameAndRoundInfo() {
    // [FULL updateGameAndRoundInfo FUNCTION GOES HERE]
}

function updateLastActionPanel() {
    // [FULL updateLastActionPanel FUNCTION GOES HERE]
}

function updateInteractivity(isMyTurn) {
    // [FULL updateInteractivity FUNCTION GOES HERE]
}

function setPlayerInteractivity(isMyTurn) {
    // [FULL setPlayerInteractivity FUNCTION GOES HERE]
}

function updateNextHoleButton() {
    // [FULL updateNextHoleButton FUNCTION GOES HERE]
}

function showHeaderButtons(show) {
    // [FULL showHeaderButtons FUNCTION GOES HERE]
}

function showReplayButton(show) {
    // [FULL showReplayButton FUNCTION GOES HERE]
}

function onGameOver() {
    // [FULL onGameOver FUNCTION GOES HERE]
}

function onMatchOver() {
    // [FULL onMatchOver FUNCTION GOES HERE]
}

function onGameStart() {
    // [FULL onGameStart FUNCTION GOES HERE]
}

function handleGameEnd() {
    // [FULL handleGameEnd FUNCTION GOES HERE]
}

function updateChart(gameData) {
    // [FULL updateChart FUNCTION GOES HERE]
}

function getPlayerColor(playerIndex) {
    // [FULL getPlayerColor FUNCTION GOES HERE]
}

function enableActionHistory() {
    // [FULL enableActionHistory FUNCTION GOES HERE]
}

// ===== GAME ACTIONS MODULE =====
// Action functions: takeDiscard, drawFromDeck, executeAction, getAvailablePositions
// Card interaction functions: showDrawnCardArea, hideDrawnCardArea, flipDrawnCardOnGrid
// Animation functions: animateSnapToGrid, handleDropOnGrid
// Drop functions: onDrop

async function takeDiscard() {
    // [FULL takeDiscard FUNCTION GOES HERE]
}

async function drawFromDeck() {
    // [FULL drawFromDeck FUNCTION GOES HERE]
}

async function executeAction(position, actionType = null) {
    // [FULL executeAction FUNCTION GOES HERE]
}

function getAvailablePositions() {
    // [FULL getAvailablePositions FUNCTION GOES HERE]
}

function showDrawnCardArea(card) {
    // [FULL showDrawnCardArea FUNCTION GOES HERE]
}

function hideDrawnCardArea() {
    // [FULL hideDrawnCardArea FUNCTION GOES HERE]
}

function flipDrawnCardOnGrid(pos) {
    // [FULL flipDrawnCardOnGrid FUNCTION GOES HERE]
}

function animateSnapToGrid(cardElem, targetElem, callback) {
    // [FULL animateSnapToGrid FUNCTION GOES HERE]
}

function handleDropOnGrid(pos) {
    // [FULL handleDropOnGrid FUNCTION GOES HERE]
}

function onDrop(card, slot) {
    // [FULL onDrop FUNCTION GOES HERE]
}

// ===== GAME CARDS MODULE =====
// Card display functions: getCardDisplayContent

function getCardDisplayContent(card, faceDown = false) {
    // [FULL getCardDisplayContent FUNCTION GOES HERE]
}

// ===== GAME NOTIFICATIONS MODULE =====
// Notification functions: startHurryUpTimer, clearHurryUpTimer, showHurryUpGif, clearCelebration, clearHurryUpGif, showCelebrationGif

function startHurryUpTimer() {
    // [FULL startHurryUpTimer FUNCTION GOES HERE]
}

function clearHurryUpTimer() {
    // [FULL clearHurryUpTimer FUNCTION GOES HERE]
}

function showHurryUpGif() {
    // [FULL showHurryUpGif FUNCTION GOES HERE]
}

function clearCelebration() {
    // [FULL clearCelebration FUNCTION GOES HERE]
}

function clearHurryUpGif() {
    // [FULL clearHurryUpGif FUNCTION GOES HERE]
}

function showCelebrationGif() {
    // [FULL showCelebrationGif FUNCTION GOES HERE]
}

// ===== GAME PROBABILITIES MODULE =====
// Probability functions: updateProbabilitiesPanel, initializeCumulativeScoreChart, updateCumulativeScoreChart

function updateProbabilitiesPanel() {
    // [FULL updateProbabilitiesPanel FUNCTION GOES HERE]
}

function initializeCumulativeScoreChart() {
    // [FULL initializeCumulativeScoreChart FUNCTION GOES HERE]
}

function updateCumulativeScoreChart() {
    // [FULL updateCumulativeScoreChart FUNCTION GOES HERE]
}

// ===== CHATBOT CORE MODULE =====
// Core chatbot functions: initializeChatbot, sendChatMessage, addMessageToChat, shouldSendGif, getRelevantGif, extractSearchTerms
// Personality functions: changePersonality, getAllowedBotsForProactive, startPeriodicProactiveComments
// UI functions: clearChatUI, setJimNantzDefault, updateChatInputState, onMoveComplete, updateChatInputVisibility
// Proactive functions: requestProactiveComment, sendUserGifToChat, updateChatParticipantsHeader
// Typing functions: showBotTypingIndicator, removeBotTypingIndicator, shouldBotSendGif
// Utility functions: parseMentions, setupAutocomplete

function initializeChatbot() {
    // [FULL initializeChatbot FUNCTION GOES HERE]
}

async function sendChatMessage() {
    // [FULL sendChatMessage FUNCTION GOES HERE]
}

function addMessageToChat(sender, message, botName = null, gifOnly = false) {
    // [FULL addMessageToChat FUNCTION GOES HERE]
}

function shouldSendGif() {
    // [FULL shouldSendGif FUNCTION GOES HERE]
}

async function getRelevantGif(searchTerm, botName = null) {
    // [FULL getRelevantGif FUNCTION GOES HERE]
}

function extractSearchTerms(message, botName) {
    // [FULL extractSearchTerms FUNCTION GOES HERE]
}

async function changePersonality(personalityType) {
    // [FULL changePersonality FUNCTION GOES HERE]
}

function getAllowedBotsForProactive() {
    // [FULL getAllowedBotsForProactive FUNCTION GOES HERE]
}

function startPeriodicProactiveComments() {
    // [FULL startPeriodicProactiveComments FUNCTION GOES HERE]
}

function clearChatUI() {
    // [FULL clearChatUI FUNCTION GOES HERE]
}

function setJimNantzDefault() {
    // [FULL setJimNantzDefault FUNCTION GOES HERE]
}

function updateChatInputState() {
    // [FULL updateChatInputState FUNCTION GOES HERE]
}

function onMoveComplete(newGameState, lastAction) {
    // [FULL onMoveComplete FUNCTION GOES HERE]
}

function updateChatInputVisibility() {
    // [FULL updateChatInputVisibility FUNCTION GOES HERE]
}

async function requestProactiveComment(eventType = 'general') {
    // [FULL requestProactiveComment FUNCTION GOES HERE]
}

function sendUserGifToChat(gifUrl) {
    // [FULL sendUserGifToChat FUNCTION GOES HERE]
}

function updateChatParticipantsHeader() {
    // [FULL updateChatParticipantsHeader FUNCTION GOES HERE]
}

function showBotTypingIndicator(botName) {
    // [FULL showBotTypingIndicator FUNCTION GOES HERE]
}

function removeBotTypingIndicator(botName) {
    // [FULL removeBotTypingIndicator FUNCTION GOES HERE]
}

function shouldBotSendGif(botName) {
    // [FULL shouldBotSendGif FUNCTION GOES HERE]
}

function parseMentions(message) {
    // [FULL parseMentions FUNCTION GOES HERE]
}

function setupAutocomplete(chatInput) {
    // [FULL setupAutocomplete FUNCTION GOES HERE]
}

// ===== CHATBOT VOICE MODULE =====
// Voice functions: initializeVoiceStatus, loadVoices, toggleVoiceSystem, toggleActionHistory
// Voice system functions: initializeVoiceSystem, loadBrowserVoices, speakText, speakWithBrowser, speakWithBackend

function initializeVoiceStatus() {
    // [FULL initializeVoiceStatus FUNCTION GOES HERE]
}

function loadVoices() {
    // [FULL loadVoices FUNCTION GOES HERE]
}

function toggleVoiceSystem() {
    // [FULL toggleVoiceSystem FUNCTION GOES HERE]
}

function toggleActionHistory() {
    // [FULL toggleActionHistory FUNCTION GOES HERE]
}

function initializeVoiceSystem() {
    // [FULL initializeVoiceSystem FUNCTION GOES HERE]
}

function loadBrowserVoices() {
    // [FULL loadBrowserVoices FUNCTION GOES HERE]
}

function speakText(text, voiceName = null) {
    // [FULL speakText FUNCTION GOES HERE]
}

function speakWithBrowser(text, voiceName = null) {
    // [FULL speakWithBrowser FUNCTION GOES HERE]
}

function speakWithBackend(text, voiceName = null) {
    // [FULL speakWithBackend FUNCTION GOES HERE]
}

// ===== CHATBOT BOTS MODULE =====
// Bot management functions: updateCustomBotCount, getRandomUnusedTemplate, loadTemplateIntoSingleForm, loadTemplateIntoBotSection, createBotSection, updateBotNumbers

function updateCustomBotCount() {
    // [FULL updateCustomBotCount FUNCTION GOES HERE]
}

function getRandomUnusedTemplate() {
    // [FULL getRandomUnusedTemplate FUNCTION GOES HERE]
}

function loadTemplateIntoSingleForm() {
    // [FULL loadTemplateIntoSingleForm FUNCTION GOES HERE]
}

function loadTemplateIntoBotSection(botSection, botIndex) {
    // [FULL loadTemplateIntoBotSection FUNCTION GOES HERE]
}

function createBotSection(botNumber) {
    // [FULL createBotSection FUNCTION GOES HERE]
}

function updateBotNumbers() {
    // [FULL updateBotNumbers FUNCTION GOES HERE]
}

// ===== GAME UTILS MODULE =====
// Utility functions: playCardShuffleSound, playCardFlipSound, playGolfClap

function playCardShuffleSound() {
    // [FULL playCardShuffleSound FUNCTION GOES HERE]
}

function playCardFlipSound() {
    // [FULL playCardFlipSound FUNCTION GOES HERE]
}

function playGolfClap() {
    // [FULL playGolfClap FUNCTION GOES HERE]
}

// ===== EVENT LISTENERS AND INITIALIZATION =====
// DOM event listeners and initialization code

// Drawn card drag-and-drop logic
document.addEventListener('DOMContentLoaded', () => {
    // [FULL DOMContentLoaded EVENT LISTENER GOES HERE]
});

// Periodically refresh game state to catch AI moves
setInterval(() => {
    if (gameId && currentGameState && !currentGameState.game_over && !pollingPaused) {
        refreshGameState();
    }
}, 500); // Reduced from 1000ms to 500ms for more responsive AI turns

// Show timer on initial load
document.addEventListener('DOMContentLoaded', function() {
    showSetupViewTimer(cardVisibilityDuration);
    // Initialize the chart when page loads
    setTimeout(() => {
        initializeCumulativeScoreChart();
    }, 100); // Small delay to ensure DOM is ready
});

// When showing setup:
showHeaderButtons(false);

// When starting the game:
showHeaderButtons(true);

document.addEventListener('DOMContentLoaded', function() {
    showHeaderButtons(false);
});

showHeaderButtons(true);