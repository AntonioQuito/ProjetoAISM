"""Measure how long the Gemini API takes, to find a fast model.

  python diagnose.py                      -> tests the model in .env
  python diagnose.py gemini-3.6-flash-lite gemini-2.5-flash-lite   -> tests several
"""
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
from google import genai
from google.genai import types

client = genai.Client()
print("Modelos Gemini disponíveis para esta chave (os 'flash'):")
try:
    names = [m.name.replace("models/", "") for m in client.models.list()
             if "flash" in m.name.lower() and "generateContent" in (m.supported_actions or ["generateContent"])]
    print("  " + "\n  ".join(sorted(names)[:25]))
except Exception as e:
    print("  (não foi possível listar:", str(e)[:100], ")")

DEFAULTS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
models = sys.argv[1:] or DEFAULTS
for model in models:
    for label, cfg in [("sem opções", None),
                       ("thinking MINIMAL", types.GenerateContentConfig(
                           thinking_config=types.ThinkingConfig(thinking_level="MINIMAL")))]:
        time.sleep(8)  # pause so one test does not trigger the per-minute limit of the next
        t = time.time()
        try:
            r = client.models.generate_content(model=model, contents="Responde apenas com a palavra: ok", config=cfg)
            print(f"{model} | {label}: {time.time() - t:.1f} s -> {(r.text or '').strip()[:30]!r}")
        except Exception as e:
            print(f"{model} | {label}: ERRO após {time.time() - t:.1f} s -> {str(e)[:400]}")