"""Agent 3: Supervisor. Deterministic escalation rules + compliance check (regex + LLM)."""
import re
from .llm import parse_json

SYSTEM = """You are the compliance supervisor of a customer-support system. You receive the original customer message, the classification and the draft reply written by a specialist. Decide if the draft can be sent automatically.
The draft is NON-COMPLIANT if it: admits legal fault or liability; promises a specific refund, discount or compensation (amount or certainty); makes commitments the company cannot guarantee; or contains abusive or inappropriate wording. Describing facts from the customer's account, or saying a case will be REVIEWED, is compliant.
Output ONLY JSON: {"compliant": true|false, "issues": ["..."]}"""

AMOUNT = re.compile(r"\d+(?:[.,]\d+)?\s?(?:€|eur\b|euros?\b)", re.I)
LIABILITY = re.compile(r"(a culpa é nossa|a culpa foi nossa|assumimos (a )?(total )?responsabilidade|"
                       r"reconhecemos a nossa responsabilidade|somos responsáveis|erro nosso|falha nossa)", re.I)


def code_checks(category, draft):
    """Cheap deterministic guard for the complaints agent's hard rules."""
    issues = []
    if category == "complaint":
        if AMOUNT.search(draft):
            issues.append("complaint draft mentions a monetary amount")
        if LIABILITY.search(draft):
            issues.append("complaint draft admits liability")
    return issues


def supervise(llm, text, routing, spec):
    if routing["urgency"] == 3:
        return {"decision": "ESCALAR", "destination": "HUMANO", "reason": "urgency_3", "llm_checked": False}
    if routing["category"] == "technical" and (not spec.get("covered", True)
                                               or spec["draft"].lstrip().lower().startswith("[not covered]")):
        return {"decision": "ESCALAR", "destination": "SUPORTE_NIVEL_2", "reason": "not_covered", "llm_checked": False}
    issues = code_checks(routing["category"], spec["draft"])
    user = (f'Original message:\n"""{text}"""\n\nClassification: {routing}\n\nDraft reply:\n"""{spec["draft"]}"""')
    res = llm.complete("supervisor", SYSTEM, user, 300)
    verdict = parse_json(res.text)
    if not verdict.get("compliant", False):
        issues += [str(i) for i in verdict.get("issues", [])] or ["llm flagged draft as non-compliant"]
    if issues:
        return {"decision": "ESCALAR", "destination": "REVISAO_HUMANA", "reason": "compliance",
                "issues": issues, "llm_checked": True}
    return {"decision": "ENVIAR", "destination": "CLIENTE", "reason": "ok", "llm_checked": True}
