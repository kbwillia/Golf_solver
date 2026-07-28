import json
from pathlib import Path

base = Path(r"C:\Users\kbwil\Documents\Data_Projects\golf\Golf_solver\backend\RL\output\_remote_check")
d = json.loads((base / "training_stats.json").read_text(encoding="utf-8"))
prog = json.loads((base / "training_progress.json").read_text(encoding="utf-8"))
scores = d.get("scores") or []
n = len(scores)


def avg(a):
    return sum(a) / len(a) if a else None


print("games", n, "wins", d.get("wins"), "losses", d.get("losses"))
print("total_time_sec", round(float(d.get("total_time") or 0), 1))
print("games_per_sec", round(float(d.get("games_per_sec") or 0), 2))
print("workers", d.get("num_workers"), "mode", d.get("train_mode"))
print("overall_avg", round(avg(scores), 2))
print("first500_avg", round(avg(scores[:500]), 2))
print("late_bootstrap_2500_3000", round(avg(scores[2500:3000]), 2))
print("early_dqn_3000_3500", round(avg(scores[3000:3500]), 2))
print("last500_avg", round(avg(scores[-500:]), 2))
lv = [x for x in (d.get("loss_values") or []) if x is not None]
print("loss_first", round(lv[0], 3) if lv else None)
print("loss_last", round(lv[-1], 3) if lv else None)
print("loss_mean", round(sum(lv) / len(lv), 3) if lv else None)
cks = prog["checkpoints"]
for g in [500, 1000, 2000, 3000, 3500, 4000, 4500, 5000]:
    c = min(cks, key=lambda x: abs(x["game"] - g))
    loss = c.get("loss")
    loss_s = f"{loss:.3f}" if isinstance(loss, (int, float)) else str(loss)
    print(
        f"ckpt~{g}: game={c['game']} phase={c.get('phase')} "
        f"wr={c['win_rate']*100:.1f}% avg={c['avg_score']:.2f} loss={loss_s}"
    )
gps = float(d.get("games_per_sec") or 0)
if gps:
    print("usd_per_1k", round((0.22 / (gps * 3600)) * 1000, 5))
    print("usd_for_5k", round(0.22 * (float(d.get("total_time") or 0) / 3600), 4))
