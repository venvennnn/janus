# JANUS

**The autonomous red-team agent for credit models.**
GOAI 2026 · Track 2 Boundless Agents · AI + Finance

> JANUS investigates whether a lending model rewards genuine creditworthiness — or merely the ability to manipulate what it sees.

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

The LLM never produces a number. It decides what to investigate. A deterministic engine records every figure against a re-executable run ID. A hallucinated statistic is structurally impossible.

Two human gates sit on the critical path: confirm mutability assumptions, then accept or reject each finding. Janus produces evidence. A person decides.

## The reference book

A 24,000-applicant synthetic portfolio with a documented causal mechanism (`janus/data_gen.py`). A 13-feature logistic scorecard. No protected attributes. The model passes a standard review: mid-0.60s AUC, a calibrated cutoff, roughly half the holdout approved.

What standard review misses, and what this run of the engine measured:

- A majority of declined applicants flip on cosmetic change. The flipped cohort defaults *worse* than the book.
- Rural residence is recoverable from model-visible features at ~0.995 AUC, carried by postal density. The model was never given it.
- Undocumented-income applicants are approved tens of points less often; realised default is effectively the same.
- Young self-employed risk is overstated. A high-leverage leaf is understated.
- The median integrity gap is two orders of magnitude: fake it in an afternoon, or earn it over months.
- For informal-income declines, documentation alone — Route C, ¥0 — crosses a large share of them, and those who cross are safer than the portfolio.

The planted mechanism: cash income unrecorded → recorded DTI inflates → DTI is the heaviest feature → exclusion follows measurement error, not risk. Independent products (NaijaLedger, GemLedger) attack the same absence from the supply side. They build the documentation. Janus measures what its absence costs.

**Figure discipline.** Only numbers from `python -m janus.run_audit` may appear in a deliverable. Two attack-cost medians exist and are not interchangeable.

## Demo

The site is static and ready for GitHub Pages. One applicant, three routes, one screen.

**[Open the demo](./docs/index.html)** after Pages is enabled, or serve it locally:

```bash
python -m http.server --directory docs 8080
```

Then visit `http://localhost:8080`.

### Deploy on GitHub

1. Push this repository.
2. **Settings → Pages**.
3. Either:
   - **GitHub Actions** (recommended). The workflow in `.github/workflows/pages.yml` publishes `docs/` on every push to `main`. First time: open the Actions tab, run **Deploy demo**, then set Pages source to GitHub Actions if prompted.
   - **Deploy from a branch**: Source = `main` (or this feature branch), folder = `/docs`.
4. The site will be at `https://<user>.github.io/janus/`.

All asset paths are relative. No build step. No API keys. Every displayed figure is bound to `docs/data/findings.json`, which is emitted by the engine.

Keyboard: `j` / `k` or arrows step the investigation; `1` `2` `3` apply routes on the desk.

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
