# JANUS

**The autonomous red-team agent for credit models.**

> JANUS investigates whether a lending model rewards genuine creditworthiness — or merely the ability to manipulate what it sees.

Website/ Demo Link: https://janus-z3zs.onrender.com/ 


This is a **credit model integrity** product. Fairness is one branch. The unifying question is simpler: does the model reward the thing it claims to measure?

```
                    MODEL INTEGRITY
        ┌─────────────────┼─────────────────┐
     GAMEABLE          EXCLUSION        RELIABILITY
   attack surface    proxy leakage     broken segments
   integrity gap     unexplained gap   miscalibration
                     recourse menu
```

## Why an agent

The integrity gap depends on a feature mutability model — for every feature, what it costs to fake, what it costs to genuinely move, how long that takes, and whether moving it reflects repayment capacity. Those judgments are lender-specific. Determining them is a language task: read a feature dictionary, absorb business context, reason about what a real applicant could do.

Without the agent, Janus works on exactly one model — the one whose lever table was hand-authored. With it, Janus works on any model a lender uploads.

Claude (Anthropic) does the language work: it reads the feature dictionary and business context, proposes the mutability table, then reads the finished battery and writes the investigation. The LLM never produces a number. A deterministic engine records every figure against a re-executable run ID. A hallucinated statistic is structurally impossible. Without `ANTHROPIC_API_KEY` the same loop runs on a heuristic stand-in so the demo still works.

Two human gates sit on the critical path: confirm mutability assumptions, then accept or reject each finding. Janus produces evidence. A person decides.

## The reference book

A 24,000-applicant synthetic portfolio with a documented causal mechanism (`janus/data_gen.py`). A 13-feature logistic scorecard. No protected attributes. The model passes a standard review: mid-0.60s AUC, a calibrated cutoff, roughly half the holdout approved.

What standard review misses, and what this run of the engine measured:

- A majority of declined applicants flip on cosmetic change. The flipped cohort defaults *worse* than the book.
- Rural residence is recoverable from model-visible features at ~0.995 AUC, carried by postal density. The model was never given it.
- Undocumented-income applicants are approved tens of points less often; realised default is effectively the same.
- Young self-employed risk is overstated. A high-leverage leaf is understated.
- The median integrity gap is two orders of magnitude: fake it in an afternoon, or earn it over months.
- For informal-income declines, documentation alone — Route C, $0 — crosses a large share of them, and those who cross are safer than the portfolio.

The planted mechanism: cash income unrecorded → recorded DTI inflates → DTI is the heaviest feature → exclusion follows measurement error, not risk. Independent products (NaijaLedger, GemLedger) attack the same absence from the supply side. They build the documentation. Janus measures what its absence costs.

**Figure discipline.** Only numbers from `python -m janus.run_audit` may appear in a deliverable. Two attack-cost medians exist and are not interchangeable.

## Demo

The recorded walkthrough is static and ready for GitHub Pages. One applicant, three routes, one screen.

Judges can also **upload a model** and get a review. GitHub Pages cannot run Python, so that path is a small FastAPI service (Render, no database). The site stays the paper essay; the service only inspects, searches, and returns the same findings package `run_audit.py` writes.

**[Open the demo](./docs/index.html)** after Pages is enabled, or serve it locally:

```bash
python -m http.server --directory docs 8080
```

Then visit `http://localhost:8080`. Reference mode is static and works on GitHub Pages with no backend.

### GitHub Pages demo

The `docs/` folder is the demo. No build step.

1. **Settings → Pages**
2. **Source:** Deploy from a branch
3. **Branch:** `main` · **Folder:** `/docs`
4. Save. The site is `https://<user>.github.io/janus/`

That serves Overview, Model Health, Attack Lab, and the rest of the recorded case. Live upload still needs the FastAPI service (Render, or `JANUS_SERVE_DOCS=1`).

Keyboard: `1` `2` `3` apply routes on the desk; `R` resets.

### Audit a model (Render)

