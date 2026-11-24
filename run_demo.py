"""Process a single message and print a readable summary.

  python run_demo.py --email ana.ferreira@exemplo.pt --text "Cobraram-me duas vezes o plano Pro!"
  (add --json to see the full technical record, --dry-run to use the offline stub)
"""
import argparse
import json
import textwrap
from dotenv import load_dotenv
from src.data import load_customers, load_faq
from src.llm import get_llm
from src.pipeline import process

LINE = "-" * 70


def show(rec):
    r, sup = rec["routing"], rec["supervisor"]
    print(f"\n{LINE}\nMENSAGEM : {rec['text']}\nCLIENTE  : {rec['sender_email'] or '(sem email)'}\n{LINE}")
    if r:
        print(f"1) ROTEADOR     -> categoria: {r['category']} | urgência: {r['urgency']}")
        print(f"2) ESPECIALISTA -> {rec['specialist']}")
        print("\n   Minuta de resposta:")
        for para in rec["draft"].split("\n"):
            print(textwrap.fill(para, 66, initial_indent="   | ", subsequent_indent="   | ") if para.strip() else "   |")
    else:
        print("1) ROTEADOR     -> falhou (ver erro abaixo)")
    destinos = {"CLIENTE": "enviar ao cliente", "HUMANO": "passar a uma pessoa",
                "SUPORTE_NIVEL_2": "passar ao Suporte de Nível 2", "REVISAO_HUMANA": "revisão humana (compliance)"}
    print(f"\n3) SUPERVISOR   -> {sup['decision']}: {destinos.get(sup['destination'], sup['destination'])}")
    print(f"   motivo: {sup['reason']}" + (f" | {'; '.join(sup['issues'])}" if sup.get("issues") else ""))
    if rec["error"]:
        print(f"\n   ERRO: {rec['error']}")
    print(f"{LINE}\nChamadas ao modelo: {rec['llm_calls']} | tokens: {rec['input_tokens']} entrada, "
          f"{rec['output_tokens']} saída | tempo: {rec['latency_s']:.0f} s\n")


if __name__ == "__main__":
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--email", default="")
    ap.add_argument("--json", action="store_true", help="print the full technical record")
    ap.add_argument("--dry-run", action="store_true", help="use the offline stub (no API key)")
    a = ap.parse_args()
    rec = process({"text": a.text, "sender_email": a.email}, get_llm(a.dry_run), load_customers(), load_faq())
    print(json.dumps(rec, ensure_ascii=False, indent=2)) if a.json else show(rec)