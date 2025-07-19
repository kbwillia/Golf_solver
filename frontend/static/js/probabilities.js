// ===== PROBABILITIES MODULE =====
// Contains all probability calculations, chart management, and statistics display

// Global variables for chart management
let cumulativeScoreChart = null;
let lastChartGameId = null;
let lastChartRound = null;
let lastChartUpdate = 0;
const CHART_UPDATE_THROTTLE = 100; // minimum 100ms between updates

// HTML Legend Plugin for Chart.js
const htmlLegendPlugin = {
    id: 'htmlLegend',
    afterUpdate(chart, args, options) {
        const items = chart.options.plugins.legend.labels.generateLabels(chart);
        const legendContainer = document.getElementById('customLegend');
        if (!legendContainer) return;

        legendContainer.innerHTML = '';
        items.forEach(item => {
            const legendItem = document.createElement('div');
            legendItem.style.cssText = `
                display: flex;
                align-items: center;
                margin: 2px 0;
                font-size: 0.8em;
                color: white;
            `;

            const colorBox = document.createElement('div');
            colorBox.style.cssText = `
                width: 12px;
                height: 12px;
                background-color: ${item.fillStyle};
                border: 1px solid ${item.strokeStyle};
                margin-right: 6px;
                border-radius: 2px;
            `;

            const text = document.createElement('span');
            text.textContent = item.text;

            legendItem.appendChild(colorBox);
            legendItem.appendChild(text);
            legendContainer.appendChild(legendItem);
        });
    }
};

