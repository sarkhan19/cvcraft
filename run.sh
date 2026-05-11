#!/bin/bash
# run.sh – Start the CV Generator app

echo ""
echo "  ╔══════════════════════════════════╗"
echo "  ║       CV Generator App 🚀        ║"
echo "  ╚══════════════════════════════════╝"
echo ""
echo "  Installing dependencies..."
pip install flask reportlab --break-system-packages -q

echo ""
echo "  Starting server..."
echo "  → Open your browser: http://localhost:5000"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

cd "$(dirname "$0")"
python3 app.py
