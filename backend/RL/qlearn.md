# Tabular Q-learning (CPU) — algorithm notes

This document describes the **CPU Q-table** trainer used by Golf Solver
(`parallel_train.py` + `QLearningAgent` in `agents.py`). GPU DQN is a separate path
and does **not** fill this table.

Live UI: `/rl` · params: `RL/output/ui_train_params.json` · artifacts under `RL/output/`.

## Pipeline overview

1. **Rollouts** — with `num_workers=1` (recommended for large tables), games run
   **in-process** (no Q snapshot I/O). Multi-worker mode writes `q_snapshot.pkl`
   once per chunk; workers cache by mtime.
2. **Main process** merges learning:
   - behavioral cloning during bootstrap (live + optional offline human BC batches)
   - **n-step Q-learning** with \(\max\) over **legal** actions
   - **trajectory replay** (losses prioritized)
   - **soft prior** on first visit to early-round `(s,a)` (hand-strength heuristic)
3. **I/O** — buffered trajectory CSV, downsampled stats, rare coverage scans,
   periodic Q checkpoints, optional perf telemetry (`train_perf.jsonl`).
4. Q-table saved to `RL/output/qtable_train.csv` and archived with runs.

## Soft prior (first-visit hand strength)

When a `(state, action)` is read for the first time and soft prior is **on**:

1. Parse visible ranks from the state key (`pub_` / `priv_`).
2. Average golf points (J=0, A=1, …, 10/Q/K=10).
3. Map to \(Q_0 \in [-\mathrm{scale}, +\mathrm{scale}]\) (default scale **5**):
   - strong low cards → positive prior  
   - junk high cards → negative prior  
   - ~5 pts/card → ~0
