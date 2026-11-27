# Launch Gate, live

Four sample AI agents run through the 12 blocking launch checks from [agent-skills](https://github.com/amir-sohel-builds/agent-skills). The page replays the latest real results.

Nothing is mocked. `tools/run_gate.py` loads the actual checker, runs the actual eval suite, and writes `data/`. A GitHub Action does that every six hours and commits the result.

## How it works

1. `specs/` holds four made-up agent specs. Three are missing things a real launch review would catch. One is ready to ship.
2. `tools/run_gate.py` evaluates each spec with `launch_check.py` and runs `evals/run_evals.py`.
3. For the agent that passes, it also evaluates four single-change variants (remove the approval step, drop the owner, and so on) so the page can show what breaks.
4. `index.html` reads `data/latest.js`. No framework, no build step.

The checker is deterministic Python. No model is in the loop, so the same spec always gets the same verdict.

## Run it yourself

```
git clone https://github.com/amir-sohel-builds/agent-skills agent-skills
python3 -I tools/run_gate.py
python3 -m http.server
```

## Credit

The idea of showing a real system running live came from Shopify's BFCM live globe. This project shares none of its code or visuals.
