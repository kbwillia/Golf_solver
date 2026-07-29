# Tabular Q-learning (CPU) — algorithm notes

This document describes the **CPU Q-table** trainer used by Golf Solver
(`parallel_train.py` + `QLearningAgent` in `agents.py`). GPU DQN is a separate path
and does **not** fill this table.

## Pipeline overview

1. **Workers** play games using a **frozen** Q snapshot (ε-greedy or EV/human bootstrap).
2. **Main process** merges learning:
   - behavioral cloning during bootstrap
   - **n-step Q-learning** with \(\max\) over **legal** actions
   - **trajectory replay** (losses prioritized)
3. Q-table is saved to `RL/output/qtable_train.csv` and archived with runs.

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

### Implementation

- Each trajectory step stores `legal_action_keys` at that state (`choose_action`).
- At bootstrap state \(s_{t+n}\), take \(\max\) over that step’s `legal_action_keys`.
- Terminal steps: no bootstrap (value \(0\)).

## n-step returns (\(n = 3\))

### Formula

For step \(t\), with per-step rewards \(r_t\) (shaped + terminal on last step):

\[
G_t^{(n)} = \sum_{k=0}^{n-1} \gamma^k r_{t+k}
  + \mathbf{1}[\text{window did not hit terminal}]\;
    \gamma^n \max_{a'} Q(s_{t+n}, a')
\]

Default **`n_step = 3`**.

- If the episode ends inside the window, sum rewards through terminal and **do not** bootstrap.
- If the full window fits, bootstrap at \(s_{t+n}\) with Priority‑1 \(\max\).

### Relation to Priority 1

n-step chooses **how far** to look; Priority 1 chooses **which** Q values to use at the bootstrap state. Both apply together.

## Priority 5 — Trajectory replay + loss priority

### Buffer

- Stores recent full trajectories (default capacity **2000**).
- After each live game update, sample **`replay_per_game`** (default **4**) trajectories and run `train_on_trajectory` again (same n-step).

### Sampling weights

| Outcome | Relative weight |
|---------|-----------------|
| Win     | 1.0 |
| Tie     | 1.5 |
| Loss    | 3.0 |

Losing lines are replayed more often so rare mistakes get more Q updates without re-simulating.

### Params (UI JSON / CLI)

- `replay_capacity` (default 2000)
- `replay_per_game` (default 4; set `0` to disable)

## Priority 7 — Q sharing for parallel rollouts

### Old cost

Every game payload pickled the **entire** Q-table → \(N\) huge IPC copies per chunk as the table grew.

### Current approach

1. Main process writes **`RL/output/q_snapshot.pkl`** once per chunk.
2. Payloads only pass `q_snapshot_path` (+ scalars).
3. Each worker **caches** the loaded table by file **mtime** (reload only when the snapshot changes).

Workers still use a **frozen** snapshot for the chunk (stale vs main’s latest merges). That is intentional for throughput; learning happens on the main process.

### Workers tip

Keep ~**2** workers on a typical PC until games/sec is measured; more workers only help if rollouts dominate after snapshot sharing.

## Priority 3 — Visit-count exploration

When not ε-exploring, greedy action uses:

\[
a = \arg\max_a \Big( Q(s,a) + \frac{\beta}{\sqrt{N(s,a)+1}} \Big)
\]

- `N(s,a)` increments on every Q update (`train_on_trajectory`).
- Default **`exploration_beta = 0.5`**. Set `0` to disable.
- Visits persist in `qtable_train.csv` (4th column) and in `q_snapshot.pkl` so workers explore the same way.

## Coverage / sparsity index

There is **no known finite full state space**, so “100% complete” is not defined. Proxies over **known** `(s,a)` entries:

| Metric | Meaning |
|--------|---------|
| `completion_pct` | Fraction with \(N \ge 5\) (“well visited”) |
| `sparsity_index` | \(1 -\) completion (1 = all thin, 0 = all well visited) |
| `mean_visits` | Average \(N(s,a)\) |

Shown live as **Q coverage** / **Sparsity** on the RL page (CPU only). Also printed in training logs.

## Rewards

### Terminal (last step of a game)

| Outcome | Reward |
|---------|--------|
| Best score among players (includes any tie at the minimum, e.g. 0–0 or 5–5) | **+10** |
| Score exactly 0 (safety) | **+10** |
| Score ≤ 5 | **+5** |
| Score ≤ 20 | **−4** |
| Else | **−10** |

### Win-rate counting

- Strict lower score → win.
- **0–0 tie → win** (perfect hole shared).
- Other ties (e.g. 5–5) → neither win nor loss for the counter; replay treats them as ties (weight 1.5).

### Dense shaping (optional Phase A)

Per-step bonuses from `reward_shaping` (pair / high keep / low keep / flip / step baseline). Turn **off** for an unbiased “solve” phase.

## Other pieces still in the algo

| Piece | Role |
|-------|------|
| **EV / human bootstrap** | First `n_bootstrap_games`: expert actions + BC toward target 1.0 |
| **Reward shaping** | Dense per-step bonuses; turn off for unbiased “solve” phase |
| **ε-greedy** | Typed random exploration + `epsilon_decay_*` schedule |
| **Visit bonus β** | Count-based bonus on greedy actions (Priority 3) |
| **Terminal reward** | Win/score buckets added on last trajectory step |
| **State key** | `pub` / `priv` ranks, discard, drawn, round (no EV `adv_` bucket — bootstrap covers EV) |

## Suggested curriculum (ops, not code switches yet)

1. **Cover:** shaping ON, modest bootstrap, ε decaying, β > 0 — grow common cells.
2. **Solve:** shaping OFF, little/no bootstrap, lower ε, β → 0 — optimize real golf score vs EV.

## Key files

| File | Role |
|------|------|
| `backend/agents.py` | `QLearningAgent.train_on_trajectory`, legal keys, n-step, visits |
| `backend/RL/parallel_train.py` | Workers, snapshot, replay buffer, coverage |
| `backend/RL/output/qtable_train.csv` | Persisted table (+ visits column) |
| `backend/RL/output/q_snapshot.pkl` | Per-chunk frozen Q + visits for workers |

## Defaults (trainer)

| Param | Default |
|-------|---------|
| `n_step` | 3 |
| `replay_capacity` | 2000 |
| `replay_per_game` | 4 |
| `exploration_beta` | 0.5 |
| `num_workers` (UI preset) | 1 |
| `learning_rate` | 0.05 |

## Not in this trainer (future)

- Eligibility traces TD(λ)
- Automatic Phase A/B shaping switch
- Shared-memory Q (stronger than snapshot file)
