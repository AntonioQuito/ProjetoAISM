# Support Inbox Triage Desk

A multi-agent customer-support triage system. A **Router** agent classifies each free-text message (category: `billing`, `technical`, `complaint`; urgency 1-3), **only one** specialist agent (billing, technical support or complaints) then drafts a reply, and a **Supervisor** agent decides whether to `ENVIAR` (send) or `ESCALAR` (escalate to a human / Level 2). Every decision is logged for auditing.

Course: Intelligent Agents and Multi-Agent Systems. Group XX.

**Group members:** António Santos (240000401), Afonso Coelho (240000372), Duarte Barros (240000330)

## Installation

- Python 3.12 (3.10+ should work)
- A free Google AI Studio API key (https://aistudio.google.com/apikey, no credit card). Optionally an Anthropic key if you set `PROVIDER=anthropic`.

```bash
git clone <repository-url>
cd <repository-folder>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
# edit .env and paste your key:  GEMINI_API_KEY=...
```

`.env` is listed in `.gitignore`. Never commit your key.

## Running

```bash
# 1. Offline sanity tests (no API key, no cost)
python -m pytest -q

# 2. One message end to end
python run_demo.py --email ana.ferreira@exemplo.pt --text "Cobraram-me duas vezes o plano Pro este mês! Quero o dinheiro de volta."

# 3. Full evaluation on the 30 test messages (uses the API)
python evaluate.py

# Optional: plumbing check with a fake LLM (NOT valid results)
python evaluate.py --dry-run --out results_dry
```

The default model is a Gemini Flash model on the free tier (`MODEL` in `.env`; check AI Studio for the current name). Calls are spaced by `MIN_INTERVAL_S` seconds to respect free-tier rate limits, so a full evaluation takes several minutes. Set `PROVIDER=anthropic` to use Claude instead.

## Expected output

- `run_demo.py` prints a JSON record: routing, chosen specialist, draft, supervisor decision, token usage and latency.
- `evaluate.py` prints one line per message and a metrics summary, and writes to `results/`:
  - `metrics.json`: category / urgency / decision accuracy, per-class precision-recall-F1, escalation reasons, calls and tokens per message, latency
  - `confusion_category.png/.csv`, `confusion_urgency.png/.csv`
  - `per_message.csv`, `errors.csv`, `audit_log.jsonl` (full audit trail)

Results can vary slightly between runs and models.

## Repository structure

```
data/
  customers.json       mock billing database (8 fictional customers)
  faq.json             mock FAQ / troubleshooting base (10 articles; some topics deliberately missing)
  test_messages.json   30 test messages in PT-PT with ground truth (category, urgency, decision)
src/
  llm.py               Gemini / Anthropic client wrappers + offline stub
  router.py            Agent 1 (classifier, JSON only)
  specialists.py       Agents 2a/2b/2c
  supervisor.py        Agent 3 (escalation rules + compliance check)
  pipeline.py          Orchestrator and audit record
  data.py              data loading / customer lookup
tests/test_offline.py  offline tests
evaluate.py            runs the dataset and computes metrics
run_demo.py            single-message demo
```

All customers, emails and data are fictional.
