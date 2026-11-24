"""Show why messages were escalated for compliance.   python show_compliance.py results_v2"""
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1] if len(sys.argv) > 1 else "results")
for line in (folder / "audit_log.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r["supervisor"]["reason"] == "compliance":
        print("=" * 70)
        print(f'{r["id"]}: {r["text"]}')
        print("MOTIVO(S):", r["supervisor"].get("issues"))
        print("MINUTA:\n" + (r["draft"] or ""))
