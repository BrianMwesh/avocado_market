#!/usr/bin/env bash
# Quick start on macOS / Linux. On Windows follow the README steps.
set -e
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
