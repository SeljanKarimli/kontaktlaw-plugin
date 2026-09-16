from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


REPO = Path(__file__).resolve().parents[1]
KNOWLEDGE = REPO / "kontaktlaw/skills/legal-review/references/knowledge"
LAW_DIR = KNOWLEDGE / "MDs"
SOURCES = KNOWLEDGE / "sources.json"
OPEN_SPAN = '<span style="color:red">'
CLOSE_SPAN = "</span>"
OLD_NOTE = "> Qırmızı hissələr əvvəlki lokal MD faylından fərqli olan maddələrdir."
NEW_NOTE = (
    "> Lokal müqayisədən qalan rəng işarələri paketləmə zamanı silinib; "
    "hüquqi dəyişiklik qeydləri [N] istinadlı footnote-lardadır."
)
FOOTNOTE = re.compile(r"^\[\d+\]", re.MULTILINE)


def main() -> None:
    manifest = json.loads(SOURCES.read_text(encoding="utf-8"))
    report = []

    for source in manifest["sources"]:
        path = LAW_DIR / source["file"]
        before = path.read_bytes().decode("utf-8")
        before_lines = before.count("\n") + (not before.endswith("\n"))
        before_footnotes = len(FOOTNOTE.findall(before))
        open_count = before.count(OPEN_SPAN)
        close_count = before.count(CLOSE_SPAN)

        if open_count != close_count:
            raise ValueError(f"Unbalanced diff markup in {path.name}")

        after = before.replace(OPEN_SPAN, "").replace(CLOSE_SPAN, "")
        after = after.replace(OLD_NOTE, NEW_NOTE)

        if FOOTNOTE.findall(after) != FOOTNOTE.findall(before):
            raise ValueError(f"Footnotes changed in {path.name}")
        if after.count("\n") + (not after.endswith("\n")) != before_lines:
            raise ValueError(f"Line count changed in {path.name}")
        if OPEN_SPAN in after or CLOSE_SPAN in after:
            raise ValueError(f"Diff markup remains in {path.name}")

        encoded = after.encode("utf-8")
        path.write_bytes(encoded)
        source["bytes"] = len(encoded)
        source["sha256"] = hashlib.sha256(encoded).hexdigest()
        source["lines"] = before_lines
        report.append(
            {
                "file": path.name,
                "removed_spans": open_count,
                "footnotes_preserved": before_footnotes,
                "lines_preserved": before_lines,
            }
        )

    manifest["packaged_on"] = "2026-09-16"
    SOURCES.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
