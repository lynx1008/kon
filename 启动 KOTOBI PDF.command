#!/bin/zsh
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "请先在项目目录创建虚拟环境并安装依赖。"
  read -k 1
  exit 1
fi
exec .venv/bin/python desktop_app.py
