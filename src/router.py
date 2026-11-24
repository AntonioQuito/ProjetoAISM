"""Agent 1: Router / Classifier. Outputs structured data only, never customer-facing text."""
from .llm import parse_json

CATEGORIES = ("billing", "technical", "complaint")

SYSTEM = """You are the routing component of a customer-support system. You read ONE customer message (usually in European Portuguese) and output ONLY a JSON object:
{"category": "billing" | "technical" | "complaint", "urgency": 1 | 2 | 3}

STRICT RULE: you never write a reply, greeting or any text for the customer. Output the JSON object and nothing else.

Categories:
- billing: payments, charges, invoices, prices, subscription fees, a concrete question about money the customer paid or was charged.
- technical: the product does not work, errors, crashes, outages, API problems, how-to questions, questions about features or integrations.
- complaint: the main purpose of the message is to express dissatisfaction (with service, staff, delays, a decision, a product change) or to demand compensation, WITHOUT a concrete billing question or technical problem that can be answered.

Tie-break rules for ambiguous messages:
1. A bug, crash or error is technical even if it happens while paying.
2. A concrete charge/invoice/payment question is billing even if the tone is angry.
3. A frustrated customer with a simple technical problem is technical, not complaint.
4. Demands for compensation for damages, or threats of legal/formal action, are complaint.

Urgency:
- 3 (critical): outage or total blockage affecting a business, suspected fraud or charges the customer does not recognise or did not authorise, an explicit demand for compensation for damages, legal threats or formal complaints.
- 2 (medium): something is wrong and affects the customer but is not critical: a wrong, duplicate or failed charge that the customer can see in their invoices, a bug or crash, a repeated problem, a justified complaint about service.
- 1 (low): informational or how-to question, a simple request for invoice data, mild dissatisfaction.
A billing mistake (duplicate charge, wrong amount, charge after cancelling) is urgency 2, NOT 3, unless the customer suspects fraud or does not recognise the charge."""


class RouterError(Exception):
    pass


def route(llm, text):
    last = None
    for _ in range(2):  # one retry on malformed output
        res = llm.complete("router", SYSTEM, f'Customer message:\n"""{text}"""', max_tokens=60)
        try:
            d = parse_json(res.text)
            cat, urg = str(d["category"]).strip().lower(), int(d["urgency"])
            if cat in CATEGORIES and urg in (1, 2, 3):
                return {"category": cat, "urgency": urg}
            last = f"invalid values: {d}"
        except Exception as e:
            last = str(e)
    raise RouterError(last)