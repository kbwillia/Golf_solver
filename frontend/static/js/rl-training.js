/**
 * RL training lab — multi-run history, compare charts, live sync, tooltips.
 */
(function () {
  const COLORS = {
    green: "#3d8b4f",
    greenLight: "#7bc48a",
    cream: "#f5f5f0",
    amber: "#d4a24c",
    blue: "#5b8fb9",
    rose: "#c46b6b",
    muted: "rgba(245,245,240,0.55)",
    grid: "rgba(245,245,240,0.12)",
    compare: ["#7bc48a", "#5b8fb9", "#d4a24c", "#c46b6b", "#c9a0dc"],
  };

  const POLL_MS = 8000;
  let charts = [];
  let pollTimer = null;
  let glossary = {};
  let selectedCompare = [];
  let lastPayload = null;
  let refreshAbort = null;

  function fmt(n, digits = 0) {
    if (n == null || Number.isNaN(n)) return "—";
    return Number(n).toLocaleString(undefined, {
      maximumFractionDigits: digits,
      minimumFractionDigits: digits,
    });
  }

  function pct(n) {
    if (n == null || Number.isNaN(n)) return "—";
    return (n * 100).toFixed(1) + "%";
  }

  function pct2(n) {
    if (n == null || Number.isNaN(n)) return "—";
    return (n * 100).toFixed(2) + "%";
  }

  function destroyCharts() {
    charts.forEach((c) => {
      try {
        c.destroy();
      } catch (_) {}
    });
    charts = [];
  }

  function baseOptions(yTitle, invertY, extra) {
    const opts = {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { color: COLORS.cream, boxWidth: 12, font: { family: "Arial", size: 11 } },
        },
        tooltip: { bodyFont: { family: "Arial" }, titleFont: { family: "Arial" } },
      },
      scales: {
        x: {
          title: { display: true, text: "Games", color: COLORS.muted, font: { family: "Arial", size: 11 } },
          ticks: { color: COLORS.muted, maxTicksLimit: 8 },
          grid: { color: COLORS.grid },
        },
        y: {
          reverse: !!invertY,
          title: { display: true, text: yTitle, color: COLORS.muted, font: { family: "Arial", size: 11 } },
          ticks: { color: COLORS.muted },
          grid: { color: COLORS.grid },
        },
      },
    };
    return extra ? Object.assign(opts, extra) : opts;
  }

  function makeChart(canvasId, config) {
    const el = document.getElementById(canvasId);
    if (!el) return null;
    try {
      const existing = typeof Chart !== "undefined" && Chart.getChart ? Chart.getChart(el) : null;
      if (existing) existing.destroy();
    } catch (_) {}
    const chart = new Chart(el, config);
    charts.push(chart);
    return chart;
  }

  function evBaselinePlugin(yValue) {
    return {
      id: "evBaseline",
      afterDraw(chart) {
        if (yValue == null) return;
        const {
          ctx,
          chartArea: { left, right },
          scales: { y },
        } = chart;
        if (!y) return;
        const yy = y.getPixelForValue(yValue);
        ctx.save();
        ctx.strokeStyle = "rgba(123,196,138,0.55)";
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(left, yy);
        ctx.lineTo(right, yy);
        ctx.stroke();
        ctx.fillStyle = "rgba(123,196,138,0.85)";
        ctx.font = "11px Arial";
        ctx.fillText("EV ~" + yValue, right - 52, yy - 4);
        ctx.restore();
      },
    };
  }

  function bootstrapPlugin(bootstrapGames) {
    return {
      id: "bootstrapBand",
      beforeDatasetsDraw(chart) {
        if (!bootstrapGames) return;
        const {
          ctx,
          chartArea: { top, bottom },
          scales: { x },
        } = chart;
        if (!x) return;
        const labels = chart.data.labels || [];
        // Labels are absolute game numbers — find the visible span inside bootstrap
        let iEnd = -1;
        for (let i = 0; i < labels.length; i++) {
          if (Number(labels[i]) <= Number(bootstrapGames)) iEnd = i;
          else break;
        }
        if (iEnd < 0) return; // bootstrap finished before this window
        const x0 = x.getPixelForValue(0);
        const x1 = x.getPixelForValue(iEnd);
        ctx.save();
        ctx.fillStyle = "rgba(212,162,76,0.12)";
        ctx.fillRect(x0, top, Math.max(0, x1 - x0), bottom - top);
        ctx.restore();
      },
    };
  }

  function wireTooltips() {
    const tipEl = document.getElementById("rlTooltip");
    document.body.addEventListener("mouseover", (e) => {
      const t = e.target.closest(".tip");
      if (!t || !tipEl) return;
      const key = t.getAttribute("data-tip");
      const text = glossary[key] || t.getAttribute("title");
      if (!text) return;
      tipEl.hidden = false;
      tipEl.textContent = text;
    });
    document.body.addEventListener("mousemove", (e) => {
      const tipEl = document.getElementById("rlTooltip");
      if (!tipEl || tipEl.hidden) return;
      tipEl.style.left = Math.min(window.innerWidth - 300, e.clientX + 14) + "px";
      tipEl.style.top = Math.min(window.innerHeight - 80, e.clientY + 14) + "px";
    });
    document.body.addEventListener("mouseout", (e) => {
      const t = e.target.closest(".tip");
      if (!t) return;
      const tipEl = document.getElementById("rlTooltip");
      if (tipEl) tipEl.hidden = true;
    });
  }

  function isDqnMode(mode) {
    const m = String(mode || "").toLowerCase();
    return m === "dqn" || m === "dqn_parallel" || m === "gpu";
  }

  function setModeVisibility(isDqn, { previewGpu = false } = {}) {
    const showDqnUi = !!(isDqn || previewGpu);
    document.querySelectorAll(".rl-dqn-only").forEach((el) => {
      el.hidden = !showDqnUi;
    });
    // Param-form CPU-only fields use .is-hidden via syncDeviceFields — do not
    // hide summary .rl-tabular-only / coverage off the GPU params toggle.
    // Keep tabular Q-hist + coverage visible for CPU data; hide only for real DQN runs
    document.querySelectorAll(".rl-tabular-only").forEach((el) => {
      el.hidden = !!isDqn;
    });
    const statesLabel = document.getElementById("statStatesLabel");
    const entriesLabel = document.getElementById("statEntriesLabel");
    const growthTitle = document.getElementById("growthTitle");
    const growthHint = document.getElementById("growthHint");
    if (isDqn) {
      if (statesLabel) {
        statesLabel.textContent = "Net params";
        statesLabel.setAttribute("data-tip", "network_params");
      }
      if (entriesLabel) {
        entriesLabel.textContent = "Net params";
        entriesLabel.setAttribute("data-tip", "network_params");
      }
      if (growthTitle) growthTitle.innerHTML = '<span class="tip" data-tip="network_params">Network params</span>';
      if (growthHint) growthHint.textContent = "Fixed weight count for the DQN — flat line is expected (not a growing Q-table).";
    } else {
      if (statesLabel) {
        statesLabel.textContent = "Q states";
        statesLabel.setAttribute("data-tip", "q_states");
      }
      if (entriesLabel) {
        entriesLabel.textContent = "SA pairs";
        entriesLabel.setAttribute("data-tip", "sa_pairs");
      }
      if (growthTitle) growthTitle.textContent = "Q-table growth";
      if (growthHint) growthHint.textContent = "";
    }
    // Empty-state hints when previewing GPU before a DQN run exists
    const lossHint = document.querySelector("#panelLoss .hint");
    const bufferTitle = document.querySelector("#panelBuffer h2");
    if (!isDqn && previewGpu) {
      if (lossHint) {
        lossHint.textContent = "No DQN run loaded yet — Start with Device=GPU (RunPod). Charts fill when the job syncs back.";
      }
    } else if (isDqn && lossHint) {
      const span = (lastPayload && lastPayload.learning && lastPayload.learning.series_span) || "";
      lossHint.textContent =
        span === "full"
          ? "Smooth L1 TD loss over the full run (downsampled). GPU / neural runs only."
          : "Smooth L1 TD loss (raw + MA). X-axis uses absolute game #s; full-run history appears on the next GPU job.";
    }
    void bufferTitle;
  }

  function setSummary(summary, trainMode, cpuCumulative) {
    const isDqn = isDqnMode(trainMode || summary.train_mode);
    const previewGpu =
      (document.querySelector('[name="train_device"]')?.value || "").toLowerCase() === "gpu";
    setModeVisibility(isDqn, { previewGpu });
    const cpu = cpuCumulative || {};
    const map = {
      statCpuGames: fmt(cpu.total_games != null ? cpu.total_games : summary.cpu_total_games),
      statCpuStates: fmt(
        cpu.q_states != null ? cpu.q_states : summary.final_states
      ),
      statCpuSa: fmt(cpu.sa_pairs != null ? cpu.sa_pairs : summary.final_entries),
      statCoverage:
        (cpu.completion_pct != null ? cpu.completion_pct : summary.completion_pct) != null
          ? pct2(cpu.completion_pct != null ? cpu.completion_pct : summary.completion_pct)
          : "—",
      statSparsity:
        (cpu.sparsity_index != null ? cpu.sparsity_index : summary.sparsity_index) != null
          ? Number(cpu.sparsity_index != null ? cpu.sparsity_index : summary.sparsity_index).toFixed(3)
          : "—",
      statGames: summary.games_total
        ? `${fmt(summary.games_played)} / ${fmt(summary.games_total)}`
        : fmt(summary.games_played),
      statWinRate: pct(summary.win_rate),
      statAvgScore: fmt(summary.avg_score, 2),
      statImprovement:
        summary.improvement == null
          ? "—"
          : (summary.improvement >= 0 ? "+" : "") + fmt(summary.improvement, 2),
      statStates: fmt(summary.final_states),
      statEntries: isDqn ? fmt(summary.final_states) : fmt(summary.final_entries),
      statEpsilon: summary.final_epsilon != null ? Number(summary.final_epsilon).toFixed(3) : "—",
      statLoss: summary.final_loss != null ? Number(summary.final_loss).toFixed(4) : "—",
      statBuffer: fmt(summary.final_buffer_size),
    };
    Object.entries(map).forEach(([id, val]) => {
      const node = document.getElementById(id);
      if (node) node.textContent = val;
    });
  }

  function setLiveStatus(live, syncErr) {
    const el = document.getElementById("rlLiveStatus");
    if (!el) return;
    el.classList.remove("is-idle", "is-error");
    if (syncErr) {
      el.classList.add("is-error");
      el.textContent = "Live sync error: " + syncErr;
      return;
    }
    if (!live) {
      el.classList.add("is-idle");
      el.textContent = "No active training · showing latest local / archived runs";
      return;
    }
    const anyCpu = !!(live.cpu_running || live.local);
    const anyGpu = !!(live.gpu_running);
    if (!anyCpu && !anyGpu && !live.running) {
      el.classList.add("is-idle");
      el.textContent = "No active training · showing latest local / archived runs";
      return;
    }
    const lanes = [];
    if (anyCpu) {
      const cs = live.cpu_summary || {};
      const parts = ["CPU local"];
      const played = cs.games_played ?? (anyGpu ? null : live.games_played);
      const total = cs.games_total ?? (anyGpu ? null : live.games_total);
      const pctVal = cs.pct ?? (anyGpu ? null : live.pct);
      if (played != null && total != null) parts.push(`${fmt(played)} / ${fmt(total)}`);
      else if (played != null) parts.push(`${fmt(played)} games`);
      if (pctVal != null) parts.push(`${pctVal}%`);
      lanes.push(parts.join(" · "));
    }
    if (anyGpu || (!anyCpu && live.running && !live.local)) {
      const gs = live.gpu_summary || (!anyCpu ? live : null);
      const parts = ["GPU RunPod"];
      if (gs) {
        if (gs.games_played != null && gs.games_total != null) {
          parts.push(`${fmt(gs.games_played)} / ${fmt(gs.games_total)}`);
        } else if (gs.games_played != null) {
          parts.push(`${fmt(gs.games_played)} games`);
        }
        if (gs.pct != null) parts.push(`${gs.pct}%`);
      }
      lanes.push(parts.join(" · "));
    }
    if (!lanes.length && live.running) {
      const parts = [live.local ? "CPU local" : "GPU RunPod"];
      if (live.games_played != null && live.games_total != null) {
        parts.push(`${fmt(live.games_played)} / ${fmt(live.games_total)} games`);
      }
      if (live.pct != null) parts.push(`${live.pct}%`);
      lanes.push(parts.join(" · "));
    }
    el.textContent = lanes.join("  |  ") + " · auto-refreshing";
  }

  function fmtDuration(sec) {
    if (sec == null || Number.isNaN(sec)) return "—";
    const s = Math.max(0, Number(sec));
    if (s < 60) return `${s.toFixed(s < 10 ? 1 : 0)}s`;
    const m = Math.floor(s / 60);
    const rem = Math.round(s % 60);
    if (m < 60) return `${m}m ${rem}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  }

  function renderRunsTable(runs, compareIds) {
    const body = document.getElementById("rlRunsBody");
    if (!body) return;
    selectedCompare = (compareIds || []).slice(0, 4);
    if (!runs || !runs.length) {
      body.innerHTML = `<tr><td colspan="11">No archived runs yet. Finish a job — CPU/GPU archive automatically.</td></tr>`;
      return;
    }
    body.innerHTML = runs
      .map((r) => {
        const s = r.summary || {};
        const p = r.params || {};
        const checked = selectedCompare.includes(r.id) ? "checked" : "";
        const disabled = !r.has_stats ? "disabled" : "";
        const device = (p.train_device || s.train_device || p.train_mode || "—").toString().toUpperCase();
        return `<tr>
          <td><input type="checkbox" class="run-check" data-id="${r.id}" ${checked} ${disabled}></td>
          <td>${r.label || r.id}</td>
          <td>${device}</td>
          <td>${fmt(s.games_played)}</td>
          <td title="${s.games_per_sec != null ? Number(s.games_per_sec).toFixed(1) + " games/s" : ""}">${fmtDuration(s.duration_sec)}</td>
          <td>${fmt(s.avg_score, 2)}</td>
          <td>${pct(s.win_rate)}</td>
          <td>${s.improvement == null ? "—" : fmt(s.improvement, 2)}</td>
          <td>${p.epsilon != null ? Number(p.epsilon).toFixed(2) : "—"}</td>
          <td>${fmt(p.n_bootstrap_games)}</td>
          <td>${p.opponent_type || "—"}</td>
        </tr>`;
      })
      .join("");
  }

  function selectedRunIds() {
    return Array.from(document.querySelectorAll(".run-check:checked"))
      .map((el) => el.getAttribute("data-id"))
      .slice(0, 4);
  }

  function renderCompare(compare, baselines) {
    const hint = document.getElementById("compareHint");
    if (!compare || !compare.length) {
      if (hint) hint.textContent = "No comparable runs with training_stats yet.";
      return;
    }
    if (hint) {
      hint.textContent = `Comparing ${compare.length} run(s). Amber band = bootstrap phase when known. Lower score is better.`;
    }
    const datasets = compare.map((run, i) => ({
      label: run.label || run.id,
      data: (run.series.games || []).map((g, idx) => ({
        x: g,
        y: (run.series.score_ma && run.series.score_ma[idx] != null
          ? run.series.score_ma[idx]
          : run.series.scores[idx]),
      })),
      borderColor: COLORS.compare[i % COLORS.compare.length],
      backgroundColor: "transparent",
      pointRadius: 0,
      borderWidth: 2,
      spanGaps: true,
    }));

    makeChart("chartCompare", {
      type: "line",
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        parsing: false,
        interaction: { mode: "nearest", intersect: false, axis: "x" },
        plugins: {
          legend: {
            labels: { color: COLORS.cream, boxWidth: 12, font: { family: "Arial", size: 11 } },
          },
          tooltip: { bodyFont: { family: "Arial" }, titleFont: { family: "Arial" } },
        },
        scales: {
          x: {
            type: "linear",
            title: { display: true, text: "Games", color: COLORS.muted },
            ticks: { color: COLORS.muted, maxTicksLimit: 8 },
            grid: { color: COLORS.grid },
          },
          y: {
            reverse: false,
            title: { display: true, text: "Score MA (lower better)", color: COLORS.muted },
            ticks: { color: COLORS.muted },
            grid: { color: COLORS.grid },
          },
        },
      },
      plugins: [evBaselinePlugin(baselines && baselines.ev_avg_score), bootstrapPlugin(compare[0] && compare[0].bootstrap_games)],
    });
  }

  function renderLearning(learning, baselines) {
    if (!learning || !learning.available) {
      document.getElementById("learningHint").textContent =
        "No training_stats.json yet — pull a finished run or wait for live checkpoints.";
      return;
    }
    const s = learning.series || {};
    const isDqn = isDqnMode(learning.train_mode);
    const previewGpu =
      (document.querySelector('[name="train_device"]')?.value || "").toLowerCase() === "gpu";
    setModeVisibility(isDqn, { previewGpu });
    const hasScores = Array.isArray(s.scores) && s.scores.length > 0;
    const bootstrap = learning.bootstrap_games;
    const windowHint = learning.games_ma_window;

    if (learning.from_live_progress) {
      document.getElementById("learningHint").textContent =
        "Live checkpoints from RunPod log (sparse). Full curves appear after stats are saved.";
    } else if (hasScores) {
      document.getElementById("learningHint").innerHTML =
        `${isDqn ? "GPU DQN · " : "CPU tabular · "}Lower is better. MA window ${windowHint || 20}. ` +
        `<span class="tip" data-tip="ev_baseline">EV baseline</span> dashed. ` +
        (bootstrap ? `Amber band = first ${bootstrap} <span class="tip" data-tip="bootstrap">bootstrap</span> games.` : "");
    }

    if (hasScores) {
      makeChart("chartLearning", {
        type: "line",
        data: {
          labels: s.games,
          datasets: [
            {
              label: "Agent score",
              data: s.scores,
              borderColor: "rgba(196,107,107,0.25)",
              pointRadius: 0,
              borderWidth: 1,
            },
            {
              label: "Agent MA",
              data: s.score_ma,
              borderColor: COLORS.rose,
              pointRadius: 0,
              borderWidth: 2,
              spanGaps: true,
            },
            {
              label: "Opponent MA",
              data: s.opponent_ma,
              borderColor: COLORS.blue,
              pointRadius: 0,
              borderWidth: 2,
              spanGaps: true,
              hidden: !(s.opponent_ma || []).some((v) => v != null),
            },
          ],
        },
        options: baseOptions("Score (lower better)", false),
        plugins: [evBaselinePlugin(baselines && baselines.ev_avg_score), bootstrapPlugin(bootstrap)],
      });
    }

    if (Array.isArray(s.rolling_win_rate) && s.rolling_win_rate.some((v) => v != null)) {
      makeChart("chartWinRate", {
        type: "line",
        data: {
          labels: s.games,
          datasets: [
            {
              label: "Rolling win rate",
              data: s.rolling_win_rate,
              borderColor: COLORS.greenLight,
              backgroundColor: "rgba(123,196,138,0.12)",
              fill: true,
              pointRadius: 0,
              borderWidth: 2,
              spanGaps: true,
            },
          ],
        },
        options: {
          ...baseOptions("Win rate", false),
          scales: {
            ...baseOptions("Win rate", false).scales,
            y: {
              ...baseOptions("Win rate", false).scales.y,
              min: 0,
              max: 1,
              ticks: {
                color: COLORS.muted,
                callback: (v) => (v * 100).toFixed(0) + "%",
              },
            },
          },
        },
      });
    }

    const hist = learning.score_histogram;
    const human = (lastPayload && lastPayload.human_demos) || null;
    const humanHist = human && human.score_histogram;
    const scoreHint = document.getElementById("scoreHistHint");
    if (scoreHint) {
      scoreHint.textContent = human && human.available
        ? "Training run vs your human demo holes (dual scale — training on left, human on right)."
        : "Training run scores (lower is better).";
    }
    if ((hist && hist.available) || (humanHist && humanHist.available)) {
      const maxCenter = Math.max(
        hist && hist.available ? Math.max(...(hist.bin_centers || [0])) : 0,
        humanHist && humanHist.available ? Math.max(...(humanHist.bin_centers || [0])) : 0
      );
      const labels = [];
      for (let i = 0; i <= maxCenter; i++) labels.push(String(i));
      const alignCounts = (src) => {
        const out = labels.map(() => 0);
        if (!src || !src.available) return out;
        (src.bin_centers || []).forEach((c, i) => {
          const idx = Number(c);
          if (idx >= 0 && idx < out.length) out[idx] = Number(src.counts[i] || 0);
        });
        return out;
      };
      const datasets = [];
      if (hist && hist.available) {
        datasets.push({
          label: "Training games",
          data: alignCounts(hist),
          backgroundColor: "rgba(91,143,185,0.55)",
          borderWidth: 0,
          yAxisID: "y",
        });
      }
      if (humanHist && humanHist.available) {
        datasets.push({
          label: "Human holes",
          data: alignCounts(humanHist),
          backgroundColor: "rgba(212,162,76,0.7)",
          borderWidth: 0,
          yAxisID: hist && hist.available ? "y1" : "y",
        });
      }
      makeChart("chartScoreHist", {
        type: "bar",
        data: { labels, datasets },
        options: {
          ...baseOptions("Count", false),
          plugins: {
            legend: {
              display: datasets.length > 1,
              labels: { color: COLORS.cream, boxWidth: 12, font: { family: "Arial", size: 11 } },
            },
          },
          scales: {
            x: {
              title: { display: true, text: "Score (0 = perfect)", color: COLORS.muted },
              ticks: { color: COLORS.muted, maxTicksLimit: 12, precision: 0 },
              grid: { color: COLORS.grid },
            },
            y: {
              title: {
                display: true,
                text: hist && hist.available ? "Training games" : "Human holes",
                color: COLORS.muted,
              },
              ticks: { color: COLORS.muted },
              grid: { color: COLORS.grid },
              beginAtZero: true,
            },
            y1: {
              position: "right",
              display: !!(hist && hist.available && humanHist && humanHist.available),
              title: { display: true, text: "Human holes", color: COLORS.muted },
              ticks: { color: COLORS.muted },
              grid: { drawOnChartArea: false },
              beginAtZero: true,
            },
          },
        },
      });
    }

    if (Array.isArray(s.qtable_states) && s.qtable_states.length) {
      const growthDatasets = [
        {
          label: isDqn ? "Network params" : "States",
          data: s.qtable_states,
          borderColor: COLORS.greenLight,
          pointRadius: 0,
          borderWidth: 2,
          yAxisID: "y",
        },
      ];
      if (!isDqn && Array.isArray(s.qtable_entries) && s.qtable_entries.length) {
        growthDatasets.push({
          label: "SA pairs",
          data: s.qtable_entries,
          borderColor: COLORS.amber,
          pointRadius: 0,
          borderWidth: 2,
          yAxisID: "y1",
        });
      }
      makeChart("chartGrowth", {
        type: "line",
        data: { labels: s.games, datasets: growthDatasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: {
              labels: { color: COLORS.cream, boxWidth: 12, font: { family: "Arial", size: 11 } },
            },
          },
          scales: {
            x: {
              title: { display: true, text: "Games", color: COLORS.muted },
              ticks: { color: COLORS.muted, maxTicksLimit: 8 },
              grid: { color: COLORS.grid },
            },
            y: {
              position: "left",
              title: { display: true, text: isDqn ? "Params" : "States", color: COLORS.muted },
              ticks: { color: COLORS.muted },
              grid: { color: COLORS.grid },
            },
            y1: {
              position: "right",
              display: growthDatasets.length > 1,
              title: { display: true, text: "SA pairs", color: COLORS.muted },
              ticks: { color: COLORS.muted },
              grid: { drawOnChartArea: false },
            },
          },
        },
      });
    }

    if (Array.isArray(s.epsilon) && s.epsilon.length) {
      makeChart("chartEpsilon", {
        type: "line",
        data: {
          labels: s.games,
          datasets: [
            {
              label: "Epsilon",
              data: s.epsilon,
              borderColor: COLORS.amber,
              backgroundColor: "rgba(212,162,76,0.15)",
              fill: true,
              pointRadius: 0,
              borderWidth: 2,
            },
          ],
        },
        options: baseOptions("Epsilon", false),
        plugins: [bootstrapPlugin(bootstrap)],
      });
    }

    if (isDqn && Array.isArray(s.loss) && s.loss.some((v) => v != null)) {
      const lossDatasets = [
        {
          label: "Loss",
          data: s.loss,
          borderColor: COLORS.rose,
          pointRadius: 0,
          borderWidth: 1.5,
          spanGaps: true,
        },
      ];
      if (Array.isArray(s.loss_ma) && s.loss_ma.length) {
        lossDatasets.push({
          label: "Loss MA",
          data: s.loss_ma,
          borderColor: COLORS.cream,
          pointRadius: 0,
          borderWidth: 2,
          spanGaps: true,
        });
      }
      makeChart("chartLoss", {
        type: "line",
        data: { labels: s.games, datasets: lossDatasets },
        options: {
          ...baseOptions("Loss", false),
          plugins: {
            legend: {
              labels: { color: COLORS.cream, boxWidth: 12, font: { family: "Arial", size: 11 } },
            },
          },
        },
        plugins: [bootstrapPlugin(bootstrap)],
      });
    }

    if (isDqn && Array.isArray(s.buffer_sizes) && s.buffer_sizes.length) {
      makeChart("chartBuffer", {
        type: "line",
        data: {
          labels: s.games,
          datasets: [
            {
              label: "Buffer size",
              data: s.buffer_sizes,
              borderColor: COLORS.blue,
              backgroundColor: "rgba(91,143,185,0.18)",
              fill: true,
              pointRadius: 0,
              borderWidth: 2,
            },
          ],
        },
        options: baseOptions("Transitions", false),
        plugins: [bootstrapPlugin(bootstrap)],
      });
    }
  }

  function renderActions(actions) {
    if (!actions || !actions.available) {
      document.getElementById("actionsHint").textContent = "No trajectory_train.csv found.";
      return;
    }
    document.getElementById("actionsHint").textContent =
      `${fmt(actions.steps)} steps · ${fmt(actions.games?.length)} sampled games.`;

    makeChart("chartActions", {
      type: "line",
      data: {
        labels: actions.games,
        datasets: [
          { label: "take_discard", data: actions.cumulative.take_discard, borderColor: COLORS.greenLight, pointRadius: 0, borderWidth: 2 },
          { label: "draw_keep", data: actions.cumulative.draw_keep, borderColor: COLORS.blue, pointRadius: 0, borderWidth: 2 },
          { label: "draw_flip", data: actions.cumulative.draw_flip, borderColor: COLORS.amber, pointRadius: 0, borderWidth: 2 },
        ],
      },
      options: baseOptions("Cumulative actions", false),
    });

    const totals = actions.totals || {};
    makeChart("chartActionMix", {
      type: "doughnut",
      data: {
        labels: ["take_discard", "draw_keep", "draw_flip"],
        datasets: [
          {
            data: [totals.take_discard || 0, totals.draw_keep || 0, totals.draw_flip || 0],
            backgroundColor: [COLORS.greenLight, COLORS.blue, COLORS.amber],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: COLORS.cream, boxWidth: 12, font: { family: "Arial", size: 11 } },
          },
        },
      },
    });
  }

  function renderQvalues(qvalues, learning) {
    const isDqn = learning && isDqnMode(learning.train_mode);
    if (isDqn) {
      const hint = document.getElementById("qHint");
      if (hint) hint.textContent = "DQN uses dqn_policy.pt (neural weights) — no tabular Q-value histogram.";
      return;
    }
    if (!qvalues || !qvalues.available) {
      document.getElementById("qHint").textContent = "No qtable_train.csv found.";
      return;
    }
    document.getElementById("qHint").textContent =
      `mean=${fmt(qvalues.mean, 3)}  std=${fmt(qvalues.std, 3)}  range=[${fmt(qvalues.min, 3)}, ${fmt(qvalues.max, 3)}]`;

    makeChart("chartQhist", {
      type: "bar",
      data: {
        labels: qvalues.bin_centers.map((c) => Number(c).toFixed(2)),
        datasets: [
          {
            label: "Frequency",
            data: qvalues.counts,
            backgroundColor: "rgba(123,196,138,0.65)",
            borderColor: COLORS.greenLight,
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            title: { display: true, text: "Q-value", color: COLORS.muted },
            ticks: { color: COLORS.muted, maxTicksLimit: 10, maxRotation: 0 },
            grid: { color: COLORS.grid },
          },
          y: {
            title: { display: true, text: "Count", color: COLORS.muted },
            ticks: { color: COLORS.muted },
            grid: { color: COLORS.grid },
          },
        },
      },
    });
  }

  function renderHumanDemos(human) {
    const hint = document.getElementById("humanDemoHint");
    const statsEl = document.getElementById("humanDemoStats");
    const histWrap = document.getElementById("humanHistWrap");
    if (!human || !human.available) {
      if (hint) {
        hint.textContent = human && human.error
          ? ("Human demos error: " + human.error + " — restart Flask (python run_app.py) if this persists.")
          : human && human.message
            ? human.message
            : "No finished human demo holes in Supabase yet. Play with demo recording on to collect them.";
      }
      if (statsEl) statsEl.hidden = true;
      return;
    }
    if (statsEl) statsEl.hidden = false;
    const set = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.textContent = v;
    };
    set("humanHoles", fmt(human.holes));
    set("humanAvg", fmt(human.avg_score, 1));
    set("humanWin", pct(human.win_rate));
    set("humanBest", fmt(human.best_score));
    if (hint) {
      const boot = human.used_in_bootstrap
        ? "During bootstrap: human action on state match/close, else EV."
        : "Not wired into bootstrap.";
      hint.textContent = `${fmt(human.steps)} recorded steps across ${fmt(human.holes)} holes. ${boot}`;
    }
    const hist = human.score_histogram;
    const hasHist =
      hist &&
      hist.available &&
      Array.isArray(hist.bin_centers) &&
      Array.isArray(hist.counts) &&
      hist.bin_centers.length > 0;
    if (histWrap) histWrap.hidden = !hasHist;
    if (hasHist) {
      makeChart("chartHumanHist", {
        type: "bar",
        data: {
          labels: hist.bin_centers.map((c) => String(Math.round(Number(c)))),
          datasets: [
            {
              label: "Human holes",
              data: hist.counts,
              backgroundColor: "rgba(212,162,76,0.7)",
              borderWidth: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              title: { display: true, text: "Score (0 = perfect)", color: COLORS.muted },
              ticks: { color: COLORS.muted, maxTicksLimit: 12, precision: 0 },
              grid: { color: COLORS.grid },
            },
            y: {
              title: { display: true, text: "Holes", color: COLORS.muted },
              ticks: { color: COLORS.muted, precision: 0 },
              grid: { color: COLORS.grid },
              beginAtZero: true,
            },
          },
        },
      });
    }

    const abr = human.action_by_round;
    const actionWrap = document.getElementById("humanActionWrap");
    const actionHint = document.getElementById("humanActionHint");
    const hasActions =
      abr &&
      abr.available &&
      Array.isArray(abr.rounds) &&
      abr.rounds.length > 0 &&
      abr.share;
    if (actionWrap) actionWrap.hidden = !hasActions;
    if (actionHint) {
      if (hasActions && abr.overall_avg_per_hole) {
        const o = abr.overall_avg_per_hole;
        actionHint.hidden = false;
        actionHint.textContent =
          `Avg / hole: take ${fmt(o.take_discard, 2)} · keep ${fmt(o.draw_keep, 2)} · flip ${fmt(o.draw_flip, 2)}` +
          (abr.holes_with_actions != null ? ` (${fmt(abr.holes_with_actions)} holes)` : "");
      } else {
        actionHint.hidden = true;
      }
    }
    if (hasActions) {
      const labels = abr.rounds.map((r) => "R" + String(r));
      const share = abr.share || {};
      makeChart("chartHumanActions", {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "take discard",
              data: share.take_discard || [],
              backgroundColor: "rgba(90, 158, 110, 0.85)",
              stack: "mix",
              borderWidth: 0,
            },
            {
              label: "draw keep",
              data: share.draw_keep || [],
              backgroundColor: "rgba(212, 162, 76, 0.85)",
              stack: "mix",
              borderWidth: 0,
            },
            {
              label: "draw flip",
              data: share.draw_flip || [],
              backgroundColor: "rgba(120, 150, 190, 0.85)",
              stack: "mix",
              borderWidth: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          plugins: {
            legend: {
              display: true,
              labels: { color: COLORS.muted, boxWidth: 10, font: { size: 11 } },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const v = Number(ctx.raw);
                  return `${ctx.dataset.label}: ${(v * 100).toFixed(1)}%`;
                },
              },
            },
          },
          scales: {
            x: {
              stacked: true,
              title: { display: true, text: "Round", color: COLORS.muted },
              ticks: { color: COLORS.muted },
              grid: { color: COLORS.grid },
            },
            y: {
              stacked: true,
              min: 0,
              max: 1,
              title: { display: true, text: "Share of actions", color: COLORS.muted },
              ticks: {
                color: COLORS.muted,
                callback: (v) => `${Math.round(Number(v) * 100)}%`,
              },
              grid: { color: COLORS.grid },
            },
          },
        },
      });
    }
  }

  function renderAll(data) {
    lastPayload = data;
    destroyCharts();
    glossary = data.glossary || glossary;
    const status = document.getElementById("rlStatus");
    if (!data.ok) {
      status.style.display = "";
      status.className = "rl-empty";
      status.textContent =
        data.error ||
        "No training output found. Start a run or pull from RunPod.";
      return;
    }
    status.style.display = "none";
    document.getElementById("rlContent").hidden = false;
    setSummary(
      data.summary || {},
      (data.learning && data.learning.train_mode) || (data.summary && data.summary.train_mode),
      data.cpu_cumulative
    );
    renderRunsTable(data.runs || [], data.compare_ids || selectedCompare);
    renderCompare(data.compare || [], data.baselines);
    renderHumanDemos(data.human_demos);
    renderLearning(data.learning, data.baselines);
    renderActions(data.actions);
    renderQvalues(data.qvalues, data.learning);
    setLiveStatus(
      data.live ||
        (data.sync && {
          running: data.sync.running,
          local: data.sync.local,
          cpu_running: data.sync.cpu_running,
          gpu_running: data.sync.gpu_running,
          cpu_summary: data.sync.cpu_summary,
          gpu_summary: data.sync.gpu_summary,
          train_device: data.sync.train_device,
          ...(data.sync.summary || {}),
        })
    );

    const meta = document.getElementById("rlMeta");
    if (meta) {
      const f = data.files || {};
      meta.textContent = `Sources — stats: ${f.training_stats ? "yes" : "no"}, trajectory: ${f.trajectory ? "yes" : "no"}, qtable: ${f.qtable ? "yes" : "no"}, runs: ${(data.runs || []).length} · updated ${new Date().toLocaleTimeString()}`;
    }
  }

  async function refresh({ sync } = { sync: true }) {
    const status = document.getElementById("rlStatus");
    const compareQs = selectedCompare.length ? `?compare=${selectedCompare.join(",")}` : "";
    if (refreshAbort) {
      try { refreshAbort.abort(); } catch (_) {}
    }
    refreshAbort = typeof AbortController !== "undefined" ? new AbortController() : null;
    const signal = refreshAbort ? refreshAbort.signal : undefined;
    try {
      let data = null;
      if (sync) {
        const syncRes = await fetch("/api/rl/sync" + compareQs, { signal });
        const syncType = (syncRes.headers.get("content-type") || "").toLowerCase();
        if (syncRes.ok && syncType.includes("application/json")) {
          data = await syncRes.json();
        }
      }
      if (!data) {
        const res = await fetch("/api/rl/training" + compareQs, { signal });
        const type = (res.headers.get("content-type") || "").toLowerCase();
        if (!res.ok || !type.includes("application/json")) {
          // Transient blip (e.g. Start/SSH blocking) — keep polling, don't panic
          throw new Error(`Temporary API hiccup (${res.status}). Retrying…`);
        }
        data = await res.json();
      }
      if (data.sync && data.sync.error && !data.ok) {
        setLiveStatus(null, data.sync.error);
      }
      renderAll(data);
      const running =
        !!(data.sync && (data.sync.running || data.sync.cpu_running || data.sync.gpu_running)) ||
        !!(data.live && data.live.running);
      schedulePoll(running || sync);
    } catch (err) {
      if (err && err.name === "AbortError") return;
      // Don't wipe a good live status line on a one-off failure
      const liveEl = document.getElementById("rlLiveStatus");
      const hadLive = liveEl && /(CPU local|GPU RunPod|Training live)/.test(liveEl.textContent || "");
      if (!hadLive) {
        setLiveStatus(null, err.message);
      }
      if (status && status.style.display !== "none") {
        status.className = "rl-error";
        status.textContent = "Failed to load training data: " + err.message;
      }
      schedulePoll(true);
    }
  }

  function schedulePoll(keepGoing) {
    if (pollTimer) clearTimeout(pollTimer);
    if (keepGoing) {
      pollTimer = setTimeout(() => refresh({ sync: true }), POLL_MS);
    }
  }

  function setControlMsg(text, kind) {
    const el = document.getElementById("rlControlMsg");
    if (!el) return;
    el.textContent = text || "";
    el.classList.remove("is-error", "is-ok");
    if (kind) el.classList.add(kind);
  }

  const DEVICE_PRESETS = {
    cpu: {
      num_workers: 1,
      chunk_size: 16,
      learning_rate: 0.05,
      n_bootstrap_games: 75,
      progress_report_interval: 50,
      num_games: 300,
      epsilon: 0.2,
      epsilon_decay_factor: 0.995,
      epsilon_decay_interval: 100,
      discount_factor: 0.9,
      use_imitation_learning: true,
      use_reward_shaping: true,
      opponent_type: "ev_ai",
      n_step: 3,
      replay_per_game: 4,
      exploration_beta: 0.5,
    },
    gpu: {
      num_workers: 8,
      learning_rate: 0.001,
      n_bootstrap_games: 400,
      progress_report_interval: 50,
      num_games: 1000,
      batch_size: 512,
      hidden_size: 128,
      train_steps_per_game: 8,
      epsilon: 0.2,
      epsilon_decay_factor: 0.995,
      epsilon_decay_interval: 100,
      discount_factor: 0.9,
      use_imitation_learning: true,
      use_reward_shaping: true,
      opponent_type: "ev_ai",
    },
  };

  let savedDevicePresets = {
    cpu: { ...DEVICE_PRESETS.cpu },
    gpu: { ...DEVICE_PRESETS.gpu },
  };

  function readParamsFromForm() {
    const form = document.getElementById("rlParamsForm");
    const fd = new FormData(form);
    const checked = (name, fallback = false) => {
      const el = form.querySelector(`[name="${name}"]`);
      return el ? !!el.checked : fallback;
    };
    const num = (name, fallback) => {
      const raw = fd.get(name);
      if (raw === null || raw === undefined || raw === "") return fallback;
      const n = Number(raw);
      return Number.isFinite(n) ? n : fallback;
    };
    const device = String(fd.get("train_device") || "cpu").toLowerCase() === "gpu" ? "gpu" : "cpu";
    const params = {
      train_device: device,
      num_workers: num("num_workers", device === "gpu" ? 8 : 1),
      chunk_size: num("chunk_size", 16),
      batch_size: num("batch_size", 512),
      hidden_size: num("hidden_size", 128),
      train_steps_per_game: num("train_steps_per_game", 8),
      num_games: num("num_games", device === "gpu" ? 1000 : 300),
      learning_rate: num("learning_rate", device === "gpu" ? 0.001 : 0.1),
      discount_factor: num("discount_factor", 0.9),
      epsilon: num("epsilon", 0.2),
      epsilon_decay_factor: num("epsilon_decay_factor", 0.995),
      epsilon_decay_interval: num("epsilon_decay_interval", 100),
      n_bootstrap_games: num("n_bootstrap_games", device === "gpu" ? 400 : 100),
      progress_report_interval: num("progress_report_interval", 50),
      opponent_type: String(fd.get("opponent_type") || "ev_ai"),
      use_imitation_learning: checked("use_imitation_learning", true),
      use_reward_shaping: checked("use_reward_shaping", true),
      shape_step: num("shape_step", 0.05),
      shape_pair: num("shape_pair", 1.5),
      shape_high_keep: num("shape_high_keep", -0.8),
      shape_low_keep: num("shape_low_keep", 0.3),
      shape_midhigh_keep: num("shape_midhigh_keep", -0.4),
      shape_flip: num("shape_flip", 0.1),
      exploration_beta: num("exploration_beta", 0.5),
      n_step: num("n_step", 3),
      replay_per_game: num("replay_per_game", 4),
      replay_capacity: num("replay_capacity", 2000),
    };
    // Keep the other device's preset when saving
    const snapshot = { ...params };
    delete snapshot.train_device;
    savedDevicePresets = {
      ...savedDevicePresets,
      [device]: { ...(savedDevicePresets[device] || {}), ...snapshot },
    };
    params.device_presets = savedDevicePresets;
    return params;
  }

  function selectedDevice() {
    return (document.querySelector('[name="train_device"]')?.value || "cpu").toLowerCase() === "gpu"
      ? "gpu"
      : "cpu";
  }

  function setDeviceToggleUI(device) {
    const key = device === "gpu" ? "gpu" : "cpu";
    const hidden = document.getElementById("trainDeviceSelect");
    if (hidden) hidden.value = key;
    document.querySelectorAll(".rl-device-btn").forEach((btn) => {
      btn.classList.toggle("is-active", btn.getAttribute("data-device") === key);
    });
    const hint = document.getElementById("devicePresetHint");
    if (hint) {
      hint.textContent =
        key === "gpu"
          ? "Editing GPU DQN params — saved separately from CPU"
          : "Editing CPU tabular Q params — saved separately from GPU";
    }
    const saveBtn = document.getElementById("btnSaveParams");
    if (saveBtn) saveBtn.textContent = `Save ${key.toUpperCase()} params`;
  }

  function updateStartStopLabels() {
    const device = selectedDevice();
    const label = device === "gpu" ? "GPU" : "CPU";
    const start = document.getElementById("btnStart");
    const stop = document.getElementById("btnStop");
    if (start) start.textContent = `Start ${label}`;
    if (stop) stop.textContent = `Stop ${label}`;
    setDeviceToggleUI(device);
  }

  function syncDeviceFields() {
    const form = document.getElementById("rlParamsForm");
    if (!form) return;
    const device = selectedDevice();
    const isGpu = device === "gpu";
    form.querySelectorAll(".rl-cpu-only").forEach((el) => el.classList.toggle("is-hidden", isGpu));
    form.querySelectorAll(".rl-gpu-only").forEach((el) => el.classList.toggle("is-hidden", !isGpu));
    const isDqn =
      lastPayload &&
      lastPayload.learning &&
      isDqnMode(lastPayload.learning.train_mode);
    setModeVisibility(!!isDqn, { previewGpu: isGpu });
    updateStartStopLabels();
  }

  function applyDevicePreset(device, { announce = false } = {}) {
    const form = document.getElementById("rlParamsForm");
    if (!form) return;
    const key = device === "gpu" ? "gpu" : "cpu";
    setDeviceToggleUI(key);
    const preset = {
      ...DEVICE_PRESETS[key],
      ...(savedDevicePresets[key] || {}),
    };
    Object.keys(preset).forEach((name) => {
      const input = form.querySelector(`[name="${name}"]`);
      if (!input) return;
      if (input.type === "checkbox") input.checked = !!preset[name];
      else input.value = preset[name];
    });
    const lr = form.querySelector('[name="learning_rate"]');
    if (lr) lr.step = key === "gpu" ? "0.001" : "0.01";
    syncDeviceFields();
    if (announce) {
      setControlMsg(
        key === "gpu"
          ? "Switched to GPU params (CPU set kept)"
          : "Switched to CPU params (GPU set kept)",
        "is-ok"
      );
    }
  }

  function switchDevice(next) {
    const nextKey = next === "gpu" ? "gpu" : "cpu";
    const current = selectedDevice();
    if (nextKey === current) return;
    // Stash in-progress edits into the current device's slot before swapping
    readParamsFromForm();
    applyDevicePreset(nextKey, { announce: true });
  }

  function fillParamsForm(params) {
    if (!params) return;
    const form = document.getElementById("rlParamsForm");
    if (!form) return;
    if (params.device_presets && typeof params.device_presets === "object") {
      savedDevicePresets = {
        cpu: { ...DEVICE_PRESETS.cpu, ...(params.device_presets.cpu || {}) },
        gpu: { ...DEVICE_PRESETS.gpu, ...(params.device_presets.gpu || {}) },
      };
    }
    const device = String(params.train_device || "cpu").toLowerCase() === "gpu" ? "gpu" : "cpu";
    // Prefer the saved device slot; fall back to flat params for first load
    const flat = { ...params };
    delete flat.device_presets;
    delete flat.train_device;
    savedDevicePresets[device] = {
      ...DEVICE_PRESETS[device],
      ...(savedDevicePresets[device] || {}),
      ...flat,
    };
    applyDevicePreset(device, { announce: false });
  }

  function setBusy(busy) {
    ["btnStart", "btnStop", "btnStopAll", "btnPull", "btnSaveParams", "btnArchive", "btnCompare"].forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = busy;
    });
  }

  async function loadControlStatus() {
    try {
      const res = await fetch("/api/rl/control/status");
      if (!res.ok) return;
      const data = await res.json();
      if (data.device_presets) {
        savedDevicePresets = {
          cpu: { ...DEVICE_PRESETS.cpu, ...(data.device_presets.cpu || {}) },
          gpu: { ...DEVICE_PRESETS.gpu, ...(data.device_presets.gpu || {}) },
        };
      } else if (data.defaults && data.defaults.device_presets) {
        savedDevicePresets = {
          cpu: { ...DEVICE_PRESETS.cpu, ...(data.defaults.device_presets.cpu || {}) },
          gpu: { ...DEVICE_PRESETS.gpu, ...(data.defaults.device_presets.gpu || {}) },
        };
      }
      // Prefer saved/UI params; only overlay remote_params while a remote job is active
      const mergedParams = {
        ...(data.defaults || {}),
        ...(data.params || {}),
        ...((data.running && !data.local && data.remote_params) || {}),
      };
      if (Object.keys(mergedParams).length) fillParamsForm(mergedParams);
      if (data.launch_error) {
        setControlMsg(data.launch_error, "is-error");
      } else if (data.launching) {
        setControlMsg("Launching neural DQN on RunPod…", "is-ok");
      } else if (data.running || data.cpu_running || data.gpu_running) {
        const parts = [];
        if (data.cpu_running || data.local) {
          const el = (data.cpu && data.cpu.elapsed) || (data.local && data.elapsed);
          parts.push(`CPU local${el ? " · " + el : ""}`);
        }
        if (data.gpu_running || data.launching) {
          const el = (data.gpu && data.gpu.elapsed) || (!data.local && data.elapsed);
          parts.push(`GPU RunPod${el ? " · " + el : ""}`);
        }
        if (!parts.length && data.running) {
          parts.push(data.local ? "CPU local" : "GPU RunPod");
        }
        setControlMsg(parts.join("  |  ") + " running", "is-ok");
      }
    } catch (_) {}
  }

  async function postControl(path, body) {
    setBusy(true);
    setControlMsg("Working…");
    try {
      const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : "{}",
      });
      const type = (res.headers.get("content-type") || "").toLowerCase();
      const data = type.includes("application/json")
        ? await res.json()
        : { ok: false, error: `Unexpected response (${res.status})` };
      if (!data.ok) setControlMsg(data.error || "Request failed", "is-error");
      else setControlMsg(data.message || "Done", "is-ok");
      await refresh({ sync: true });
      return data;
    } catch (err) {
      setControlMsg(err.message, "is-error");
      return null;
    } finally {
      setBusy(false);
    }
  }

  function wireControls() {
    document.getElementById("btnStart")?.addEventListener("click", () =>
      postControl("/api/rl/control/start", { params: readParamsFromForm() })
    );
    document.getElementById("btnStop")?.addEventListener("click", () =>
      postControl("/api/rl/control/stop", { device: selectedDevice() })
    );
    document.getElementById("btnStopAll")?.addEventListener("click", () =>
      postControl("/api/rl/control/stop", { device: "all" })
    );
    document.getElementById("btnPull")?.addEventListener("click", async () => {
      const data = await postControl("/api/rl/control/pull");
      if (data && data.ok) {
        const arch = data.archived && data.archived.id ? ` · archived ${data.archived.id}` : "";
        setControlMsg(`Pulled: ${(data.pulled || []).join(", ") || "nothing"}${arch}`, "is-ok");
      }
    });
    document.getElementById("btnSaveParams")?.addEventListener("click", async () => {
      setBusy(true);
      try {
        const res = await fetch("/api/rl/control/params", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ params: readParamsFromForm() }),
        });
        const data = await res.json();
        setControlMsg(
          data.ok
            ? `${selectedDevice().toUpperCase()} params saved (other device kept)`
            : data.error || "Save failed",
          data.ok ? "is-ok" : "is-error"
        );
      } catch (err) {
        setControlMsg(err.message, "is-error");
      } finally {
        setBusy(false);
      }
    });
    document.getElementById("btnArchive")?.addEventListener("click", async () => {
      setBusy(true);
      try {
        const res = await fetch("/api/rl/runs?archive=1");
        const data = await res.json();
        setControlMsg(
          data.ok ? `Archived ${data.archived?.id || "run"}` : data.error || "Archive failed",
          data.ok ? "is-ok" : "is-error"
        );
        await refresh({ sync: false });
      } catch (err) {
        setControlMsg(err.message, "is-error");
      } finally {
        setBusy(false);
      }
    });
    document.getElementById("btnCompare")?.addEventListener("click", async () => {
      selectedCompare = selectedRunIds();
      setControlMsg(`Comparing ${selectedCompare.length} run(s)…`, "is-ok");
      await refresh({ sync: false });
    });
    document.querySelectorAll(".rl-device-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchDevice(btn.getAttribute("data-device")));
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireTooltips();
    wireControls();
    syncDeviceFields();
    loadControlStatus();
    refresh({ sync: true });
  });
})();
