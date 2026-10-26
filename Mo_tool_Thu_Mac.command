#!/bin/bash
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null; then
  echo "Cần cài Python 3.11 trở lên từ python.org."
  read -r -p "Nhấn Enter để đóng."
  exit 1
fi
python3 start.py
if [ $? -ne 0 ]; then read -r -p "Chưa mở được. Nhấn Enter để đóng."; fi
