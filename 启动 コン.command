#!/bin/zsh
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "请先在项目目录创建虚拟环境并安装依赖。"
  read -k 1
  exit 1
fi
if [ "$#" -gt 0 ]; then
  PDF_PATH="$1"
else
  PDF_PATH=$(osascript -e 'POSIX path of (choose file with prompt "选择要转换的 PDF" of type {"pdf"})') || exit 0
fi
FORMAT=$(osascript <<'APPLESCRIPT'
set formats to {"全部格式（ZIP）", "Markdown（.md）", "Word（.docx）", "JSON（.json）", "纯文本（.txt）"}
set picked to choose from list formats with prompt "コン · 选择输出格式" default items {"全部格式（ZIP）"}
if picked is false then return ""
return item 1 of picked
APPLESCRIPT
)
case "$FORMAT" in
  "全部格式（ZIP）") EXT="zip";;
  "Markdown（.md）") EXT="md";;
  "Word（.docx）") EXT="docx";;
  "JSON（.json）") EXT="json";;
  "纯文本（.txt）") EXT="txt";;
  *) exit 0;;
esac
OUTPUT=$(.venv/bin/python convert_local.py "$PDF_PATH" "$EXT") || exit 1
osascript -e "display notification \"转换完成：$OUTPUT\" with title \"コン\""
