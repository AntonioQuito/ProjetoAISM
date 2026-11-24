"""Orchestrator: router -> ONE specialist -> supervisor, with a full audit record."""
import time
from .data import find_customer
from .router import route
from .specialists import SPECIALISTS
from .supervisor import supervise


class Tracker:
    """Wraps an LLM and records every call (agent, tokens) for cost auditing."""
    def __init__(self, llm):
        self.llm, self.calls = llm, []

    def complete(self, agent, system, user, max_tokens=800):
        r = self.llm.complete(agent, system, user, max_tokens)
        self.calls.append({"agent": agent, "input_tokens": r.input_tokens, "output_tokens": r.output_tokens})
        return r


def process(msg, llm, customers, faq):
    t0, tr = time.time(), Tracker(llm)
    rec = {"id": msg.get("id"), "text": msg["text"], "sender_email": msg.get("sender_email"),
           "routing": None, "specialist": None, "draft": None, "supervisor": None, "error": None}
    try:
        rec["routing"] = routing = route(tr, msg["text"])
        ctx = {"customer": find_customer(msg.get("sender_email"), customers), "faq": faq}
        rec["specialist"] = routing["category"]  # only this one is executed
        spec = SPECIALISTS[routing["category"]](tr, msg["text"], ctx)
        rec["draft"], rec["specialist_output"] = spec["draft"], spec
        rec["supervisor"] = supervise(tr, msg["text"], routing, spec)
    except Exception as e:  # fail safe: anything unexpected goes to a human
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["supervisor"] = {"decision": "ESCALAR", "destination": "HUMANO", "reason": "pipeline_error", "llm_checked": False}
    rec["trace"] = tr.calls
    rec["llm_calls"] = len(tr.calls)
    rec["specialist_calls"] = sum(c["agent"] in SPECIALISTS for c in tr.calls)
    rec["input_tokens"] = sum(c["input_tokens"] for c in tr.calls)
    rec["output_tokens"] = sum(c["output_tokens"] for c in tr.calls)
    rec["latency_s"] = round(time.time() - t0, 3)
    return rec
