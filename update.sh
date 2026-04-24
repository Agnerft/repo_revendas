#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".git" ]; then
  echo "Erro: este diretório não parece ser um repositório git: $ROOT_DIR" >&2
  exit 1
fi

# Faz backup dos arquivos de dados das revendas (não versionados no git)
echo "Fazendo backup dos arquivos de revendas..."
BACKUP_DIR="/tmp/revendas_backup_$(date +%s)"
mkdir -p "$BACKUP_DIR"

# Lista de arquivos JSON das revendas (exceto os versionados)
for file in *.json; do
  # Pula arquivos que não existem (quando não há matches)
  [ -e "$file" ] || continue
  
  # Pula arquivos versionados no git
  if git check-ignore -q "$file" 2>/dev/null || [ "$file" = "revendas_logins.json" ]; then
    cp -v "$file" "$BACKUP_DIR/" 2>/dev/null || true
  fi
done

# Também faz backup do Excel consolidado se existir
if [ -f "revendas_consolidadas.xlsx" ]; then
  cp -v "revendas_consolidadas.xlsx" "$BACKUP_DIR/" 2>/dev/null || true
fi

echo "Backup salvo em: $BACKUP_DIR"

git fetch origin

BRANCH="${BRANCH:-main}"

if git diff --quiet && git diff --cached --quiet; then
  :
else
  git stash push -u -m "auto-stash: update.sh $(date -Iseconds)" >/dev/null || true
fi

git checkout "$BRANCH" >/dev/null 2>&1 || git checkout -b "$BRANCH"
git reset --hard "origin/$BRANCH"

# Restaura os arquivos de backup
echo "Restaurando arquivos de revendas..."
if [ -d "$BACKUP_DIR" ]; then
  cp -v "$BACKUP_DIR"/*.json . 2>/dev/null || true
  cp -v "$BACKUP_DIR"/*.xlsx . 2>/dev/null || true
  rm -rf "$BACKUP_DIR"
fi

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    docker compose up -d --build
  else
    docker-compose up -d --build
  fi
fi

echo "OK"
