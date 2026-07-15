#!/usr/bin/env bash
# Replit entrypoint: installs dependencies once, then runs the demo.
set -e
pip install -e . -q
echo ""
echo "=== agentic-logistics-eval: running demo scenario ==="
python -m agentic_logistics.cli demo --scenario scenario_01_port_congestion.json --provider mock
echo ""
echo "=== To run the full evaluation harness: ==="
echo "    python -m agentic_logistics.cli eval"
echo "=== To run the test suite: ==="
echo "    pytest"