// Update the probabilities panel with current game statistics
function updateProbabilitiesPanel() {
    const unknownCardsPanel = document.getElementById('unknownCardsPanel');
    const otherProbabilitiesPanel = document.getElementById('otherProbabilitiesPanel');

    // Hide probabilities if game is over
    if (currentGameState && currentGameState.game_over) {
        if (unknownCardsPanel) unknownCardsPanel.classList.add('hidden');
        // Only hide the content, not the column
        const panelBox = otherProbabilitiesPanel.querySelector('.probabilities-panel-box');
        if (panelBox) panelBox.classList.add('hidden');
        return;
    } else {
        if (unknownCardsPanel) unknownCardsPanel.classList.remove('hidden');
        const panelBox = otherProbabilitiesPanel.querySelector('.probabilities-panel-box');
        if (panelBox) panelBox.classList.remove('hidden');
    }

    if (!currentGameState || !currentGameState.probabilities) {
        if (unknownCardsPanel) unknownCardsPanel.innerHTML = '';
        if (otherProbabilitiesPanel) otherProbabilitiesPanel.innerHTML = '';
        return;
    }

    const probs = currentGameState.probabilities;

    // LEFT COLUMN: Unknown Cards Chart
    if (unknownCardsPanel && probs.deck_counts) {
        let unknownHtml = '<div class="probabilities-panel-box">';
        unknownHtml += '<h4 class="probabilities-title">Cards Left</h4>';

        // Desired order: J, A, 2-10, Q, K
        const order = ['J', 'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Q', 'K'];
        const maxCount = Math.max(...Object.values(probs.deck_counts));

        unknownHtml += '<table class="probabilities-table">';
        unknownHtml += '<thead><tr><th class="rank-header">Rank</th><th class="count-header">Count</th></tr></thead><tbody>';

        for (const rank of order) {
            if (probs.deck_counts[rank] !== undefined) {
                const count = probs.deck_counts[rank];
                const barWidth = maxCount > 0 ? (count / maxCount) * 100 : 0;

                // Color based on count
                let barColorClass;
                if (count === 0) {
                    barColorClass = 'card-bar-red';
                } else if (count === 1) {
                    barColorClass = 'card-bar-orange';
                } else if (count <= 2) {
                    barColorClass = 'card-bar-yellow';
                } else if (count <= 3) {
                    barColorClass = 'card-bar-teal';
                } else {
                    barColorClass = 'card-bar-green';
                }

                unknownHtml += `<tr><td class="rank-cell">${rank}</td>`;
                unknownHtml += `<td class="count-cell">`;
                unknownHtml += `<div class="card-count-bar-container">`;
                unknownHtml += `<div class="card-count-bar ${barColorClass}" style="width:${Math.max(barWidth, 8)}%;">`;
                unknownHtml += `<span class="card-count-text">${count}</span>`;
                unknownHtml += `</div>`;
                unknownHtml += `</div>`;
                unknownHtml += `</td></tr>`;
            }
        }
        unknownHtml += '</tbody></table></div>';
        unknownCardsPanel.innerHTML = unknownHtml;
    }

    // RIGHT COLUMN: Other Probabilities
    if (otherProbabilitiesPanel) {
        let otherHtml = '<div class="probabilities-panel-box">';
        otherHtml += '<h4 class="probabilities-title">Probabilities</h4>';

        // Expected Value Comparison (most important - show first)
        if (probs.expected_value_draw_vs_discard && currentGameState.current_turn === 0 && !currentGameState.game_over) {
            const ev = probs.expected_value_draw_vs_discard;
            otherHtml += '<div class="probabilities-bar">';
            otherHtml += '<div class="probabilities-bar-title">🎯 Strategery!</div>';
            otherHtml += `<div class="probabilities-bar-main"><b>${ev.recommendation}</b></div>`;
            otherHtml += `<div class="probabilities-bar-detail">Draw: ${ev.draw_expected_value > 0 ? '+' : ''}${ev.draw_expected_value} EV</div>`;
            otherHtml += `<div class="probabilities-bar-detail">Discard: ${ev.discard_expected_value > 0 ? '+' : ''}${ev.discard_expected_value} EV</div>`;
            otherHtml += `<div class="probabilities-bar-detail">Advantage: ${ev.draw_advantage > 0 ? '+' : ''}${ev.draw_advantage} EV</div>`;
            // if (ev.discard_card) {
            //     otherHtml += `<div class="probabilities-bar-detail">Discard: ${ev.discard_card} (score: ${ev.discard_score})</div>`;
            // }
            otherHtml += '</div>';
        }

        // Probability statistics
        if (probs.prob_draw_pair && probs.prob_draw_pair.length > 0) {
            otherHtml += `<div class="probabilities-stat">`;
            otherHtml += `<b>Prob. next card matches your grid:</b> <span class="probability-blue">${probs.prob_draw_pair[0]}</span>`;
            otherHtml += '</div>';
        }
        // Probability of drawing a card that improves your hand (for human)
        if (probs.prob_improve_hand && probs.prob_improve_hand.length > 0) {
            otherHtml += `<div class="probabilities-stat">`;
            otherHtml += `<b>Prob. next card improves your hand:</b> <span class="probability-blue">${probs.prob_improve_hand[0]}</span>`;
            otherHtml += '</div>';
        }

        // Average score of remaining cards in deck
        if (probs.average_deck_score !== undefined) {
            otherHtml += `<div class="probabilities-stat">`;
            otherHtml += `<b>Average score of remaining cards:</b> <span class="probability-blue">${probs.average_deck_score}</span>`;
            otherHtml += '</div>';
        }

        otherHtml += '</div>';
        otherProbabilitiesPanel.innerHTML = otherHtml;
    }

    // Hide probabilities panel box if game is over
    if (currentGameState && currentGameState.game_over) {
        // Hide the probabilities panel box
        const panelBox = otherProbabilitiesPanel.querySelector('.probabilities-panel-box');
        if (panelBox) {
            panelBox.classList.add('hidden');
        }
    } else {
        // Show it if not game over
        const panelBox = otherProbabilitiesPanel.querySelector('.probabilities-panel-box');
        if (panelBox) {
            panelBox.classList.remove('hidden');
        }
    }
}

