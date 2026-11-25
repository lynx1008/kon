from __future__ import annotations

import io
import json
import re
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

import fitz
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
app.config["JSON_AS_ASCII"] = False
SETTINGS_PATH = Path.home() / ".kon-config.json"

WORD_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
HIRAGANA_KATAKANA_RE = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def normalize(text: str) -> str:
    """Normalize compatibility characters while preserving line structure."""
    return unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")


def analyze_text(text: str) -> dict:
    normalized = normalize(text)
    kana = len(HIRAGANA_KATAKANA_RE.findall(normalized))
    kanji = len(CJK_RE.findall(normalized))
    english_words = len(WORD_RE.findall(normalized))
    latin_letters = len(re.findall(r"[A-Za-z]", normalized))
    scores = {"日本語": kana * 2 + kanji * 0.15, "中文": kanji, "English": english_words * 4 + latin_letters * 0.05}
    primary = max(scores, key=scores.get) if any(scores.values()) else "判定不能"
    return {
        "kana": kana,
        "kanji": kanji,
        "english_words": english_words,
        "primary_language": primary,
        "characters": len(normalized.replace("\n", "")),
    }


def repair_line_breaks(text: str) -> str:
    """Join PDF line wraps without destroying paragraphs or headings."""
    lines = [line.rstrip() for line in normalize(text).split("\n")]
    output: list[str] = []
    pending = ""
    for raw in lines:
        line = raw.strip()
        if not line:
            if pending:
                output.append(pending.strip())
                pending = ""
            if not output or output[-1] != "":
                output.append("")
            continue
        if not pending:
            pending = line
            continue
        is_heading = bool(re.match(r"^(?:#{1,6}\s|第[一二三四五六七八九十0-9]+[章節]|[0-9]+[.、])", line))
        ends_sentence = bool(re.search(r"[。．.!！?？:：]$", pending))
        if is_heading or ends_sentence:
            output.append(pending.strip())
            pending = line
        elif re.search(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]$", pending) or re.match(r"^[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]", line):
            pending += line
        else:
            pending += " " + line
    if pending:
        output.append(pending.strip())
    return "\n".join(output).strip()


def extract_pdf(file_storage) -> tuple[str, list[dict]]:
    data = file_storage.read()
    with fitz.open(stream=data, filetype="pdf") as pdf:
        pages = [{"page": i + 1, "text": page.get_text("text")} for i, page in enumerate(pdf)]
    raw = "\n\n".join(page["text"] for page in pages)
    return repair_line_breaks(raw), pages


def markdown_content(text: str, stats: dict, filename: str) -> str:
    return f"# {filename}\n\n> 主言語: {stats['primary_language']}\n> 日本語かな: {stats['kana']} / CJK漢字: {stats['kanji']} / English words: {stats['english_words']}\n\n{text}\n"


def make_docx(text: str, stats: dict, filename: str) -> io.BytesIO:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    def set_east_asia_font(style, font_name: str):
        rpr = style._element.get_or_add_rPr()
        rfonts = rpr.rFonts
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        rfonts.set(qn("w:eastAsia"), font_name)

    set_east_asia_font(normal, "Yu Gothic")
    for style_name in ["Title", "Heading 1", "Heading 2"]:
        if style_name in doc.styles:
            style = doc.styles[style_name]
            style.font.name = "Calibri"
            set_east_asia_font(style, "Yu Gothic")
    doc.add_heading(filename, level=0)
    doc.add_paragraph(f"主言語: {stats['primary_language']}　かな: {stats['kana']}　漢字: {stats['kanji']}　English words: {stats['english_words']}")
    for block in text.split("\n\n"):
        if block.strip():
            doc.add_paragraph(block.strip())
    stream = io.BytesIO()
    doc.save(stream)
    stream.seek(0)
    return stream


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/preview")
def preview():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "PDFファイルを選択してください。"}), 400
    text, pages = extract_pdf(file)
    return jsonify({"filename": Path(file.filename).stem, "text": text, "stats": analyze_text(text), "pages": len(pages)})


@app.post("/api/convert")
def convert():
    file = request.files.get("file")
    fmt = request.form.get("format", "md")
    if not file or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "PDFファイルを選択してください。"}), 400
    if fmt not in {"md", "docx", "json", "txt", "zip"}:
        return jsonify({"error": "未対応の形式です。"}), 400
    text, pages = extract_pdf(file)
    stats = analyze_text(text)
    stem = Path(file.filename).stem
    output_dir = request.form.get("output_dir", "").strip()
    files = {
        f"{stem}.md": markdown_content(text, stats, stem).encode("utf-8"),
        f"{stem}.json": json.dumps({"filename": file.filename, "statistics": stats, "pages": pages, "text": text}, ensure_ascii=False, indent=2).encode("utf-8"),
        f"{stem}.txt": text.encode("utf-8"),
    }
    docx_stream = make_docx(text, stats, stem)
    files[f"{stem}.docx"] = docx_stream.getvalue()
    if fmt == "zip":
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        stream.seek(0)
        if output_dir:
            target = Path(output_dir).expanduser() / f"{stem}-converted.zip"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(stream.getvalue())
            return jsonify({"saved_to": str(target)})
        return send_file(stream, as_attachment=True, download_name=f"{stem}-converted.zip", mimetype="application/zip")
    mimetypes = {"md": "text/markdown", "json": "application/json", "txt": "text/plain", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if output_dir:
        target = Path(output_dir).expanduser() / f"{stem}.{fmt}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(files[f"{stem}.{fmt}"])
        return jsonify({"saved_to": str(target)})
    return send_file(io.BytesIO(files[f"{stem}.{fmt}"]), as_attachment=True, download_name=f"{stem}.{fmt}", mimetype=mimetypes[fmt])


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
