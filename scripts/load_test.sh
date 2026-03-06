#!/usr/bin/env bash
# load_test.sh — Simulation de trafic sur l'API demo
# Usage: ./scripts/load_test.sh [normal|errors|slow|all]
set -euo pipefail

API="http://localhost:8000"
MODE="${1:-normal}"

normal_traffic() {
  echo "[load_test] Mode NORMAL — trafic de fond (Ctrl+C pour arrêter)"
  while true; do
    curl -s "$API/" > /dev/null
    curl -s "$API/items" > /dev/null
    curl -s "$API/items/$((RANDOM % 150))" > /dev/null
    curl -s "$API/health" > /dev/null
    sleep 0.2
  done
}

error_traffic() {
  echo "[load_test] Mode ERRORS — pic d'erreurs 5xx (déclenche HighErrorRate en ~2min)"
  for i in $(seq 1 300); do
    curl -s "$API/error" > /dev/null
    curl -s "$API/" > /dev/null
    sleep 0.05
  done
  echo "[load_test] Pic d'erreurs terminé"
}

slow_traffic() {
  echo "[load_test] Mode SLOW — pic de latence (déclenche HighLatencyP95 en ~3min)"
  for i in $(seq 1 60); do
    curl -s "$API/slow" > /dev/null &
  done
  wait
  echo "[load_test] Pic de latence terminé"
}

all_traffic() {
  echo "[load_test] Mode ALL — trafic mixte continu (Ctrl+C pour arrêter)"
  while true; do
    curl -s "$API/" > /dev/null
    curl -s "$API/items" > /dev/null
    curl -s "$API/items/$((RANDOM % 200))" > /dev/null
    curl -s "$API/error" > /dev/null
    if [ $((RANDOM % 5)) -eq 0 ]; then
      curl -s "$API/slow" > /dev/null &
    fi
    if [ $((RANDOM % 10)) -eq 0 ]; then
      curl -s "$API/cpu-intensive" > /dev/null &
    fi
    sleep 0.1
  done
}

case "$MODE" in
  normal)  normal_traffic ;;
  errors)  error_traffic ;;
  slow)    slow_traffic ;;
  all)     all_traffic ;;
  *)
    echo "Usage: $0 [normal|errors|slow|all]"
    echo "  normal  — trafic de fond continu"
    echo "  errors  — pic d'erreurs 5xx (~300 requêtes)"
    echo "  slow    — pic de latence (~60 requêtes /slow en parallèle)"
    echo "  all     — trafic mixte continu"
    exit 1
    ;;
esac