// Initialize the cumulative score chart
function initializeCumulativeScoreChart() {
    const canvas = document.getElementById('cumulativeScoreChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart if it exists
    if (cumulativeScoreChart) {
        cumulativeScoreChart.destroy();
    }

    // Initialize with empty data
    const initialLabels = window.cumulativeScoreLabels || [];
    const initialDatasets = [];

    // Create datasets for current players if available
    if (currentGameState && currentGameState.players) {
        currentGameState.players.forEach((player, i) => {
            initialDatasets.push({
                label: player.name,
                data: window.cumulativeScoreHistory ? (window.cumulativeScoreHistory[i] || []) : [],
                borderColor: getPlayerColor(i),
                backgroundColor: getPlayerColor(i),
                borderWidth: 3, // Thicker lines
                fill: false,
                tension: 0.4, // Smooth curved lines
                pointRadius: 3,
                hoverRadius: 6
            });
        });
    }

    cumulativeScoreChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: initialLabels,
            datasets: initialDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false, // Hide default legend
                    position: 'left', // Changed from 'right' to 'left'
                    labels: {
                        boxWidth: 10,
                        padding: 4,
                        usePointStyle: true,
                        font: {
                            size: 7  // Reduced from 10 to 8
                        },
                        color: '#ffffff'
                    }
                },
                title: {
                    display: true,
                    text: 'Cumulative Scores by Round',
                    color: '#ffffff',
                    font: {
                        size: 12,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Game & Round',
                        color: '#ffffff',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        autoSkip: false,
                        color: '#ffffff',
                        font: {
                            size: 9
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.6)',
                        lineWidth: 1
                    },
                    border: {
                        color: '#ffffff',
                        width: 1
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Score',
                        color: '#ffffff',
                        font: {
                            size: 10
                        }
                    },
                    beginAtZero: true,
                    suggestedMin: 0,
                    suggestedMax: 20,
                    ticks: {
                        color: '#ffffff',
                        font: {
                            size: 9
                        },
                        stepSize: 4
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.6)',
                        lineWidth: 1
                    },
                    border: {
                        color: '#ffffff',
                        width: 1
                    }
                }
            },
            elements: {
                point: {
                    radius: 2,
                    hoverRadius: 4
                },
                line: {
                    spanGaps: false
                }
            }
        },
        plugins: [htmlLegendPlugin, {
            id: 'textOutline',
            afterDraw: (chart) => {
                const ctx = chart.ctx;
                const originalStrokeText = ctx.strokeText;
                const originalFillText = ctx.fillText;

                // Override fillText to add stroke
                ctx.fillText = function(text, x, y, maxWidth) {
                    // Save current state
                    ctx.save();

                    // Draw black outline
                    ctx.strokeStyle = '#000000';
                    ctx.lineWidth = 3;
                    ctx.lineJoin = 'round';
                    ctx.miterLimit = 2;
                    if (originalStrokeText) {
                        originalStrokeText.call(ctx, text, x, y, maxWidth);
                    }

                    // Draw white fill
                    ctx.fillStyle = '#ffffff';
                    originalFillText.call(ctx, text, x, y, maxWidth);

                    // Restore state
                    ctx.restore();
                };

                // Trigger a redraw
                Chart.helpers.each(chart.boxes, (box) => {
                    box.draw();
                });

                // Restore original methods
                ctx.fillText = originalFillText;
                ctx.strokeText = originalStrokeText;
            }
        }]
    });
}

