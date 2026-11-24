"""Run the whole test set and compute metrics.  python evaluate.py [--dry-run] [--limit N]"""
import argparse, json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sklearn.metrics import classification_report
from src.data import load_customers, load_faq, load_messages
from src.llm import get_llm
from src.pipeline import process

CATS = ["billing", "technical", "complaint"]


def plot_cm(cm, title, path):
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.imshow(cm.values, cmap="Blues")
    ax.set_xticks(range(len(cm.columns)), [str(c) for c in cm.columns])
    ax.set_yticks(range(len(cm.index)), [str(i) for i in cm.index])
    ax.set_xlabel("Predicted (Agent 1)"); ax.set_ylabel("Ground truth"); ax.set_title(title)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, int(cm.values[i, j]), ha="center", va="center",
                    color="white" if cm.values[i, j] > cm.values.max() / 2 else "black")
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def main():
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="offline stub; metrics are NOT valid results")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default="results")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run in --out (redoes messages that errored)")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)

    llm = get_llm(a.dry_run)
    customers, faq, msgs = load_customers(), load_faq(), load_messages()[: a.limit]
    log_path = out / "audit_log.jsonl"
    records = []
    if a.resume and log_path.exists():
        prev = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        records = [r for r in prev if not r.get("error")]  # failed messages are redone
        log_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        print(f"Resuming: {len(records)} messages already done")
    done = {r["id"] for r in records}
    with open(log_path, "a" if a.resume else "w", encoding="utf-8") as log:
        for m in msgs:
            if m["id"] in done:
                continue
            r = process(m, llm, customers, faq)
            r["expected"] = {k: m[k] for k in ("expected_category", "expected_urgency", "expected_decision", "ambiguous")}
            records.append(r)
            log.write(json.dumps(r, ensure_ascii=False) + "\n")
            log.flush()  # progress is saved after every message
            print(f'{m["id"]}: {r["routing"]} -> {r["supervisor"]["decision"]} ({r["supervisor"]["reason"]}) [{r["latency_s"]}s]'
                  + (f' ERROR: {r["error"]}' if r["error"] else ""))
    records.sort(key=lambda r: r["id"])

    rows = []
    for r in records:
        e = r["expected"]
        rows.append({"id": r["id"], "text": r["text"], "ambiguous": e["ambiguous"],
                     "exp_cat": e["expected_category"], "pred_cat": (r["routing"] or {}).get("category", "error"),
                     "exp_urg": e["expected_urgency"], "pred_urg": (r["routing"] or {}).get("urgency"),
                     "exp_dec": e["expected_decision"], "pred_dec": r["supervisor"]["decision"],
                     "reason": r["supervisor"]["reason"], "issues": "; ".join(r["supervisor"].get("issues", [])),
                     "draft": r.get("draft"), "specialist_calls": r["specialist_calls"],
                     "llm_calls": r["llm_calls"], "in_tok": r["input_tokens"], "out_tok": r["output_tokens"],
                     "latency_s": r["latency_s"], "error": r["error"]})
    df = pd.DataFrame(rows)
    df["cat_ok"] = df.exp_cat == df.pred_cat
    df["urg_ok"] = df.exp_urg == df.pred_urg
    df["dec_ok"] = df.exp_dec == df.pred_dec
    df.to_csv(out / "per_message.csv", index=False, encoding="utf-8")
    df[~(df.cat_ok & df.urg_ok & df.dec_ok)].to_csv(out / "errors.csv", index=False, encoding="utf-8")

    cm = pd.crosstab(df.exp_cat, df.pred_cat).reindex(index=CATS, columns=CATS + ["error"], fill_value=0)
    cm.to_csv(out / "confusion_category.csv")
    plot_cm(cm, "Routing: category", out / "confusion_category.png")
    ucm = pd.crosstab(df.exp_urg, df.pred_urg).reindex(index=[1, 2, 3], columns=[1, 2, 3], fill_value=0)
    ucm.to_csv(out / "confusion_urgency.csv")
    plot_cm(ucm, "Routing: urgency", out / "confusion_urgency.png")

    amb = df[df.ambiguous]
    metrics = {
        "model": getattr(llm, "model", "?"), "dry_run": a.dry_run, "n_messages": len(df),
        "category_accuracy": round(df.cat_ok.mean(), 4),
        "category_accuracy_ambiguous": round(amb.cat_ok.mean(), 4) if len(amb) else None,
        "category_accuracy_non_ambiguous": round(df[~df.ambiguous].cat_ok.mean(), 4),
        "urgency_accuracy": round(df.urg_ok.mean(), 4),
        "urgency_mae": round((df.exp_urg - df.pred_urg.fillna(0)).abs().mean(), 4),
        "decision_accuracy": round(df.dec_ok.mean(), 4),
        "escalation_rate_pred": round((df.pred_dec == "ESCALAR").mean(), 4),
        "escalation_rate_expected": round((df.exp_dec == "ESCALAR").mean(), 4),
        "escalation_reasons": df.reason.value_counts().to_dict(),
        "avg_specialist_calls_per_message": round(df.specialist_calls.mean(), 3),
        "avg_llm_calls_per_message": round(df.llm_calls.mean(), 3),
        "total_input_tokens": int(df.in_tok.sum()), "total_output_tokens": int(df.out_tok.sum()),
        "avg_latency_s": round(df.latency_s.mean(), 3),
        "pipeline_errors": int(df.error.notna().sum()),
        "per_class": classification_report(df.exp_cat, df.pred_cat, labels=CATS, output_dict=True, zero_division=0),
    }
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== METRICS ===" + ("  (DRY RUN: NOT VALID RESULTS)" if a.dry_run else ""))
    for k, v in metrics.items():
        if k != "per_class":
            print(f"{k}: {v}")
    print("\nConfusion matrix (rows=truth):\n", cm)


if __name__ == "__main__":
    main()