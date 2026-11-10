#!/usr/bin/env python3
"""Ledger: log model, effort and cost per step; summarize a run.
  ledger.py log --task ID --step NAME --model M --effort E --in TOKENS --out TOKENS --result PASS|FAIL [--file PATH]
  ledger.py summary [--task ID] [--file PATH]
Prices: USD per million tokens (input, output), as listed in the routing guide. Edit PRICES if list prices change."""
import argparse, json, os, time
PRICES = {"haiku": (0.10, 0.50), "sonnet": (2, 10), "opus": (4, 20), "fable": (8, 40)}
DEFAULT = ".claude/router-ledger.jsonl"
def cost(m, i, o):
    pi, po = PRICES[m]; return round(i / 1e6 * pi + o / 1e6 * po, 6)
ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
l = sp.add_parser("log")
for k in ("--task", "--step", "--model", "--effort", "--result"):
    l.add_argument(k, required=True)
l.add_argument("--in", dest="tin", type=int, default=0); l.add_argument("--out", dest="tout", type=int, default=0)
l.add_argument("--file", default=DEFAULT)
s = sp.add_parser("summary"); s.add_argument("--task"); s.add_argument("--file", default=DEFAULT)
a = ap.parse_args()
if a.cmd == "log":
    os.makedirs(os.path.dirname(a.file) or ".", exist_ok=True)
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "task": a.task, "step": a.step, "model": a.model, "effort": a.effort,
           "in": a.tin, "out": a.tout, "cost_usd": cost(a.model, a.tin, a.tout), "result": a.result}
    with open(a.file, "a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False))
else:
    rows = [json.loads(x) for x in open(a.file)] if os.path.exists(a.file) else []
    if a.task:
        rows = [r for r in rows if r["task"] == a.task]
    by = {}
    for r in rows:
        by[r["model"]] = by.get(r["model"], 0) + r["cost_usd"]
    print(json.dumps({"steps": len(rows), "total_usd": round(sum(by.values()), 4),
                      "by_model": {k: round(v, 4) for k, v in by.items()},
                      "fails": sum(r["result"] == "FAIL" for r in rows)}, ensure_ascii=False, indent=2))
