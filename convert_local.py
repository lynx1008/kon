"""Headless local converter used by the macOS native dialog launcher."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

from app import analyze_text, extract_pdf, make_docx, markdown_content


def convert(pdf_path: Path, fmt: str) -> Path:
    with pdf_path.open("rb") as source:
        class Upload:
            def read(self_inner):
                return source.read()
        text, pages = extract_pdf(Upload())
    stats = analyze_text(text)
    stem = pdf_path.stem
    outputs = {
        f"{stem}.md": markdown_content(text, stats, stem).encode(),
        f"{stem}.json": json.dumps({"filename": pdf_path.name, "statistics": stats, "pages": pages, "text": text}, ensure_ascii=False, indent=2).encode(),
        f"{stem}.txt": text.encode(),
        f"{stem}.docx": make_docx(text, stats, stem).getvalue(),
    }
    if fmt == "zip":
        target = pdf_path.with_name(f"{stem}-converted.zip")
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in outputs.items():
                archive.writestr(name, content)
    else:
        target = pdf_path.with_name(f"{stem}.{fmt}")
        target.write_bytes(outputs[f"{stem}.{fmt}"])
    return target


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python convert_local.py FILE.pdf md|docx|json|txt|zip")
    print(convert(Path(sys.argv[1]).expanduser(), sys.argv[2]))
