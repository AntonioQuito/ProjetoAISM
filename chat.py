"""Modo interativo: escreves a mensagem do cliente e o sistema processa-a.

  python chat.py
Comandos: /email <endereço>  muda o email do cliente   |   /sair  termina
"""
import textwrap
from dotenv import load_dotenv
from src.data import load_customers, load_faq
from src.llm import get_llm
from src.pipeline import process

LINE = "-" * 70
DESTINOS = {"CLIENTE": "enviar ao cliente", "HUMANO": "passar a uma pessoa",
            "SUPORTE_NIVEL_2": "passar ao Suporte de Nível 2", "REVISAO_HUMANA": "revisão humana (compliance)"}


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
    print(f"\n3) SUPERVISOR   -> {sup['decision']}: {DESTINOS.get(sup['destination'], sup['destination'])}")
    print(f"   motivo: {sup['reason']}" + (f" | {'; '.join(sup['issues'])}" if sup.get("issues") else ""))
    if rec["error"]:
        print(f"\n   ERRO: {rec['error']}")
    print(f"{LINE}\nChamadas ao modelo: {rec['llm_calls']} | tokens: {rec['input_tokens']} entrada, "
          f"{rec['output_tokens']} saída | tempo: {rec['latency_s']:.0f} s\n")


def main():
    load_dotenv()
    llm, customers, faq = get_llm(), load_customers(), load_faq()
    email = input("Email do cliente (Enter para nenhum): ").strip()
    print("Escreve a mensagem do cliente. Comandos: /email <endereço>, /sair\n")
    while True:
        try:
            text = input("Mensagem> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("/sair", "/exit", "/quit"):
            break
        if text.lower().startswith("/email"):
            email = text[6:].strip()
            print(f"Email definido: {email or '(nenhum)'}\n")
            continue
        show(process({"text": text, "sender_email": email}, llm, customers, faq))


if __name__ == "__main__":
    main()