// Update the cumulative score chart with new data
function updateCumulativeScoreChart() {
    const canvas = document.getElementById('cumulativeScoreChart');
    if (!canvas) {
        return;
    }

    // Throttle chart updates to prevent excessive rendering
    const now = Date.now();
    if (now - lastChartUpdate < CHART_UPDATE_THROTTLE) {
        return;
    }
    lastChartUpdate = now;

    const ctx = canvas.getContext('2d');

    // Initialize chart if it doesn't exist
    if (!cumulativeScoreChart) {
        initializeCumulativeScoreChart();
    }

    if (!currentGameState || !currentGameState.current_game) {
        return;
    }

    const gameId = currentGameState.current_game;

    // Build score history for each player, per round
    // Only reset history when starting a completely new match (not when advancing games)
    const matchId = `${currentGameState.num_games}_` +
        currentGameState.players.map(p => (p.name + '_' + (p.agent_type || '')).toLowerCase()).join('_');
    if (!window.cumulativeScoreHistory || !window.lastMatchId || window.lastMatchId !== matchId) {
        // Reset history for new match session (not just new game)
        window.cumulativeScoreHistory = [];
        for (let i = 0; i < currentGameState.players.length; i++) {
            window.cumulativeScoreHistory.push([]);
        }
        window.cumulativeScoreLabels = [];
        window.lastMatchId = matchId; // Track match with num_games and player names
        window.lastProcessedRound = 1; // Reset round tracking
        lastChartRound = null;
    }

    // Track current round progress
    const currentRoundKey = `G${currentGameState.current_game}R${currentGameState.round}`;

    // Use cumulative_scores first (which contains accumulated match totals), fallback to public_scores
    let roundScores = null;
    if (currentGameState.cumulative_scores && currentGameState.cumulative_scores.every(score => score !== null && score !== undefined)) {
        // Use cumulative scores first (contains accumulated match totals)
        roundScores = currentGameState.cumulative_scores;
        console.log('Using cumulative_scores:', roundScores);
    } else if (currentGameState.public_scores && currentGameState.public_scores.some(score => typeof score === 'number')) {
        // Fallback to public scores if cumulative not available
        roundScores = currentGameState.public_scores.map(score => typeof score === 'number' ? score : 0);
        console.log('Using public_scores:', roundScores);
    }

    console.log('Chart Debug - Game:', currentGameState.current_game, 'Round:', currentGameState.round, 'Scores:', roundScores, 'Game Over:', currentGameState.game_over);

    // Only proceed if we have valid scores to chart
    if (!roundScores) {
        console.log('No valid scores available for charting');
        return;
    }

    // Round completion detection: When scores exist but we're in a later round,
    // the scores represent the previous completed round
    let targetRound = currentGameState.round;
    let targetRoundKey = currentRoundKey;

    // Track the last round we processed
    if (!window.lastProcessedRound) {
        window.lastProcessedRound = 1;
    }

    // If we have scores and round has advanced, scores are for the previous round
    if (currentGameState.round > window.lastProcessedRound && roundScores.some(score => score > 0)) {
        targetRound = currentGameState.round - 1;
        targetRoundKey = `G${currentGameState.current_game}R${targetRound}`;
        console.log('=== ROUND COMPLETION DETECTED ===');
        console.log('Current round:', currentGameState.round, 'Recording scores for completed round:', targetRound);
        window.lastProcessedRound = currentGameState.round;
    }

    const isNewRound = !window.cumulativeScoreLabels.includes(targetRoundKey);
    let dataChanged = false;

    if (isNewRound) {
        // Add new data point for new round
        for (let i = 0; i < currentGameState.players.length; i++) {
            window.cumulativeScoreHistory[i].push(roundScores[i] || 0);
        }
        window.cumulativeScoreLabels.push(targetRoundKey);
        lastChartRound = targetRoundKey;
        dataChanged = true;
        console.log('=== ADDED NEW ROUND ===', targetRoundKey, 'with scores:', roundScores);
    } else {
        // Update existing data point if scores have changed
        const lastIndex = window.cumulativeScoreLabels.findIndex(label => label === targetRoundKey);
        if (lastIndex >= 0) {
            for (let i = 0; i < currentGameState.players.length; i++) {
                const newScore = roundScores[i] || 0;
                if (window.cumulativeScoreHistory[i][lastIndex] !== newScore) {
                    console.log('=== UPDATING SCORE ===', `Player ${i}:`, window.cumulativeScoreHistory[i][lastIndex], '→', newScore);
                    window.cumulativeScoreHistory[i][lastIndex] = newScore;
                    dataChanged = true;
                }
            }
        }
    }

    // Only update the chart if data actually changed
    if (!dataChanged) {
        return;
    }

    // Update chart data without recreating the chart
    if (cumulativeScoreChart && cumulativeScoreChart.data) {
        // Determine what data to show based on game progression
        let displayLabels = [...window.cumulativeScoreLabels];
        let displayHistory = window.cumulativeScoreHistory.map(playerHistory => [...playerHistory]);

        const maxRoundsToShow = 12; // or whatever number you want
        if (displayLabels.length > maxRoundsToShow) {
            displayLabels = displayLabels.slice(-maxRoundsToShow);
            displayHistory = displayHistory.map(playerHistory =>
                playerHistory.slice(-maxRoundsToShow)
            );
        }

        // Update chart with the determined data
        cumulativeScoreChart.data.labels = displayLabels;

        // Update datasets for active players only
        const activePlayerNames = currentGameState.players.map(p => p.name);
        cumulativeScoreChart.data.datasets = activePlayerNames.map((playerName, i) => ({
            label: playerName,
            data: displayHistory[i] || [],
            borderColor: getPlayerColor(i),
            backgroundColor: getPlayerColor(i),
            borderWidth: 3, // Thicker lines
            fill: false,
            tension: 0.4, // Smooth curved lines
            spanGaps: false // Don't connect lines across null values
        }));

        // Update the chart display
        cumulativeScoreChart.update('none'); // Use 'none' animation mode for smooth updates
    } else {
        // Fallback: recreate chart if something went wrong
        initializeCumulativeScoreChart();
    }

    console.log('Chart DEBUG:', {
        matchId,
        lastMatchId: window.lastMatchId,
        cumulativeScoreHistory: window.cumulativeScoreHistory,
        cumulativeScoreLabels: window.cumulativeScoreLabels
    });
}

// Update chart with game data (legacy function)
function updateChart(gameData) {
    // Only include players that are actually in the game
    const activePlayers = gameData.players.filter(player => player.isActive);

    // Create datasets only for active players
    const datasets = activePlayers.map(player => ({
        label: player.name,
        data: player.scores,
        backgroundColor: player.color,
        // ...
    }));
}

// Initialize chart when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the chart when page loads
    setTimeout(() => {
        initializeCumulativeScoreChart();
    }, 100); // Small delay to ensure DOM is ready
});

// Export functions globally for backward compatibility
window.updateProbabilitiesPanel = updateProbabilitiesPanel;
window.initializeCumulativeScoreChart = initializeCumulativeScoreChart;
window.updateCumulativeScoreChart = updateCumulativeScoreChart;
window.updateChart = updateChart;
