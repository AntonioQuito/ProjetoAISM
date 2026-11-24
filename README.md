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
python chat.py
```

O programa pede o email do cliente (opcional, usado pelo agente de faturação para consultar a base de dados) e depois fica à espera de mensagens. Escreve a frase do cliente e carrega em Enter. Comandos: `/email <endereço>` para mudar de cliente e `/sair` para terminar.

Para cada mensagem é mostrado: categoria e urgência (Roteador), o especialista executado, a minuta de resposta, a decisão do Supervisor (`ENVIAR` / `ESCALAR`), e o número de chamadas, tokens e tempo.

The default model is a Gemini Flash model on the free tier (`MODEL` in `.env`). Calls are spaced by `MIN_INTERVAL_S` seconds to respect free-tier rate limits. Set `PROVIDER=anthropic` to use Claude instead.

## Repository structure

```
data/
  customers.json       mock billing database (8 fictional customers)
  faq.json             mock FAQ / troubleshooting base (some topics deliberately missing)
src/
  llm.py               Gemini / Anthropic client wrappers
  router.py            Agent 1 (classifier, JSON only)
  specialists.py       Agents 2a/2b/2c
  supervisor.py        Agent 3 (escalation rules + compliance check)
  pipeline.py          Orchestrator
  data.py              data loading / customer lookup
chat.py                interactive mode (type a message, get the result)
```

All customers, emails and data are fictional.