Five inputs: a model with `predict_proba`, a holdout CSV with features plus `default`, an approval cutoff, a feature dictionary (strongly recommended), and optional business context. Claude proposes mutability. A person confirms. The engine runs the battery. Claude reads those figures and writes the memo. The holdout is dropped from memory after the run.

One-click fallback: **use the JANUS book** — the recorded A-7100 walkthrough, no upload. A sample pack lives in `sample/` (and `docs/sample/janus-sample.zip`) so someone without a bank model can still try the upload path.

```bash
python -m pip install -e ".[serve]"
uvicorn janus.server:app --host 0.0.0.0 --port 8000
```

`docs/js/config.js` points the static site at `http://localhost:8000` unless you are already on port 8000 or `*.onrender.com`.

**Deploy the review service on Render**

1. New Web Service → connect `venvennnn/janus`.
2. Runtime: Python. Build: `pip install -e ".[serve]"`. Start: `uvicorn janus.server:app --host 0.0.0.0 --port $PORT`.
3. Set `JANUS_SERVE_DOCS=1` so the paper site and the API share one origin (no CORS dance for judges).
4. Set `ANTHROPIC_API_KEY` to your Anthropic key. Optional: `ANTHROPIC_MODEL=claude-sonnet-4-5`.
5. Optional: copy `render.yaml`. Free tier sleeps; the first request after idle can wait.
6. If Pages still hosts the essay, set `window.JANUS_API` in `docs/js/config.js` to the Render URL.

Do not put the key in the repo. Add it only in the Render dashboard. After you add it, Manual Deploy → Deploy latest commit.

Do not upload PII. Pickle/joblib can execute code — only load a model you trust. Cap is 20,000 rows / 50 MB. Route C is a clean figure only when recorded and true income both exist; on real data it is directional, with that caveat left visible.

The recorded Pages demo does not need Render. It is still the `/docs` folder on `main`.

### Deploy on GitHub

The site is the `docs/` folder. No build. Do this once:

1. **Settings → Pages**
2. **Build and deployment → Source:** Deploy from a branch
3. **Branch:** `main` (or `cursor/janus-demo-website-3173` before merge) · **Folder:** `/docs`
4. Save. The site is `https://<user>.github.io/janus/`

That path does not use GitHub Actions and does not need Pages to be pre-created by a workflow.

**Optional — deploy via Actions** after the site exists:

1. **Settings → Pages → Source:** GitHub Actions  
   (`actions/configure-pages` cannot create the site with `GITHUB_TOKEN`. This click has to be yours.)
2. Actions → **Deploy demo** → Run workflow

The Actions workflow uses Node 24-native action versions (`checkout@v6`, `configure-pages@v6`, `upload-pages-artifact@v5`, `deploy-pages@v5`) and is `workflow_dispatch` only, so a missing Pages site will not fail every push.

All asset paths are relative. No build step. No API keys. Every displayed figure is bound to `docs/data/findings.json`, which is emitted by the engine.

Keyboard: `1` `2` `3` apply routes on the desk; `R` resets.

## Reproduce the figures

```bash
python -m pip install -e ".[dev]"
python -m janus.run_audit
python -m pytest
```

`run_audit` writes `results/audit.json` and `docs/data/findings.js`. The demo reads the latter.

## Architecture

```
model + holdout + feature dictionary + business context + audit objective
                        │
              AGENT LAYER (LLM / investigation loop)
              tool calls only — never computes a figure
                        │
              DETERMINISTIC ENGINE
              inspect · attack_surface · proxy_audit
              unexplained_exclusion · discover_segments
              integrity_gap · evidence_recourse · recourse_menu
                        │
              INVESTIGATION GRAPH + RUN LEDGER
```

Search is vectorised. Each greedy step stacks every remaining (applicant × lever) candidate and scores once.

## Boundaries

Janus does not make credit decisions. Attack recipes are defender findings — full detail to the model owner, aggregate only elsewhere, never to applicants. Recourse routes, including Route C, travel through the lender’s adverse-action process. They describe what the model responds to; they never promise approval. Demo data is synthetic. No real applicant data is used.

## License

MIT