4. Only for **round ≤ `soft_prior_max_round`** (default **2**). Later rounds stay 0 until learned.
5. Learning / BC **overwrite** the value; this only biases the start and
   \(\max_{a'} Q(s',a')\) bootstrap into good/bad early hands.

**Why it helps:** early TD targets and next-state max-Q are not a flat zero table,
so credit assignment into good opening deals starts sooner. Within one state all
actions share the same hand prior (action ranking still needs samples / shaping / BC).

| Param | Default | Role |
|-------|---------|------|
| `use_soft_prior` | `true` | Enable / disable |
| `soft_prior_max_round` | `2` | Apply only for early rounds |
| `soft_prior_scale` | `5.0` | Clip \(|Q_0|\) |

UI: CPU-only checkbox + max round / scale fields (tooltips on `/rl`).

## Priority 1 — True Q-learning bootstrap

### Bug that was fixed

Updates used only the **next action taken** in the trajectory for \(\max Q(s')\).
That is closer to SARSA. Early good moves were punished when later exploration was bad.

### Correct target

\[
Q(s,a) \leftarrow Q(s,a) + \alpha\big(G - Q(s,a)\big)
\]

where the bootstrap term inside \(G\) (when used) is:

\[
\max_{a' \in \mathrm{Legal}(s')} Q(s', a')
\]

(via `get_q`, so soft prior can seed unseen next actions).

### Implementation

- Each trajectory step stores `legal_action_keys` at that state (`choose_action`).
- At bootstrap state \(s_{t+n}\), take \(\max\) over that step’s `legal_action_keys`.
- Terminal steps: no bootstrap (value \(0\)).

## n-step returns (\(n = 3\))

For step \(t\), with per-step rewards \(r_t\) (shaped + terminal on last step):

\[
G_t^{(n)} = \sum_{k=0}^{n-1} \gamma^k r_{t+k}
  + \mathbf{1}[\text{window did not hit terminal}]\;
    \gamma^n \max_{a'} Q(s_{t+n}, a')
\]

Default **`n_step = 3`**. Full window → Priority‑1 \(\max\); else sum through terminal only.

## Trajectory replay + loss priority

- Buffer capacity default **2000**; after each live game, sample **`replay_per_game`** (default **4**).
- Weights: win **1.0**, tie **1.5**, loss **3.0**.

## Visit-count exploration (Priority 3)

When not ε-exploring:

\[
a = \arg\max_a \Big( Q(s,a) + \frac{\beta}{\sqrt{N(s,a)+1}} \Big)
\]

Default **`exploration_beta = 0.5`**. Visits persist in CSV + snapshot.

## Human demos / bootstrap

| Mechanism | Role |
|-----------|------|
| **Live bootstrap** | First `n_bootstrap_games`: human demo on state match/close, else EV; BC toward 1.0 |
| **Offline BC** | Every `offline_human_bc_every` games, sample weighted demo steps (prefer wins / score ≤5; skip losses ≥12) |

Warm-table tip: keep bootstrap **~5–15%** of the run, not 75%+.

## ε schedule

- Start ε (default **0.2**), multiply by `epsilon_decay_factor` (default **0.995**) every `epsilon_decay_interval` games.
- Rule of thumb for interval: **~0.5–1% of total games**.
- Aim **~150–250 decays** per run for end ε roughly **0.06–0.10** (with factor 0.995).

## Rewards

### Terminal

| Outcome | Reward |
|---------|--------|
| Best score among players (any min-tie, e.g. 0–0) | **+10** |
| Score exactly 0 | **+10** |
| Score ≤ 5 | **+5** |
| Score ≤ 20 | **−4** |
| Else | **−10** |

### Win-rate counting

- Strict lower score → win; **0–0 → win**; other ties neither win nor loss (replay weight 1.5).

### Dense shaping (optional Phase A)

`reward_shaping` pair / high keep / low keep / flip / step. **Off** for unbiased solve.

## Coverage / sparsity

No finite full state space. Over **known** `(s,a)`:

| Metric | Meaning |
|--------|---------|
| `completion_pct` | Fraction with \(N \ge 5\) |
| `sparsity_index` | \(1 -\) completion |
| `mean_visits` | Average \(N(s,a)\) |

Full coverage scans run every `coverage_every_n_reports` progress reports (default **5**), not every report.

## Throughput / I/O (large table)

| Knob | Default | Purpose |
|------|---------|---------|
| `num_workers` | **1** (in-process) | Best GPS once Q is large on this machine |
| `chunk_size` | **16** | Games between progress checks |
| `traj_flush_every` | **100** | Buffer trajectory CSV appends |
| `q_checkpoint_every` | **50_000** | Periodic `qtable_train.csv` save |
| `stats_stride` / `stats_max_points` | **100** / **5000** | Downsampled series in memory / JSON |
| `coverage_every_n_reports` | **5** | Rare full coverage scans |
| `save_trajectories` | `true` | Set false for max speed on long runs |

**Perf telemetry** (next runs): `train_perf.jsonl` + `train_perf.json` — GPS, RSS, file sizes, timed I/O counters. Archived with runs.

Historical note: appending every game to a huge `trajectory_train.csv` + full stats/coverage each report caused a GPS cliff (~58 → ~16); buffering + rarer scans fix that.

## Q sharing (multi-worker only)

1. Main writes `q_snapshot.pkl` once per chunk.
2. Workers load/cache by mtime.
3. Prefer **workers=1 in-process** when the table is large.

## Suggested curriculum

1. **Cover:** shaping ON, soft prior ON, modest bootstrap (5–15%), ε decaying (~150–250 steps), β > 0.
2. **Solve:** shaping OFF, soft prior optional/off, little/no bootstrap, lower ε, β → 0.

## Key files

| File | Role |
|------|------|
| `backend/agents.py` | `QLearningAgent`: `get_q` / soft prior, n-step, visits, shaping |
| `backend/RL/parallel_train.py` | Train loop, replay, I/O knobs, checkpoints, offline BC |
| `backend/RL/train_perf.py` | Perf / metadata tracker |
| `backend/human_bootstrap.py` | Demo policy + offline BC pool |
| `backend/RL/output/qtable_train.csv` | Persisted Q (+ visits) |
| `backend/RL/output/train_perf.jsonl` | Per-report timing / memory samples |

## Defaults (trainer / UI CPU preset)

| Param | Default |
|-------|---------|
| `n_step` | 3 |
| `replay_capacity` | 2000 |
| `replay_per_game` | 4 |
| `exploration_beta` | 0.5 |
| `num_workers` | 1 |
| `chunk_size` | 16 |
| `learning_rate` | 0.05 |
| `use_soft_prior` | true |
| `soft_prior_max_round` | 2 |
| `soft_prior_scale` | 5.0 |
| `traj_flush_every` | 100 |
| `q_checkpoint_every` | 50000 |

## Not in this trainer (future)

- Eligibility traces TD(λ)
- Automatic Phase A/B shaping switch
- Shared-memory Q (stronger than snapshot file)
- Graceful Stop that saves Q before exit
