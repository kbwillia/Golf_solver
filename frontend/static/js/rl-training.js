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
        const x0 = x.getPixelForValue(1);
        const x1 = x.getPixelForValue(bootstrapGames);
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

  function setModeVisibility(isDqn) {
    document.querySelectorAll(".rl-dqn-only").forEach((el) => {
      el.hidden = !isDqn;
    });
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
  }

  function setSummary(summary, trainMode) {
    const isDqn = String(trainMode || summary.train_mode || "").toLowerCase() === "dqn";
    setModeVisibility(isDqn);
    const map = {
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
    if (live && live.running) {
      const parts = ["Training live on RunPod"];
      if (live.games_played != null && live.games_total != null) {
        parts.push(`${fmt(live.games_played)} / ${fmt(live.games_total)} games`);
      }
      if (live.pct != null) parts.push(`${live.pct}%`);
      el.textContent = parts.join(" · ") + " · auto-refreshing";
    } else {
      el.classList.add("is-idle");
      el.textContent = "No active RunPod training · showing latest local / archived runs";
    }
  }

  function renderRunsTable(runs, compareIds) {
    const body = document.getElementById("rlRunsBody");
    if (!body) return;
    selectedCompare = (compareIds || []).slice(0, 4);
    if (!runs || !runs.length) {
      body.innerHTML = `<tr><td colspan="10">No archived runs yet. Finish a job and click Pull + archive.</td></tr>`;
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
    const isDqn = String(learning.train_mode || "").toLowerCase() === "dqn";
    setModeVisibility(isDqn);
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
    if (hist && hist.available) {
      makeChart("chartScoreHist", {
        type: "bar",
        data: {
          labels: hist.bin_centers.map((c) => String(Math.round(Number(c)))),
          datasets: [
            {
              label: "Games",
              data: hist.counts,
              backgroundColor: "rgba(91,143,185,0.55)",
              borderWidth: 0,
            },
          ],
        },
        options: {
          ...baseOptions("Count", false),
          plugins: { legend: { display: false } },
          scales: {
            x: {
              title: { display: true, text: "Score (0 = perfect)", color: COLORS.muted },
              ticks: { color: COLORS.muted, maxTicksLimit: 12, precision: 0 },
              grid: { color: COLORS.grid },
            },
            y: {
              title: { display: true, text: "Games", color: COLORS.muted },
              ticks: { color: COLORS.muted },
              grid: { color: COLORS.grid },
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
    const isDqn = learning && String(learning.train_mode || "").toLowerCase() === "dqn";
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
    setSummary(data.summary || {}, (data.learning && data.learning.train_mode) || (data.summary && data.summary.train_mode));
    renderRunsTable(data.runs || [], data.compare_ids || selectedCompare);
    renderCompare(data.compare || [], data.baselines);
    renderLearning(data.learning, data.baselines);
    renderActions(data.actions);
    renderQvalues(data.qvalues, data.learning);
    setLiveStatus(data.live || (data.sync && { running: data.sync.running, ...(data.sync.summary || {}) }));

    const meta = document.getElementById("rlMeta");
    if (meta) {
      const f = data.files || {};
      meta.textContent = `Sources — stats: ${f.training_stats ? "yes" : "no"}, trajectory: ${f.trajectory ? "yes" : "no"}, qtable: ${f.qtable ? "yes" : "no"}, runs: ${(data.runs || []).length} · updated ${new Date().toLocaleTimeString()}`;
    }
  }

  async function refresh({ sync } = { sync: true }) {
    const status = document.getElementById("rlStatus");
    const compareQs = selectedCompare.length ? `?compare=${selectedCompare.join(",")}` : "";
    try {
      let data = null;
      if (sync) {
        const syncRes = await fetch("/api/rl/sync" + compareQs);
        const syncType = (syncRes.headers.get("content-type") || "").toLowerCase();
        if (syncRes.ok && syncType.includes("application/json")) {
          data = await syncRes.json();
        }
      }
      if (!data) {
        const res = await fetch("/api/rl/training" + compareQs);
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
      const running = !!(data.live && data.live.running) || !!(data.sync && data.sync.running);
      schedulePoll(running || sync);
    } catch (err) {
      // Don't wipe a good live status line on a one-off failure
      const liveEl = document.getElementById("rlLiveStatus");
      const hadLive = liveEl && /Training live/.test(liveEl.textContent || "");
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
    return {
      train_device: device,
      num_workers: num("num_workers", 8),
      batch_size: num("batch_size", 256),
      hidden_size: num("hidden_size", 256),
      num_games: num("num_games", 5000),
      learning_rate: num("learning_rate", device === "gpu" ? 0.001 : 0.1),
      discount_factor: num("discount_factor", 0.9),
      epsilon: num("epsilon", 0.2),
      epsilon_decay_factor: num("epsilon_decay_factor", 0.995),
      epsilon_decay_interval: num("epsilon_decay_interval", 100),
      n_bootstrap_games: num("n_bootstrap_games", 1000),
      progress_report_interval: num("progress_report_interval", 250),
      opponent_type: String(fd.get("opponent_type") || "ev_ai"),
      use_imitation_learning: checked("use_imitation_learning", true),
      use_reward_shaping: checked("use_reward_shaping", true),
      shape_step: num("shape_step", 0.05),
      shape_pair: num("shape_pair", 1.5),
      shape_high_keep: num("shape_high_keep", -0.8),
      shape_low_keep: num("shape_low_keep", 0.3),
      shape_midhigh_keep: num("shape_midhigh_keep", -0.4),
      shape_flip: num("shape_flip", 0.1),
    };
  }

  function syncDeviceFields() {
    const form = document.getElementById("rlParamsForm");
    if (!form) return;
    const device = (form.querySelector('[name="train_device"]')?.value || "cpu").toLowerCase();
    const isGpu = device === "gpu";
    form.querySelectorAll(".rl-cpu-only").forEach((el) => el.classList.toggle("is-hidden", isGpu));
    form.querySelectorAll(".rl-gpu-only").forEach((el) => el.classList.toggle("is-hidden", !isGpu));
  }

  function fillParamsForm(params) {
    if (!params) return;
    const form = document.getElementById("rlParamsForm");
    Object.keys(params).forEach((key) => {
      const input = form.querySelector(`[name="${key}"]`);
      if (!input) return;
      if (input.type === "checkbox") input.checked = !!params[key];
      else input.value = params[key];
    });
    syncDeviceFields();
  }

  function setBusy(busy) {
    ["btnStart", "btnStop", "btnPull", "btnSaveParams", "btnArchive", "btnCompare"].forEach((id) => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = busy;
    });
  }

  async function loadControlStatus() {
    try {
      const res = await fetch("/api/rl/control/status");
      if (!res.ok) return;
      const data = await res.json();
      const mergedParams = { ...(data.defaults || {}), ...(data.params || {}), ...(data.remote_params || {}) };
      if (Object.keys(mergedParams).length) fillParamsForm(mergedParams);
      if (data.running) {
        const where = data.local ? "Local" : "RunPod";
        const device = (data.train_device || data.params?.train_device || "").toUpperCase();
        setControlMsg(
          `${where} job running${device ? " · " + device : ""}${data.elapsed ? " · " + data.elapsed : ""}`,
          "is-ok"
        );
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
    document.getElementById("btnStop")?.addEventListener("click", () => postControl("/api/rl/control/stop"));
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
        setControlMsg(data.ok ? "Params saved" : data.error || "Save failed", data.ok ? "is-ok" : "is-error");
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
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireTooltips();
    wireControls();
    document.getElementById("trainDeviceSelect")?.addEventListener("change", syncDeviceFields);
    syncDeviceFields();
    loadControlStatus();
    refresh({ sync: true });
  });
})();
