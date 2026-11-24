"""Offline tests with the stub LLM: they check the plumbing and rules, not model quality."""
from src.data import load_customers, load_faq, load_messages
from src.llm import StubLLM
from src.pipeline import process
from src.supervisor import code_checks

C, F = load_customers(), load_faq()


def run(text, email="ana.ferreira@exemplo.pt"):
    return process({"id": "t", "text": text, "sender_email": email}, StubLLM(), C, F)


def test_dataset_is_consistent():
    msgs = load_messages()
    assert 20 <= len(msgs) <= 30
    assert {m["expected_category"] for m in msgs} == {"billing", "technical", "complaint"}


def test_only_one_specialist_runs():
    for m in load_messages():
        assert process(m, StubLLM(), C, F)["specialist_calls"] == 1


def test_urgency_3_escalates_to_human():
    r = run("A API está offline há 4 horas!")
    assert r["supervisor"]["decision"] == "ESCALAR" and r["supervisor"]["destination"] == "HUMANO"


def test_not_covered_escalates_to_level2():
    r = run("Vocês suportam SSO com SAML?")
    assert r["supervisor"]["destination"] == "SUPORTE_NIVEL_2"


def test_complaint_code_guard():
    assert code_checks("complaint", "Vamos devolver 50€.")
    assert code_checks("complaint", "A culpa é nossa.")
    assert not code_checks("billing", "A fatura é de 49€.")
