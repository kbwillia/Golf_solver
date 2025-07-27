// ===== FAQ COMPONENT FOR SETUP SCREEN =====

console.log('FAQ.js loaded!');

const faqs = [
    {
        question: "How to play Golf?",
        answer: `
            <ul>
                <li>Each player gets 4 cards face down in a 2x2 grid</li>
                <li>On your turn, draw from deck or take the discard</li>
                <li>Replace one of your cards or flip a face-down card</li>
                <li>Goal: Get the lowest total score</li>
                <li>Face cards (J,Q,K) = 10, Aces = 1, Number cards = face value</li>
                <li>Game ends when someone knocks or all cards are face up</li>
            </ul>
        `
    },
    {
        question: "What are the different game modes?",
        answer: `
            <ul>
                <li><strong>1v1:</strong> You vs one AI opponent</li>
                <li><strong>1v3:</strong> You vs three AI opponents</li>
                <li><strong>Tournament:</strong> Play multiple holes (1, 3, 9, or 18)</li>
                <li><strong>Single Hole:</strong> Quick one-round games</li>
            </ul>
        `
    },
    {
        question: "How do AI opponents work?",
        answer: `
            <ul>
                <li>Each AI has a unique personality and playing style</li>
                <li>Difficulty levels: Easy, Medium, Hard</li>
                <li>AI makes strategic decisions based on their personality</li>
                <li>You can create custom AI bots with your own personalities</li>
                <li>AI opponents will chat and react during the game</li>
            </ul>
        `
    },
    {
        question: "What are the special features?",
        answer: `
            <ul>
                <li><strong>Voice Commentary:</strong> Jim Nantz provides play-by-play</li>
                <li><strong>Crowd Sound:</strong> Gets louder the closer you get to start button!</li>
                <li><strong>Double-click areas:</strong> Hide panels</li>
                <li><strong>Peek Feature:</strong> Look at your hidden cards (with cooldown)</li>
                <li><strong>Probability Hints:</strong> Get strategic advice</li>
                <li><strong>Custom Bots:</strong> Create your own AI opponents</li>
                <li><strong>Celebration Effects:</strong> Visual feedback for wins</li>
            </ul>
        `
    },
    {
        question: "How do I create a custom bot?",
        answer: `
            <ul>
                <li>Click "Create Custom Bot" button</li>
                <li>Choose a name and difficulty level</li>
                <li>Describe the bot's personality</li>
                <li>Upload an image (optional)</li>
                <li>Select a voice for the bot</li>
                <li>Save and the bot will appear in your selection</li>
            </ul>
        `
    },
    {
        question: "Tips for winning?",
        answer: `
            <ul>
                <li>Keep low cards (2-6) in your grid</li>
                <li>Use the peek feature strategically</li>
                <li>Watch the discard pile for good cards</li>
                <li>Consider knocking early if you have a good hand</li>
                <li>Pay attention to what cards other players are taking</li>
                <li>Use the probability hints to make informed decisions</li>
            </ul>
        `
    }
];

class FAQ {
    constructor(containerId) {
        console.log('FAQ constructor called with containerId:', containerId);
        this.container = document.getElementById(containerId);
        console.log('Container found:', this.container);
        this.isMinimized = true; // Start minimized
        this.openItems = new Set();
        this.init();
    }

    init() {
        if (!this.container) {
            console.error('FAQ container not found:', containerId);
            return;
        }

        console.log('Initializing FAQ, rendering...');
        this.render();
        this.setupEventListeners();
        console.log('FAQ initialization complete');
    }

    render() {
        console.log('Rendering FAQ...');
        const faqHTML = `
            <div class="faq-container ${this.isMinimized ? 'minimized' : ''}">
                <div class="faq-header" style="cursor: pointer;">
                    <h3>Frequently Asked Questions</h3>
                </div>
                ${!this.isMinimized ? `
                    <div class="faq-content">
                        ${faqs.map((faq, index) => `
                            <div class="faq-item">
                                <button class="faq-question" data-index="${index}">
                                    ${faq.question}
                                    <span class="faq-toggle">${this.openItems.has(index) ? '−' : '+'}</span>
                                </button>
                                <div class="faq-answer ${this.openItems.has(index) ? 'open' : ''}">
                                    ${faq.answer}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
        console.log('FAQ HTML:', faqHTML);
        this.container.innerHTML = faqHTML;
        console.log('FAQ rendered successfully');
    }

    setupEventListeners() {
        // Minimize/expand header click
        const header = this.container.querySelector('.faq-header');
        if (header) {
            header.addEventListener('click', () => {
                this.isMinimized = !this.isMinimized;
                this.render();
                this.setupEventListeners();
            });
        }

        // FAQ item toggles
        const questionButtons = this.container.querySelectorAll('.faq-question');
        questionButtons.forEach(button => {
            button.addEventListener('click', () => {
                const index = parseInt(button.dataset.index);
                if (this.openItems.has(index)) {
                    this.openItems.delete(index);
                } else {
                    this.openItems.add(index);
                }
                this.render();
                this.setupEventListeners();
            });
        });
    }
}

// Initialize FAQ when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing FAQ...');
    // Initialize FAQ in the setupLeftColumn
    new FAQ('setupLeftColumn');
});

// Also try initializing after a short delay in case DOM is not ready
setTimeout(() => {
    console.log('Timeout initialization of FAQ...');
    const container = document.getElementById('setupLeftColumn');
    if (container && !container.querySelector('.faq-container')) {
        console.log('Container found, initializing FAQ...');
        new FAQ('setupLeftColumn');
    } else {
        console.log('Container not found or FAQ already exists');
    }
}, 1000);

// Try initializing after window load to ensure all scripts are loaded
window.addEventListener('load', () => {
    console.log('Window loaded, checking FAQ...');
    const container = document.getElementById('setupLeftColumn');
    if (container && !container.querySelector('.faq-container')) {
        console.log('Container found on window load, initializing FAQ...');
        new FAQ('setupLeftColumn');
    } else {
        console.log('Container not found or FAQ already exists on window load');
    }
});