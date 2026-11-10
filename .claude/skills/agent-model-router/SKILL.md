---
name: agent-model-router
description: "Route every step of a Claude Code task to the right model and effort automatically, instead of running the whole session on one model. Classifies the request and its assets with a deterministic rule (no extra model call), sends cheap read-only work (classify, extract, search, read logs, summarize) to Haiku, scoped fixes and docs to Sonnet, complex work and debugging to Opus, and migrations, architecture and deep research to Fable, then validates the result and escalates only on a failed check (effort first, then model, max 3 cycles), logging model, effort and cost per step. Use this skill whenever the user works in Claude Code on a multi-step task, mentions model routing, choosing a model or effort per task, saving tokens or cost, subagents per tier, or says things like 'pick the best model', 'use the cheapest model that works', or 'اختر أفضل موديل للمهمة', even if they don't name the skill."
---

# Agent Model Router

A harness that reads the request and its assets, then picks the model and effort for every step.
The main session never switches model (switching with /model rewrites the prompt cache for the whole
conversation). Instead, each work item goes to a per-tier subagent: `worker-haiku`, `worker-sonnet`,
`worker-opus`, `worker-fable`, plus a `-high` variant of each for escalation.

## One-time setup

1. Install the subagents into the project (or `user` for all projects):
   `bash <skill-dir>/scripts/install_agents.sh project`
2. Run `/agents` and confirm the nine agents appear (8 workers + `router-validator`).
3. Optional: run `/tasks` after a routed step to confirm which model each subagent actually ran on.

## The five components

1. **Router**: classify the request and assets in code. Never ask a model to guess difficulty.
2. **Orchestrator**: you, in the main session. Write the goal and acceptance criteria for each work item.
3. **Worker**: the routed subagent implements the item.
4. **Validator**: `router-validator` runs read-only spec and standards checks. Returns PASS or FAIL.
5. **Ledger**: log model, effort and cost per step.

## Workflow for each request

### 1. Split into work items
Break the request into steps (recall files, plan, implement, read test logs, validate). Most tasks
mix cheap and hard steps; that is where routing saves money.

### 2. Route each item
Read the signals and call the router:

```bash
python <skill-dir>/scripts/route.py route --request "<the work item>" \
  [--images N] [--logs] [--large-assets] [--files N] [--repos N] [--computer-use] [--code-edit]
```

Set the flags from what you can see, not from how hard the task feels:
- `--images N`: screenshots or images attached.
- `--logs`: the item is reading logs or test output.
- `--large-assets`: a lot of source material to read.
- `--files N` / `--repos N`: files or repos the item will touch.
- `--code-edit`: the item must change code (guard: never on Haiku).
- `--kind`: override the detected kind when you know it (classify, extract, search, logs, summarize,
  scoped_fix, docs, feature, multi_pr, debugging, computer_use, migration, architecture, research).

The router prints JSON such as
`{"kind": "logs", "model": "haiku", "effort": "medium", "subagent": "worker-haiku", "reason": "..."}`.
When it falls through, it returns the default: **opus @ medium**.

### 3. Dispatch
Delegate the item to the returned `subagent` with the Agent/Task tool. Give it:
- the goal in one or two sentences,
- acceptance criteria as a short checklist,
- a check it can run itself (test command, lint, grep, expected output). This is escalation step 1.

### 4. Verify
Send the worker's result to `router-validator` with the same acceptance criteria.

### 5. Escalate only on FAIL
```bash
python <skill-dir>/scripts/route.py escalate --model <model> --effort <effort> --cycle <n>
```
Order: raise effort to high on the same model, then move one model up at medium.
Haiku → Sonnet → Opus → Fable. A PASS ends the loop. After three failed cycles the router returns
`blocked`: stop, record the reason in `TASK.md`, and tell the user what failed and what was tried.

### 6. Log every step
```bash
python <skill-dir>/scripts/ledger.py log --task <id> --step <name> --model <m> --effort <e> \
  --in <input_tokens> --out <output_tokens> --result PASS|FAIL
python <skill-dir>/scripts/ledger.py summary --task <id>
```
Use real token counts when the subagent reports them; otherwise log 0 and say the cost is unknown.

### 7. Report
End with a short table: step, model, effort, result, and the ledger total.

## Rules

- Route in code from the request and its assets. When unsure, start on Opus at medium.
- Keep the session on one model; send work to per-tier subagents.
- Escalate only on a failed check, bound the retries, and log model, effort and cost.
- Haiku workers are read-only (Edit/Write disallowed). Any code change goes to Sonnet or above.
- Do not route trivial one-line answers through subagents; answer them directly.

## Reference

- `references/routing-contract.yaml`: the full rule table, escalation policy, guards and list prices.
  Keep it and `scripts/route.py` in sync when you change a rule.
- Subagent frontmatter uses `model` (haiku, sonnet, opus, fable, a full model ID, or inherit) and
  `effort` (low, medium, high, xhigh, max; available levels depend on the model). Unknown frontmatter
  keys are ignored silently, so check `/tasks` if a worker seems to run on the wrong model.
