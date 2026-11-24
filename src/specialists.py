"""Agent 2: the three specialists. Exactly one is executed per message."""
import json
from .llm import parse_json

COMMON = ("Write the reply draft in European Portuguese (PT-PT), polite and concise, "
          "signed 'Equipa de Suporte'. Write ONLY in Portuguese: no English words. Output ONLY a JSON object. ")

BILLING_SYSTEM = COMMON + """You are the billing specialist. You receive the customer's record from the billing database (JSON) and the customer's message.
Write a draft that answers the question citing the REAL amounts, dates, invoice and payment IDs from the record. Never invent data. Write for a customer, not for engineers: never show internal codes or raw field values (like 'card_mastercard_5521' or 'failed_card_declined'); say them in plain words (e.g. 'cartão Mastercard terminado em 5521', 'o cartão foi recusado'). Invoice and payment IDs may be cited. If the record does not contain what is needed (or no record was found), say so and ask for the missing information. If the record shows a problem (e.g. duplicate payment), describe it factually and say the case will be reviewed by the billing team; do not promise any outcome.
Output: {"draft": "..."}"""

TECHNICAL_SYSTEM = COMMON + """You are the technical-support specialist. You receive the FAQ / troubleshooting knowledge base (JSON) and the customer's message.
If the problem is covered by one or more FAQ articles, write a clear step-by-step guide based ONLY on those articles and list their ids.
If the knowledge base does NOT cover the problem, do not guess: set "covered" to false and begin the draft with the exact marker "[not covered]" followed by a short, honest holding message.
Output: {"covered": true|false, "article_ids": ["FAQ-xx"], "draft": "..."}"""

COMPLAINT_SYSTEM = COMMON + """You are the complaints specialist. Write an empathetic apology for the customer's experience and propose a commercial next step (for example: a call from an account manager, a review of the account, a goodwill gesture to be assessed).
HARD RULES: never admit legal fault or liability (do not say it was our fault or that we are responsible); never promise a specific refund, discount or compensation amount; never mention figures in euros.
Output: {"draft": "..."}"""


def _msg(text):
    return f'Customer message:\n"""{text}"""'


def billing(llm, text, ctx):
    cust = ctx["customer"]
    record = json.dumps(cust, ensure_ascii=False, indent=1) if cust else "NO CUSTOMER RECORD FOUND FOR THIS SENDER"
    res = llm.complete("billing", BILLING_SYSTEM, f"Billing database record:\n{record}\n\n{_msg(text)}", 700)
    return {"draft": parse_json(res.text)["draft"], "customer_found": cust is not None}


def technical(llm, text, ctx):
    kb = json.dumps(ctx["faq"], ensure_ascii=False, indent=1)
    res = llm.complete("technical", TECHNICAL_SYSTEM, f"Knowledge base:\n{kb}\n\n{_msg(text)}", 900)
    d = parse_json(res.text)
    covered, draft = bool(d.get("covered", False)), d["draft"]
    if not covered and not draft.lstrip().lower().startswith("[not covered]"):
        draft = "[not covered] " + draft  # enforce the marker the supervisor relies on
    return {"draft": draft, "covered": covered, "article_ids": d.get("article_ids", [])}


def complaint(llm, text, ctx):
    res = llm.complete("complaint", COMPLAINT_SYSTEM, _msg(text), 600)
    return {"draft": parse_json(res.text)["draft"]}


SPECIALISTS = {"billing": billing, "technical": technical, "complaint": complaint}