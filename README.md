# Support Inbox Triage Desk

A multi-agent customer-support triage system. A **Router** agent classifies each free-text message (category: `billing`, `technical` or `complaint`; urgency 1 to 3). **Only one** specialist agent (billing, technical support or complaints) then writes a draft reply, and a **Supervisor** agent decides whether to `ENVIAR` (send to the customer) or `ESCALAR` (escalate to a human or to Level 2 support). The evaluation script keeps a full audit log of every decision.

Course: Intelligent Agents and Multi-Agent Systems. Group 7.

**Group members:** António Santos (240000401), Afonso Coelho (240000372), Duarte Barros (240000330)

## Installation

Requirements:

- Python 3.12 (3.10 or newer should work).
- A free Google AI Studio API key (https://aistudio.google.com/apikey, no credit card needed). Optionally an Anthropic key, if you set `PROVIDER=anthropic`.

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

The model is set with `MODEL` in `.env` (we ran the experiments with `gemini-3.5-flash-lite`; check Google AI Studio for the model names currently available). Calls are spaced by `MIN_INTERVAL_S` seconds to respect the free-tier rate limits. Temporary errors (such as `503 UNAVAILABLE`) are retried automatically.

## Running

```bash
# 1. Interactive mode: type a customer message and see the result
python chat.py

# 2. Full evaluation on the 30 test messages (uses the API, several minutes)
python evaluate.py

# 3. Offline sanity tests (no API key, no cost)
python -m pytest -q
```

### Interactive mode (`chat.py`)

The program asks for the customer's e-mail (optional; the billing agent uses it to look up the customer in the mock database, for example `ana.ferreira@exemplo.pt`) and then waits for messages. Commands: `/email <address>` changes the customer and `/sair` quits.

### Evaluation (`evaluate.py`)

Runs the 30 test messages and compares the Router's output and the final decision with the ground truth. Optional: `python evaluate.py --dry-run --out results_dry` runs the same pipeline with a fake LLM to check the code only (these are **not** valid results).

## Expected output

**`chat.py`** prints, for each message: the Router's category and urgency, the specialist that ran, the draft reply, the Supervisor's decision and reason, and the number of model calls, tokens and time. Example:

```
Mensagem> A API está offline há 4 horas! Toda a minha empresa está parada!
1) ROTEADOR     -> categoria: technical | urgência: 3
2) ESPECIALISTA -> technical
   Minuta de resposta: ...
3) SUPERVISOR   -> ESCALAR: passar a uma pessoa
   motivo: urgency_3
```

**`evaluate.py`** prints one line per message and then a summary, and writes the results to `results/`:

- `metrics.json`: category, urgency and decision accuracy, escalation reasons, calls and tokens per message, latency.
- `confusion_category.png` and `confusion_urgency.png` (and `.csv` files): confusion matrices.
- `per_message.csv`, `errors.csv` and `audit_log.jsonl`: results per message, the mismatches and the full audit trail.

Summary of the run included in this repository (30 messages, model `gemini-3.5-flash-lite`):

| Metric | Value |
|---|---|
| Category accuracy | 0.967 |
| Category accuracy (ambiguous messages) | 0.875 |
| Urgency accuracy | 0.900 |
| Decision accuracy (`ENVIAR`/`ESCALAR`) | 0.833 |
| Specialists run per message | 1.0 |
| Model calls per message | 2.7 |
| Average latency | 19.3 s |

Results can vary slightly between runs, because the language model is not deterministic.

## Escalation rules (Supervisor)

1. Urgency 3: always escalated to a human.
2. Technical message not covered by the FAQ (`[not covered]`): escalated to Level 2 support.
3. Billing message from a customer whose account is `cancelled`: escalated to a human.
4. Otherwise a compliance check (regular expressions plus an LLM check) blocks drafts that admit fault or promise refunds, discounts or compensation.

## Repository structure

```
data/
  customers.json       mock billing database (8 fictional customers)
  faq.json             mock FAQ / troubleshooting base (10 articles; some topics deliberately missing)
  test_messages.json   30 test messages in European Portuguese with ground truth (category, urgency, decision)
src/
  llm.py               Gemini / Anthropic client wrappers + offline stub
  router.py            Agent 1 (classifier, JSON output only)
  specialists.py       Agents 2a / 2b / 2c (billing, technical, complaints)
  supervisor.py        Agent 3 (escalation rules + compliance check)
  pipeline.py          Orchestrator and audit record
  data.py              data loading and customer lookup
tests/test_offline.py  offline tests (stub LLM)
results/               output of evaluate.py
chat.py                interactive mode
evaluate.py            runs the dataset and computes the metrics
```

All customers, e-mails and data are fictional.
