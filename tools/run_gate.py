#!/usr/bin/env python3
"""Run the real evals and the real launch checker, then write the results the site replays.

Reads a checkout of agent-skills in ./agent-skills. Writes data/latest.json and data/history.json.
"""
import datetime
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS = os.path.join(ROOT, "agent-skills")
DATA = os.path.join(ROOT, "data")
HISTORY_CAP = 120


def load_checker():
    path = os.path.join(AS, "skills", "agent-launch-readiness", "scripts", "launch_check.py")
    spec = importlib.util.spec_from_file_location("launch_check", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_evals():
    started = time.time()
    p = subprocess.run([sys.executable, "evals/run_evals.py"], cwd=AS, capture_output=True, text=True)
    out = p.stdout + p.stderr
    passed = len(re.findall(r"^\[PASS\]", out, re.M))
    m = re.search(r"Failed: (\d+)", out)
    failed = int(m.group(1)) if m else (0 if p.returncode == 0 else 1)
    return {"passed": passed, "failed": failed, "seconds": round(time.time() - started, 1)}


def count_skills():
    n = 0
    for folder in ("skills", "tools-and-automation"):
        d = os.path.join(AS, folder)
        if os.path.isdir(d):
            n += len([x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))])
    return n


def commit_sha():
    p = subprocess.run(["git", "-C", AS, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() or "unknown"


def main():
    checker = load_checker()
    agents = []
    for path in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        with open(path) as f:
            spec = json.load(f)
        blocking, warnings, passed, total = checker.evaluate(spec)
        breaks = []
        if not blocking:
            import copy
            def mut(label, fn):
                m = copy.deepcopy(spec); fn(m)
                b, _, _, _ = checker.evaluate(m)
                for i, q, r in b:
                    breaks.append({"label": label, "id": i, "reason": r})
            mut("Remove the approval step", lambda m: m["actions"][0].__setitem__("human_approval", False))
            mut("Drop the owner", lambda m: m.__setitem__("owner", ""))
            mut("Lower the pass rate to 85%", lambda m: m["eval"].__setitem__("pass_rate", 85))
            mut("Remove the cost cap", lambda m: m.__setitem__("cost_cap_monthly", 0))
        agents.append({
            "breaks": breaks,
            "name": spec.get("name", "unnamed agent"),
            "purpose": spec.get("purpose", ""),
            "verdict": "GO" if not blocking else "NO-GO",
            "passed": passed,
            "total": total,
            "blocking": [{"id": i, "reason": r} for i, q, r in blocking],
            "warnings": warnings,
        })
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    evals = run_evals()
    sha = commit_sha()
    latest = {"generated_at": now, "agent_skills_commit": sha, "skills": count_skills(), "evals": evals, "agents": agents}
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "latest.json"), "w") as f:
        json.dump(latest, f, indent=2)
        f.write("\n")
    with open(os.path.join(DATA, "latest.js"), "w") as f:
        f.write("window.GATE_DATA=" + json.dumps(latest) + ";\n")
    hist_path = os.path.join(DATA, "history.json")
    try:
        with open(hist_path) as f:
            history = json.load(f)
    except (OSError, ValueError):
        history = []
    history.append({"t": now, "passed": evals["passed"], "failed": evals["failed"], "commit": sha})
    with open(hist_path, "w") as f:
        json.dump(history[-HISTORY_CAP:], f)
        f.write("\n")
    print(f"evals: {evals['passed']} passed, {evals['failed']} failed; agents: {[(a['name'], a['verdict']) for a in agents]}")
    sys.exit(0)


if __name__ == "__main__":
    main()
