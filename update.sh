#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".git" ]; then
  echo "Erro: este diretório não parece ser um repositório git: $ROOT_DIR" >&2
  exit 1
fi

git fetch origin

BRANCH="${BRANCH:-main}"

if git diff --quiet && git diff --cached --quiet; then
  :
else
  git stash push -u -m "auto-stash: update.sh $(date -Iseconds)" >/dev/null || true
fi

git checkout "$BRANCH" >/dev/null 2>&1 || git checkout -b "$BRANCH"
git reset --hard "origin/$BRANCH"

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    docker compose up -d --build
  else
    docker-compose up -d --build
  fi
fi

echo "OK"
