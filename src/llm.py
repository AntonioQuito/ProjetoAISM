"""LLM access layer: real Anthropic client and an offline stub for plumbing tests."""
import json
import os
import re
import time
from dataclasses import dataclass

DEFAULT_MODELS = {"gemini": "gemini-3.6-flash", "anthropic": "claude-sonnet-5-5"}


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


def parse_json(text):
    """Extract the first JSON object from a model reply (tolerates code fences / preamble)."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in reply: {text[:120]!r}")
    return json.loads(text[start:end + 1])


class AnthropicLLM:
    def __init__(self, model=None):
        from anthropic import Anthropic  # imported lazily so --dry-run needs no key
        self.client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        self.model = model or os.getenv("MODEL", DEFAULT_MODELS["anthropic"])
        self.use_temperature = True

    def complete(self, agent, system, user, max_tokens=800):
        last = None
        for attempt in range(3):
            try:
                kwargs = dict(model=self.model, max_tokens=max_tokens, system=system,
                              messages=[{"role": "user", "content": user}])
                if self.use_temperature:
                    kwargs["temperature"] = 0
                r = self.client.messages.create(**kwargs)
                text = "".join(b.text for b in r.content if b.type == "text")
                return LLMResult(text, r.usage.input_tokens, r.usage.output_tokens)
            except Exception as e:  # network errors, rate limits, unsupported params
                last = e
                if "temperature" in str(e).lower() and self.use_temperature:
                    self.use_temperature = False  # some models do not accept it
                    continue
                time.sleep(2 * (attempt + 1))
        raise last


class GeminiLLM:
    """Google AI Studio (free tier). Reads GEMINI_API_KEY. Spaces calls to respect the RPM limit."""

    def __init__(self, model=None):
        from google import genai  # imported lazily so --dry-run needs no key
        from google.genai import types
        self.types = types
        self.client = genai.Client()  # reads GEMINI_API_KEY from the environment
        self.model = model or os.getenv("MODEL", DEFAULT_MODELS["gemini"])
        self.min_interval = float(os.getenv("MIN_INTERVAL_S", "6"))  # 6 s -> max 10 requests/minute
        self._last = 0.0
        # Gemini 3 models "think" before answering, which is slow and unnecessary for our short tasks
        self.thinking = os.getenv("THINKING_LEVEL", "MINIMAL").upper()  # MINIMAL | LOW | MEDIUM | HIGH | OFF

    def complete(self, agent, system, user, max_tokens=800):
        last = None
        for attempt in range(6):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                cfg = self.types.GenerateContentConfig(
                    system_instruction=system, temperature=0,
                    max_output_tokens=max(max_tokens, 2048),  # headroom in case the model "thinks"
                    response_mime_type="application/json",  # all our agents answer in JSON
                    **({"thinking_config": self.types.ThinkingConfig(thinking_level=self.thinking)}
                       if self.thinking != "OFF" else {}))
                self._last = time.time()
                r = self.client.models.generate_content(model=self.model, contents=user, config=cfg)
                u = r.usage_metadata
                out_tok = (getattr(u, "candidates_token_count", 0) or 0) + (getattr(u, "thoughts_token_count", 0) or 0)
                return LLMResult(r.text or "", getattr(u, "prompt_token_count", 0) or 0, out_tok)
            except Exception as e:
                last = e
                msg = str(e)
                if "thinking" in msg.lower() and self.thinking != "OFF":
                    print("  [aviso] este modelo não aceita THINKING_LEVEL; a desativar essa opção", flush=True)
                    self.thinking = "OFF"
                    continue
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    wait = 30 * (attempt + 1)  # rate limit: back off for longer
                    print(f"  [aviso] limite de pedidos do plano gratuito (429); a esperar {wait}s...", flush=True)
                else:
                    wait = 3 * (attempt + 1)
                    print(f"  [aviso] erro na chamada ({msg[:80]}); a tentar de novo em {wait}s...", flush=True)
                time.sleep(wait)
        raise last


class StubLLM:
    """Keyword-based fake used ONLY to test the code path without an API key.
    Its outputs are meaningless as results."""
    model = "stub"

    def complete(self, agent, system, user, max_tokens=800):
        u = user.lower()
        if agent == "router":
            if re.search(r"fraude|offline|indemniza|advogado|reclama", u):
                out = {"category": "complaint" if re.search(r"indemniza|advogado", u) else
                       ("billing" if "fraude" in u else "technical"), "urgency": 3}
            elif re.search(r"fatura|cobr|pagamento|pago|€", u):
                out = {"category": "billing", "urgency": 2}
            elif re.search(r"péssimo|desiludido|insatisfeit|mal-educado|prometeram", u):
                out = {"category": "complaint", "urgency": 2}
            else:
                out = {"category": "technical", "urgency": 1}
        elif agent == "technical":
            covered = not re.search(r"sso|salesforce|funcionalidade", u)
            out = {"covered": covered, "article_ids": ["FAQ-01"] if covered else [],
                   "draft": "[stub] guia" if covered else "[not covered] [stub]"}
        elif agent == "supervisor":
            out = {"compliant": True, "issues": []}
        else:
            out = {"draft": f"[stub] minuta {agent}"}
        return LLMResult(json.dumps(out, ensure_ascii=False), 0, 0)


def get_llm(dry_run=False):
    if dry_run:
        return StubLLM()
    provider = os.getenv("PROVIDER", "gemini").lower()
    if provider == "gemini":
        return GeminiLLM()
    if provider == "anthropic":
        return AnthropicLLM()
    raise ValueError(f"Unknown PROVIDER {provider!r} (use 'gemini' or 'anthropic')")