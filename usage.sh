#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

section() {
  printf '\n==== %s ====\n' "$1"
}

section "Memoria RAM"
free -h || true

section "Disco"
df -h || true

section "Tamanho do projeto"
if [ -d "$PROJECT_DIR" ]; then
  du -sh "$PROJECT_DIR" || true
else
  echo "Diretorio nao encontrado: $PROJECT_DIR"
fi

section "Maiores itens do projeto"
if [ -d "$PROJECT_DIR" ]; then
  du -h --max-depth=1 "$PROJECT_DIR" 2>/dev/null | sort -hr | head -20 || true
fi

section "Docker - uso de disco"
if command -v docker >/dev/null 2>&1; then
  docker system df || true
else
  echo "Docker nao encontrado."
fi

section "Docker - containers"
if command -v docker >/dev/null 2>&1; then
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true
else
  echo "Docker nao encontrado."
fi

section "Docker - recursos agora"
if command -v docker >/dev/null 2>&1; then
  docker stats --no-stream || true
else
  echo "Docker nao encontrado."
fi
