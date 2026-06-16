#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".git" ]; then
  echo "Erro: este diretorio nao parece ser um repositorio git: $ROOT_DIR" >&2
  exit 1
fi

# Faz backup dos arquivos de dados das revendas (nao versionados no git)
echo "Fazendo backup dos arquivos de revendas..."
BACKUP_DIR="/tmp/revendas_backup_$(date +%s)"
mkdir -p "$BACKUP_DIR"

# Lista de arquivos JSON das revendas (exceto os versionados)
for file in *.json; do
  # Pula arquivos que nao existem (quando nao ha matches)
  [ -e "$file" ] || continue
  
  # Pula arquivos versionados no git
  if git check-ignore -q "$file" 2>/dev/null || [ "$file" = "revendas_logins.json" ]; then
    cp -v "$file" "$BACKUP_DIR/" 2>/dev/null || true
  fi
done

# Tambem faz backup do Excel consolidado se existir
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

  echo "Limpando cache antigo do Docker..."
  docker builder prune -af >/dev/null 2>&1 || true
  docker image prune -af >/dev/null 2>&1 || true
  docker container prune -f >/dev/null 2>&1 || true
fi

NGINX_SITE="/etc/nginx/sites-available/revendas"
EXPECTED_PROXY="proxy_pass http://127.0.0.1:8080;"

if [ -f "$NGINX_SITE" ] && command -v nginx >/dev/null 2>&1 && command -v systemctl >/dev/null 2>&1; then
  if grep -q "server_name vps64488.publiccloud.com.br" "$NGINX_SITE" && ! grep -q "$EXPECTED_PROXY" "$NGINX_SITE"; then
    echo "Corrigindo proxy do Nginx para a API de revendas..."
    cp "$NGINX_SITE" "${NGINX_SITE}.backup-update-$(date +%Y%m%d-%H%M%S)"
    sed -i 's#proxy_pass http://127\.0\.0\.1:8010;#proxy_pass http://127.0.0.1:8080;#' "$NGINX_SITE"
    nginx -t
    systemctl reload nginx
  fi
fi

echo "OK"
