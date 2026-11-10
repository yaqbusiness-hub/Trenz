#!/usr/bin/env python3
"""Deterministic router: request + asset signals -> model tier, effort, subagent.
Usage:
  route.py route --request "text" [--kind KIND] [--images N] [--logs] [--large-assets]
                 [--files N] [--repos N] [--computer-use] [--code-edit]
  route.py escalate --model opus --effort medium [--cycle N]
Prints JSON. No model call is made: rules only.
"""
import argparse, json, re

TIERS = ["haiku", "sonnet", "opus", "fable"]
MAX_CYCLES = 3

# kind -> keywords (English + Arabic). First match in this order wins.
KINDS = [
    ("migration",     r"\bmigrat|\bport (to|from)|upgrade (the )?framework|ترحيل|نقل (النظام|القاعدة)|ترقية الإطار"),
    ("architecture",  r"architect|system design|redesign the|new (service|module) structure|معمارية|هيكلة النظام|تصميم النظام|بنية الكود"),
    ("research",      r"deep research|quant|analy[sz]e (the )?(market|data)|benchmark study|بحث معمق|تحليل كمي|دراسة شاملة"),
    ("computer_use",  r"computer use|click (on|the)|browser automation|استخدام الحاسوب|اضغط على الشاشة"),
    ("multi_pr",      r"multi[- ]?pr|across (several|multiple) (files|repos|prs)|عدة طلبات دمج|عدة مستودعات"),
    ("debugging",     r"\bdebug|stack ?trace|root cause|\bcrash|\bbug\b|not working|broken|تصحيح|ديبق|سبب الخطأ|يتعطل"),
    ("feature",       r"\b(add|implement|build) (a |an |the )?(new )?(feature|endpoint|component|page|module)|أضف ميزة|نفذ ميزة|ابن (صفحة|مكون)"),
    ("scoped_fix",    r"\bfix\b|rename|typo|\bbump\b|small change|one[- ]line|spec[- ]driven|أصلح|غير اسم|عدل سطر|تعديل بسيط"),
    ("docs",          r"\bdocs?\b|readme|docstring|changelog|repeated task|توثيق|اكتب وثيقة"),
    ("logs",          r"\blogs?\b|test output|سجلات|لوج|مخرجات الاختبار"),
    ("search",        r"\bsearch|\bfind\b|grep|locate|where is|ابحث|دور على|أين يوجد"),
    ("summarize",     r"summar|tl;?dr|لخص|تلخيص|ملخص|اختصر"),
    ("extract",       r"extract|parse|pull out|استخرج|استخراج"),
    ("classify",      r"classif|categori[sz]e|\btag\b|label|صنف|تصنيف|وسم"),
]
CHEAP = {"classify", "extract", "search", "logs", "summarize"}
SONNET = {"scoped_fix", "docs"}
OPUS = {"multi_pr", "debugging", "computer_use", "feature"}
HARD = {"migration", "architecture", "research"}

def detect_kind(text):
    t = text.lower()
    for kind, pat in KINDS:
        if re.search(pat, t):
            return kind
    return "unknown"

def route(kind, images=0, large=False, computer_use=False, code_edit=False, files=0, repos=0):
    reason = []
    if computer_use:
        kind = "computer_use"
    if kind in CHEAP and not code_edit:
        model, effort = "haiku", "medium"; reason.append(f"cheap kind '{kind}'")
    elif images or kind == "computer_use":
        model, effort = "opus", "medium"; reason.append("images or computer use")
    elif kind in HARD:
        model, effort = "fable", "medium"; reason.append(f"hard kind '{kind}'")
    elif kind in SONNET and not large and files <= 3 and repos <= 1:
        model, effort = "sonnet", "medium"; reason.append(f"scoped kind '{kind}', small assets")
    elif kind in OPUS:
        model, effort = "opus", "medium"; reason.append(f"complex kind '{kind}'")
    else:
        model, effort = "opus", "medium"; reason.append("not sure yet -> default opus @ medium")
    if repos > 1 and model in ("haiku", "sonnet"):
        model = "opus"; reason.append("touches several repos")
    if code_edit and model == "haiku":
        model = "sonnet"; reason.append("guard: code_edits never on haiku")
    return model, effort, kind, "; ".join(reason)

def subagent(model, effort):
    return f"worker-{model}" + ("-high" if effort == "high" else "")

def escalate(model, effort, cycle):
    if cycle >= MAX_CYCLES:
        return {"status": "blocked", "reason": f"{MAX_CYCLES} failed cycles"}
    if effort != "high":
        return {"status": "retry", "model": model, "effort": "high", "subagent": subagent(model, "high"), "step": "raise effort"}
    i = TIERS.index(model)
    if i == len(TIERS) - 1:
        return {"status": "blocked", "reason": "top tier at high effort already failed"}
    nxt = TIERS[i + 1]
    return {"status": "retry", "model": nxt, "effort": "medium", "subagent": subagent(nxt, "medium"), "step": "move one model up"}

def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("route")
    r.add_argument("--request", required=True); r.add_argument("--kind")
    r.add_argument("--images", type=int, default=0); r.add_argument("--logs", action="store_true")
    r.add_argument("--large-assets", action="store_true"); r.add_argument("--files", type=int, default=0)
    r.add_argument("--repos", type=int, default=0); r.add_argument("--computer-use", action="store_true")
    r.add_argument("--code-edit", action="store_true")
    e = sp.add_parser("escalate"); e.add_argument("--model", required=True, choices=TIERS)
    e.add_argument("--effort", required=True); e.add_argument("--cycle", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "route":
        kind = a.kind or detect_kind(a.request)
        if a.logs and kind == "unknown":
            kind = "logs"
        m, eff, kind, why = route(kind, a.images, a.large_assets, a.computer_use, a.code_edit, a.files, a.repos)
        print(json.dumps({"kind": kind, "model": m, "effort": eff, "subagent": subagent(m, eff), "reason": why}, ensure_ascii=False))
    else:
        print(json.dumps(escalate(a.model, a.effort, a.cycle), ensure_ascii=False))

if __name__ == "__main__":
    main()
