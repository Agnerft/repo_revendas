from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
import pandas as pd
import os
import json
import re
import unicodedata
import subprocess
import sys
import threading
import time
import requests
from typing import Optional

app = FastAPI(title="ServiÃ§o de Busca de Revendas")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, "revendas_consolidadas.xlsx")
df = None
update_lock = threading.Lock()
update_status = {
    "running": False,
    "status": "idle",
    "message": "Nenhuma atualizacao em andamento.",
    "total": None,
    "returncode": None
}
update_process = None
UPDATE_LOG_FILE = os.path.join(BASE_DIR, "update_all_revendas.log")
GESTOR_LOGIN_PAGE_URL = "https://app.gestorinove.com.br/login"
GESTOR_LOGIN_URL = "https://app.gestorinove.com.br/valida"

class SearchRequest(BaseModel):
    termo: str

class RevendaRequest(BaseModel):
    nome: str
    email: str
    password: str
    filename: Optional[str] = None

class CredenciaisRevendaRequest(BaseModel):
    email_atual: str
    novo_email: str
    nova_senha: Optional[str] = None

def testar_login_gestor(email, password):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        session.get(GESTOR_LOGIN_PAGE_URL, timeout=30)
        response = session.post(
            GESTOR_LOGIN_URL,
            data={"email": email, "senha": password, "redir": ""},
            timeout=30
        )

        if response.url == "https://app.gestorinove.com.br/painel" or "painel" in response.url:
            return True, "Login validado com sucesso."

        if "GESTOR_SESSION" in session.cookies:
            return True, "Login validado por cookie de sessao."

        response_text = unicodedata.normalize("NFKD", response.text).encode("ASCII", "ignore").decode("ASCII")
        response_text = response_text.lower()
        if "erro" in response_text or "invalido" in response_text:
            return False, "Credenciais invalidas no Gestor."

        return False, "Nao foi possivel confirmar o login no Gestor."
    except requests.exceptions.RequestException as e:
        return False, f"Erro ao conectar no Gestor: {e}"
    finally:
        session.close()

def load_data():
    global df
    if os.path.exists(EXCEL_FILE):
        try:
            print(f"Carregando {EXCEL_FILE}...")
            # LÃª todas as colunas como string para facilitar a busca
            df = pd.read_excel(EXCEL_FILE, dtype=str)
            # Preenche NaN com string vazia
            df = df.fillna("")
            print(f"Colunas carregadas: {df.columns.tolist()}")
            print(f"Dados carregados: {len(df)} registros.")
        except Exception as e:
            print(f"Erro ao carregar Excel: {e}")
            df = pd.DataFrame()
    else:
        print(f"Arquivo {EXCEL_FILE} nÃ£o encontrado.")
        df = pd.DataFrame()

# Carrega os dados na inicializaÃ§Ã£o
def start_update_process():
    """Inicia o atualizador sem bloquear o processo da API."""
    global update_process

    script_path = os.path.join(BASE_DIR, "update_all_revendas.py")
    log_file = open(UPDATE_LOG_FILE, "w", encoding="utf-8")
    update_process = subprocess.Popen(
        [sys.executable, script_path],
        cwd=BASE_DIR,
        text=True,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    return update_process

def get_update_log_tail():
    if not os.path.exists(UPDATE_LOG_FILE):
        return ""

    try:
        with open(UPDATE_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[-40:]).strip()
    except Exception as e:
        return f"Erro ao ler log: {e}"

def refresh_update_status():
    global update_process

    with update_lock:
        if update_process is None or not update_status["running"]:
            return update_status

        returncode = update_process.poll()
        if returncode is None:
            return update_status

        update_process = None
        update_status["running"] = False
        update_status["returncode"] = returncode

    if returncode == 0:
        load_data()
        update_status.update({
            "status": "success",
            "message": "Atualizado com sucesso",
            "total": len(df)
        })
    else:
        update_status.update({
            "status": "error",
            "message": get_update_log_tail() or "Falha ao executar update_all_revendas.py"
        })

    return update_status

load_data()

@app.get("/")
def read_root():
    return RedirectResponse(url="/painel")

@app.get("/status")
def status():
    return {
        "message": "API de Busca de Clientes Ativa",
        "total_registros": len(df) if df is not None else 0,
        "uso_post": "POST /buscar com body {'termo': 'valor'}"
    }

PAINEL_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Painel de Revendas</title>
    <style>
        :root {
            --bg: #0b1020;
            --surface: #101827;
            --surface-2: #162033;
            --line: #273449;
            --text: #eef4ff;
            --muted: #97a6ba;
            --soft: #cbd5e1;
            --green: #18b26b;
            --green-soft: rgba(24, 178, 107, 0.15);
            --blue: #3a82f7;
            --blue-soft: rgba(58, 130, 247, 0.15);
            --amber: #f59e0b;
            --amber-soft: rgba(245, 158, 11, 0.14);
            --red: #ef4444;
            --red-soft: rgba(239, 68, 68, 0.14);
            --shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            min-height: 100vh;
            color: var(--text);
            background:
                radial-gradient(circle at 15% 0%, rgba(24, 178, 107, 0.18), transparent 32rem),
                radial-gradient(circle at 90% 10%, rgba(58, 130, 247, 0.14), transparent 30rem),
                var(--bg);
            font-family: Inter, "Segoe UI", Arial, sans-serif;
        }

        button, input {
            font: inherit;
        }

        .shell {
            display: grid;
            grid-template-columns: 280px minmax(0, 1fr);
            min-height: 100vh;
        }

        .sidebar {
            position: sticky;
            top: 0;
            height: 100vh;
            padding: 28px 22px;
            border-right: 1px solid var(--line);
            background: rgba(12, 18, 32, 0.88);
            backdrop-filter: blur(18px);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 28px;
        }

        .brand-mark {
            display: grid;
            place-items: center;
            width: 42px;
            height: 42px;
            border-radius: 8px;
            color: #082013;
            background: linear-gradient(135deg, #5ee2a0, #54a4ff);
            font-weight: 900;
        }

        .brand-title {
            margin: 0;
            font-size: 18px;
            line-height: 1.15;
        }

        .brand-subtitle {
            margin: 3px 0 0;
            color: var(--muted);
            font-size: 13px;
        }

        .nav-label {
            color: #6f7f94;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .nav {
            display: grid;
            gap: 8px;
            margin-bottom: 26px;
        }

        .nav button {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            width: 100%;
            padding: 11px 12px;
            border: 1px solid transparent;
            border-radius: 8px;
            color: var(--soft);
            background: transparent;
            cursor: pointer;
            text-align: left;
        }

        .nav button:hover,
        .nav button.active {
            color: var(--text);
            background: var(--surface-2);
            border-color: var(--line);
        }

        .nav-count {
            color: var(--muted);
            font-size: 12px;
        }

        .side-note {
            margin-top: auto;
            padding: 14px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--surface);
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
        }

        main {
            padding: 30px;
        }

        .topbar {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 22px;
        }

        h1 {
            margin: 0;
            font-size: clamp(28px, 4vw, 44px);
            line-height: 1;
            letter-spacing: 0;
        }

        .lead {
            max-width: 780px;
            margin: 12px 0 0;
            color: var(--muted);
            font-size: 15px;
            line-height: 1.55;
        }

        .toolbar {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        .btn {
            min-height: 40px;
            padding: 0 14px;
            border: 1px solid var(--line);
            border-radius: 8px;
            color: var(--text);
            background: var(--surface-2);
            cursor: pointer;
            transition: transform .18s ease, border-color .18s ease, background .18s ease;
        }

        .btn:hover {
            transform: translateY(-1px);
            border-color: #40516b;
        }

        .btn.primary {
            border-color: rgba(24, 178, 107, .45);
            background: var(--green);
            color: white;
            font-weight: 800;
        }

        .btn.danger {
            border-color: rgba(239, 68, 68, .5);
            background: var(--red);
            color: white;
            font-weight: 800;
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin-bottom: 18px;
        }

        .stat {
            min-height: 112px;
            padding: 18px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(16, 24, 39, .82);
            box-shadow: var(--shadow);
        }

        .stat-label {
            color: var(--muted);
            font-size: 12px;
            font-weight: 800;
            letter-spacing: .07em;
            text-transform: uppercase;
        }

        .stat-value {
            margin-top: 12px;
            font-size: 30px;
            font-weight: 900;
        }

        .stat-helper {
            margin-top: 7px;
            color: var(--muted);
            font-size: 13px;
        }

        .workspace {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 360px;
            gap: 18px;
            align-items: start;
        }

        .panel {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(16, 24, 39, .82);
            box-shadow: var(--shadow);
        }

        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 16px;
            border-bottom: 1px solid var(--line);
        }

        .panel-title {
            margin: 0;
            font-size: 16px;
        }

        .search {
            width: min(360px, 100%);
            padding: 10px 12px;
            border: 1px solid var(--line);
            border-radius: 8px;
            outline: none;
            color: var(--text);
            background: #0b1322;
        }

        .search:focus,
        .field input:focus {
            border-color: var(--blue);
            box-shadow: 0 0 0 3px rgba(58, 130, 247, 0.14);
        }

        .endpoint-list {
            display: grid;
            gap: 12px;
            padding: 16px;
        }

        .endpoint-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #0d1524;
            overflow: hidden;
        }

        .endpoint-main {
            display: grid;
            grid-template-columns: 96px minmax(0, 1fr) auto;
            gap: 14px;
            align-items: start;
            padding: 16px;
        }

        .method {
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 72px;
            min-height: 28px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 900;
            color: white;
        }

        .method.get { background: var(--green); }
        .method.post { background: var(--blue); }
        .method.delete { background: var(--red); }

        .endpoint-path {
            margin: 0 0 6px;
            font-family: Consolas, "Courier New", monospace;
            font-size: 16px;
            color: white;
            overflow-wrap: anywhere;
        }

        .endpoint-desc {
            margin: 0;
            color: var(--muted);
            line-height: 1.45;
            font-size: 14px;
        }

        .endpoint-body {
            display: none;
            border-top: 1px solid var(--line);
            padding: 16px;
            background: #0a111f;
        }

        .endpoint-card.open .endpoint-body {
            display: grid;
            gap: 14px;
        }

        pre {
            margin: 0;
            padding: 14px;
            border: 1px solid #1f2d42;
            border-radius: 8px;
            overflow: auto;
            color: #dbeafe;
            background: #07101d;
            font-family: Consolas, "Courier New", monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        .field {
            display: grid;
            gap: 7px;
        }

        .field label {
            color: var(--soft);
            font-size: 13px;
            font-weight: 700;
        }

        .field input {
            width: 100%;
            padding: 11px 12px;
            border: 1px solid var(--line);
            border-radius: 8px;
            outline: none;
            color: var(--text);
            background: #0b1322;
        }

        .actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .response {
            display: none;
            padding: 14px;
            border-radius: 8px;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: Consolas, "Courier New", monospace;
            font-size: 13px;
            line-height: 1.45;
        }

        .response.show { display: block; }
        .response.loading { color: #fef3c7; background: var(--amber-soft); border: 1px solid rgba(245, 158, 11, .35); }
        .response.success { color: #b7f7d4; background: var(--green-soft); border: 1px solid rgba(24, 178, 107, .36); }
        .response.error { color: #fecaca; background: var(--red-soft); border: 1px solid rgba(239, 68, 68, .38); }

        .quick-card {
            padding: 16px;
            display: grid;
            gap: 14px;
        }

        .quick-title {
            margin: 0;
            font-size: 15px;
        }

        .quick-text {
            margin: 0;
            color: var(--muted);
            font-size: 14px;
            line-height: 1.45;
        }

        .update-log {
            max-height: 360px;
            overflow: auto;
        }

        .empty {
            padding: 26px;
            text-align: center;
            color: var(--muted);
        }

        @media (max-width: 1080px) {
            .shell { grid-template-columns: 1fr; }
            .sidebar {
                position: static;
                height: auto;
                border-right: 0;
                border-bottom: 1px solid var(--line);
            }
            .workspace { grid-template-columns: 1fr; }
            .status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }

        @media (max-width: 720px) {
            main { padding: 18px; }
            .topbar,
            .panel-header {
                align-items: stretch;
                flex-direction: column;
            }
            .toolbar { justify-content: stretch; }
            .toolbar .btn { flex: 1; }
            .status-grid { grid-template-columns: 1fr; }
            .endpoint-main { grid-template-columns: 1fr; }
            .endpoint-main .btn { width: 100%; }
        }

        body {
            color: #172033;
            background: #f4f7fb;
        }

        .shell {
            display: block;
            min-height: 100vh;
        }

        .sidebar {
            display: none;
        }

        .workspace {
            display: none;
            grid-template-columns: minmax(0, 1fr) 340px;
            margin-top: 18px;
        }

        .workspace.show {
            display: grid;
        }

        main {
            width: min(1120px, calc(100% - 32px));
            margin: 0 auto;
            padding: 34px 0 54px;
        }

        .topbar {
            align-items: center;
            margin-bottom: 18px;
        }

        h1 {
            color: #111827;
            font-size: clamp(26px, 3vw, 38px);
        }

        .lead {
            max-width: 620px;
            color: #667085;
        }

        .btn {
            color: #263244;
            background: #fff;
            border-color: #d7deea;
            box-shadow: 0 1px 2px rgba(16, 24, 40, .06);
        }

        .btn.primary {
            color: #fff;
            background: #166534;
            border-color: #166534;
        }

        .status-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin: 18px 0;
        }

        .stat,
        .panel {
            color: #172033;
            background: #fff;
            border-color: #e4e9f2;
            box-shadow: 0 14px 36px rgba(16, 24, 40, .08);
        }

        .stat-value {
            color: #111827;
            font-size: 28px;
        }

        .stat-label,
        .stat-helper {
            color: #667085;
        }

        .unified {
            padding: 22px;
            border: 1px solid #e4e9f2;
            border-radius: 8px;
            background: #fff;
            box-shadow: 0 14px 36px rgba(16, 24, 40, .08);
        }

        .unified-form {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 10px;
            margin-top: 14px;
        }

        .unified-input {
            width: 100%;
            min-height: 48px;
            padding: 0 14px;
            border: 1px solid #cfd8e6;
            border-radius: 8px;
            outline: none;
            color: #111827;
            background: #fff;
        }

        .unified-input:focus {
            border-color: #166534;
            box-shadow: 0 0 0 3px rgba(22, 101, 52, .12);
        }

        .unified-title {
            margin: 0;
            color: #111827;
            font-size: 18px;
        }

        .unified-text {
            margin: 6px 0 0;
            color: #667085;
            line-height: 1.45;
        }

        .results {
            display: none;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-top: 16px;
        }

        .results.show {
            display: grid;
        }

        .result-card {
            min-height: 250px;
            padding: 18px;
            border: 1px solid #e4e9f2;
            border-radius: 8px;
            background: #fbfcfe;
        }

        .result-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
        }

        .result-title {
            margin: 0;
            color: #111827;
            font-size: 16px;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            min-height: 26px;
            padding: 0 9px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 800;
        }

        .badge.ok {
            color: #166534;
            background: #dcfce7;
        }

        .badge.warn {
            color: #92400e;
            background: #fef3c7;
        }

        .badge.err {
            color: #991b1b;
            background: #fee2e2;
        }

        .data-grid {
            display: grid;
            gap: 10px;
        }

        .data-row {
            display: grid;
            grid-template-columns: 128px minmax(0, 1fr);
            gap: 12px;
            padding-bottom: 9px;
            border-bottom: 1px solid #edf1f7;
        }

        .data-row:last-child {
            border-bottom: 0;
            padding-bottom: 0;
        }

        .data-label {
            color: #667085;
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
        }

        .data-value {
            color: #172033;
            overflow-wrap: anywhere;
        }

        .empty-result {
            color: #667085;
            line-height: 1.5;
        }

        .raw-toggle {
            margin-top: 14px;
            color: #475467;
            background: transparent;
            border: 0;
            padding: 0;
            cursor: pointer;
            font-weight: 700;
        }

        .raw-output {
            display: none;
            margin-top: 12px;
            color: #344054;
            background: #f7f9fc;
            border-color: #e4e9f2;
        }

        .raw-output.show {
            display: block;
        }

        .value-link {
            display: inline-flex;
            align-items: center;
            min-height: 32px;
            padding: 0 10px;
            border-radius: 8px;
            color: #fff;
            background: #166534;
            text-decoration: none;
            font-weight: 800;
        }

        .theme-toggle {
            min-width: 122px;
        }

        .workspace .panel {
            box-shadow: none;
        }

        .workspace .endpoint-card,
        .workspace pre,
        .workspace .endpoint-body {
            background: #fff;
            color: #172033;
            border-color: #e4e9f2;
        }

        .workspace .endpoint-path {
            color: #111827;
        }

        .workspace .search,
        .workspace .field input {
            color: #111827;
            background: #fff;
            border-color: #cfd8e6;
        }

        body.theme-dark {
            color: #e5edf8;
            background: #0b1020;
        }

        body.theme-dark h1,
        body.theme-dark .unified-title,
        body.theme-dark .result-title,
        body.theme-dark .stat-value,
        body.theme-dark .panel-title,
        body.theme-dark .endpoint-path {
            color: #f8fafc;
        }

        body.theme-dark .lead,
        body.theme-dark .unified-text,
        body.theme-dark .stat-label,
        body.theme-dark .stat-helper,
        body.theme-dark .data-label,
        body.theme-dark .endpoint-desc,
        body.theme-dark .quick-text,
        body.theme-dark .empty-result {
            color: #9aa8bb;
        }

        body.theme-dark .unified,
        body.theme-dark .stat,
        body.theme-dark .panel,
        body.theme-dark .result-card,
        body.theme-dark .endpoint-card {
            color: #e5edf8;
            background: #111827;
            border-color: #263244;
            box-shadow: 0 14px 36px rgba(0, 0, 0, .24);
        }

        body.theme-dark .result-card,
        body.theme-dark .workspace .endpoint-card,
        body.theme-dark .workspace pre,
        body.theme-dark .workspace .endpoint-body,
        body.theme-dark .raw-output {
            background: #0f172a;
            color: #dbeafe;
            border-color: #263244;
        }

        body.theme-dark .btn,
        body.theme-dark .unified-input,
        body.theme-dark .workspace .search,
        body.theme-dark .workspace .field input {
            color: #e5edf8;
            background: #0f172a;
            border-color: #334155;
        }

        body.theme-dark .btn.primary,
        body.theme-dark .value-link {
            background: #18b26b;
            border-color: #18b26b;
            color: #052e16;
        }

        body.theme-dark .data-row {
            border-color: #263244;
        }

        body.theme-dark .data-value {
            color: #e5edf8;
        }

        @media (max-width: 820px) {
            main {
                width: min(100% - 22px, 1120px);
                padding-top: 22px;
            }

            .topbar,
            .unified-form {
                grid-template-columns: 1fr;
                flex-direction: column;
                align-items: stretch;
            }

            .status-grid,
            .results {
                grid-template-columns: 1fr;
            }

            .workspace,
            .workspace.show {
                grid-template-columns: 1fr;
            }

            .data-row {
                grid-template-columns: 1fr;
                gap: 4px;
            }
        }
    </style>
</head>
<body>
    <div class="shell">
        <aside class="sidebar">
            <div class="brand">
                <div class="brand-mark">RV</div>
                <div>
                    <h2 class="brand-title">Revendas API</h2>
                    <p class="brand-subtitle">Painel operacional</p>
                </div>
            </div>

            <div class="nav-label">Filtros</div>
            <nav class="nav" id="navFilters">
                <button class="active" data-filter="all">Todos <span class="nav-count" id="countAll">0</span></button>
                <button data-filter="GET">GET <span class="nav-count" id="countGet">0</span></button>
                <button data-filter="POST">POST <span class="nav-count" id="countPost">0</span></button>
                <button data-filter="DELETE">DELETE <span class="nav-count" id="countDelete">0</span></button>
            </nav>

            <div class="side-note">
                Use este painel para consultar clientes, listar revendas, recarregar a planilha e acompanhar atualizacoes sem abrir o Postman.
            </div>
        </aside>

        <main>
            <section class="topbar">
                <div>
                    <h1>Consulta de cliente</h1>
                    <p class="lead">Pesquise uma vez e veja o retorno da base de linhas e do MaxPlayer no mesmo lugar.</p>
                </div>
                <div class="toolbar">
                    <button class="btn theme-toggle" id="themeToggleBtn">Modo escuro</button>
                    <button class="btn" id="toggleEndpointsBtn">Endpoints</button>
                    <button class="btn" id="refreshStatusBtn">Atualizar status</button>
                    <button class="btn primary" id="runUpdateBtn">Atualizar dados</button>
                </div>
            </section>

            <section class="unified">
                <h2 class="unified-title">Pesquisa unificada</h2>
                <p class="unified-text">Digite telefone, usuario, ID ou email. Para a base de linhas, a busca usa apenas os numeros do telefone.</p>
                <form class="unified-form" id="clientSearchForm">
                    <input class="unified-input" id="clientSearchInput" type="search" placeholder="Ex: 5521999999999 ou usuario MaxPlayer" autocomplete="off">
                    <button class="btn primary" id="clientSearchButton" type="submit">Pesquisar</button>
                </form>
                <div class="results" id="clientResults">
                    <article class="result-card" id="resellerResult"></article>
                    <article class="result-card" id="lineResult"></article>
                    <article class="result-card" id="maxplayerResult"></article>
                </div>
            </section>

            <section class="status-grid">
                <article class="stat">
                    <div class="stat-label">Registros</div>
                    <div class="stat-value" id="totalRegs">-</div>
                    <div class="stat-helper">Carregados do Excel</div>
                </article>
                <article class="stat">
                    <div class="stat-label">Endpoints</div>
                    <div class="stat-value" id="endpointTotal">-</div>
                    <div class="stat-helper">Disponiveis neste painel</div>
                </article>
                <article class="stat">
                    <div class="stat-label">API</div>
                    <div class="stat-value" id="apiState">-</div>
                    <div class="stat-helper" id="apiMessage">Verificando...</div>
                </article>
                <article class="stat">
                    <div class="stat-label">Atualizacao</div>
                    <div class="stat-value" id="updateState">Idle</div>
                    <div class="stat-helper" id="updateMessage">Nenhuma execucao ativa</div>
                </article>
            </section>

            <section class="workspace">
                <div class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Endpoints</h2>
                        <input class="search" id="searchInput" type="search" placeholder="Buscar endpoint ou descricao">
                    </div>
                    <div class="endpoint-list" id="endpointList"></div>
                    <div class="empty" id="emptyState" hidden>Nenhum endpoint encontrado.</div>
                </div>

                <aside class="panel">
                    <div class="panel-header">
                        <h2 class="panel-title">Execucao recente</h2>
                    </div>
                    <div class="quick-card">
                        <p class="quick-title">Status do atualizador</p>
                        <p class="quick-text">Ao iniciar a atualizacao, o painel acompanha o processo em segundo plano e mostra o retorno mais recente.</p>
                        <pre class="update-log" id="updateLog">Aguardando acao.</pre>
                    </div>
                </aside>
            </section>
        </main>
    </div>

    <script>
        const VERSION = '3.0';
        const endpoints = [
            {
                method: 'GET',
                path: '/status',
                description: 'Retorna o status da API e o total de registros carregados.',
                sample: '{\\n  "message": "API de Busca de Clientes Ativa",\\n  "total_registros": 42860\\n}',
                action: { type: 'request', label: 'Testar', endpoint: '/status', responseId: 'r-status' }
            },
            {
                method: 'POST',
                path: '/buscar',
                description: 'Busca um cliente em todas as colunas pelo termo informado.',
                sample: 'Body: { "termo": "+5551999999999" }\\n\\nRetorna o primeiro cliente encontrado.',
                field: { id: 'buscarTermo', label: 'Termo de busca', placeholder: 'Telefone, nome ou ID' },
                action: { type: 'postTerm', label: 'Buscar', endpoint: '/buscar', inputId: 'buscarTermo', responseId: 'r-buscar' }
            },
            {
                method: 'POST',
                path: '/filtrar',
                description: 'Retorna uma lista com todos os clientes encontrados. Bom para busca por data.',
                sample: 'Body: { "termo": "19/08/2025" }\\n\\nRetorna: [ { ... }, { ... } ]',
                field: { id: 'filtrarTermo', label: 'Filtro', placeholder: 'Data, nome, telefone ou termo' },
                action: { type: 'postTerm', label: 'Filtrar', endpoint: '/filtrar', inputId: 'filtrarTermo', responseId: 'r-filtrar' }
            },
            {
                method: 'POST',
                path: '/cliente/consulta',
                description: 'Consulta revendas, link de pagamento, linhas e MaxPlayer em uma unica pesquisa.',
                sample: 'Body: { "termo": "5521999999999" }\\n\\nRetorna: revenda, linha e maxplayer.',
                field: { id: 'consultaUnificadaTermo', label: 'Termo', placeholder: 'Telefone, usuario, ID ou email' },
                action: { type: 'postTerm', label: 'Consultar tudo', endpoint: '/cliente/consulta', inputId: 'consultaUnificadaTermo', responseId: 'r-consulta-unificada' }
            },
            {
                method: 'GET',
                path: '/reload',
                description: 'Recarrega os dados do Excel sem reiniciar o servidor.',
                sample: '{\\n  "message": "Dados recarregados.",\\n  "total_registros": 42860\\n}',
                action: { type: 'request', label: 'Recarregar', endpoint: '/reload', responseId: 'r-reload' }
            },
            {
                method: 'POST',
                path: '/atualizar',
                description: 'Executa o script update_all_revendas.py para atualizar todos os dados.',
                sample: '{\\n  "message": "Atualizacao iniciada em segundo plano",\\n  "status_url": "/atualizar/status"\\n}',
                action: { type: 'update', label: 'Atualizar dados', responseId: 'r-atualizar' }
            },
            {
                method: 'GET',
                path: '/atualizar/status',
                description: 'Consulta o andamento da atualizacao em segundo plano.',
                sample: '{\\n  "running": false,\\n  "status": "success",\\n  "message": "Atualizado com sucesso"\\n}',
                action: { type: 'request', label: 'Ver status', endpoint: '/atualizar/status', responseId: 'r-atualizar-status' }
            },
            {
                method: 'GET',
                path: '/revenda/adicionar',
                description: 'Mostra a documentacao para adicionar uma nova revenda.',
                sample: 'Retorna instrucoes de uso do POST /revenda/adicionar.',
                action: { type: 'request', label: 'Ver instrucoes', endpoint: '/revenda/adicionar', responseId: 'r-add-doc' }
            },
            {
                method: 'POST',
                path: '/revenda/adicionar',
                description: 'Adiciona uma nova revenda ao arquivo de logins.',
                sample: 'Body: {\\n  "nome": "Revenda XYZ",\\n  "email": "revenda@email.com",\\n  "password": "senha123",\\n  "filename": "opcional.json"\\n}',
                action: { type: 'manual', label: 'Usar via API', responseId: 'r-add' }
            },
            {
                method: 'POST',
                path: '/ (alias)',
                description: 'Alias para /buscar. Busca cliente pelo termo enviado.',
                sample: 'Body: { "termo": "valor" }\\n\\nRetorna o cliente encontrado.',
                field: { id: 'aliasTermo', label: 'Termo', placeholder: 'Digite o termo de busca' },
                action: { type: 'postTerm', label: 'Testar alias', endpoint: '/', inputId: 'aliasTermo', responseId: 'r-alias' }
            },
            {
                method: 'GET',
                path: '/consultar-linha/{telefone}',
                description: 'Consulta API externa de linhas pelo numero de telefone.',
                sample: 'Exemplo: /consultar-linha/5511999999999\\n\\nRetorna dados da linha na API externa.',
                field: { id: 'linhaTelefone', label: 'Telefone', placeholder: 'Telefone com DDD' },
                action: { type: 'phone', label: 'Consultar linha', inputId: 'linhaTelefone', responseId: 'r-linha' }
            },
            {
                method: 'POST',
                path: '/maxplayer/usuario',
                description: 'Pesquisa se um usuario existe na base do MaxPlayer.',
                sample: 'Body: { "termo": "5521999999999" }\\n\\nBusca por usuario, ID, email ou usuario IPTV vinculado.',
                field: { id: 'maxplayerUsuario', label: 'Usuario MaxPlayer', placeholder: 'Usuario, telefone, ID ou email' },
                action: { type: 'postTerm', label: 'Pesquisar MaxPlayer', endpoint: '/maxplayer/usuario', inputId: 'maxplayerUsuario', responseId: 'r-maxplayer' }
            },
            {
                method: 'GET',
                path: '/revenda/listar',
                description: 'Lista todas as revendas cadastradas com total de clientes.',
                sample: '{\\n  "total": 5,\\n  "revendas": [\\n    { "nome": "...", "email": "...", "total_clientes": 150 }\\n  ]\\n}',
                action: { type: 'request', label: 'Listar revendas', endpoint: '/revenda/listar', responseId: 'r-listar' }
            },
            {
                method: 'DELETE',
                path: '/revenda/excluir',
                description: 'Exclui uma revenda pelo email e remove o arquivo JSON relacionado.',
                sample: 'Body: { "email": "revenda@email.com" }\\n\\nAtencao: esta acao nao pode ser desfeita.',
                field: { id: 'deleteEmail', label: 'Email da revenda', placeholder: 'revenda@email.com', type: 'email' },
                action: { type: 'delete', label: 'Excluir revenda', inputId: 'deleteEmail', responseId: 'r-delete' }
            }
        ];

        let activeFilter = 'all';
        let updateTimer = null;

        const endpointList = document.getElementById('endpointList');
        const emptyState = document.getElementById('emptyState');
        const searchInput = document.getElementById('searchInput');

        function escapeHtml(value) {
            return String(value)
                .replaceAll('&', '&amp;')
                .replaceAll('<', '&lt;')
                .replaceAll('>', '&gt;')
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#039;');
        }

        function setResponse(id, state, message) {
            const el = document.getElementById(id);
            if (!el) return;
            el.className = 'response show ' + state;
            el.textContent = message;
        }

        async function requestJson(endpoint, options = {}) {
            const separator = endpoint.includes('?') ? '&' : '?';
            const response = await fetch(endpoint + separator + 'v=' + VERSION, options);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(JSON.stringify(data, null, 2));
            }
            return data;
        }

        function pretty(data) {
            return JSON.stringify(data, null, 2);
        }

        function normalizeStatus(status) {
            if (status === 'sucesso') return { label: 'Encontrado', className: 'ok' };
            if (status === 'erro') return { label: 'Erro', className: 'err' };
            if (status === 'ignorado') return { label: 'Ignorado', className: 'warn' };
            return { label: 'Nao encontrado', className: 'warn' };
        }

        function emptyValue(value) {
            return value === undefined || value === null || value === '' ? 'N/A' : value;
        }

        function dataRows(rows) {
            return `
                <div class="data-grid">
                    ${rows.map((row) => `
                        <div class="data-row">
                            <div class="data-label">${escapeHtml(row[0])}</div>
                            <div class="data-value">${row[2] === 'link' && row[1] && row[1] !== 'nao_encontrado' ? `<a class="value-link" href="${escapeHtml(row[1])}" target="_blank" rel="noopener">Abrir link</a>` : escapeHtml(emptyValue(row[1]))}</div>
                        </div>
                    `).join('')}
                </div>`;
        }

        function renderResultCard(targetId, title, status, rows, emptyMessage, rawData) {
            const target = document.getElementById(targetId);
            const badge = normalizeStatus(status);
            const rawId = targetId + '-raw';
            target.innerHTML = `
                <div class="result-head">
                    <h3 class="result-title">${escapeHtml(title)}</h3>
                    <span class="badge ${badge.className}">${escapeHtml(badge.label)}</span>
                </div>
                ${rows.length ? dataRows(rows) : `<p class="empty-result">${escapeHtml(emptyMessage)}</p>`}
                <button class="raw-toggle" type="button" data-raw-target="${rawId}">Ver JSON</button>
                <pre class="raw-output" id="${rawId}">${escapeHtml(pretty(rawData))}</pre>
            `;
        }

        function renderResellerResult(data) {
            const revenda = data.revenda || {};
            const rows = revenda.status === 'sucesso' ? [
                ['Cliente', revenda.nome],
                ['Telefone', revenda.telefone],
                ['Revenda', revenda.Revenda],
                ['Plano', revenda.plano],
                ['Vencimento', revenda.data_expiracao],
                ['ID cliente', revenda.Id_client],
                ['DT Row', revenda.DT_RowId],
                ['Pagamento', revenda.Link, 'link']
            ] : [];

            renderResultCard(
                'resellerResult',
                'Revenda e pagamento',
                revenda.status,
                rows,
                revenda.mensagem || 'Nenhum cadastro encontrado na base das revendas.',
                revenda
            );
        }

        function renderLineResult(data) {
            const linha = data.linha || {};
            const detalhe = linha.linha || {};
            const rows = linha.status === 'sucesso' ? [
                ['Telefone', detalhe.telefone],
                ['Usuario', detalhe.usuario],
                ['Senha', detalhe.senha],
                ['Vencimento', detalhe.vencimento],
                ['Dias restantes', detalhe.dias_restantes],
                ['Status', detalhe.status_conta],
                ['Teste', detalhe.e_teste],
                ['Revenda', detalhe.revenda]
            ] : [];

            renderResultCard(
                'lineResult',
                'Base de linhas',
                linha.status,
                rows,
                linha.mensagem || 'Nenhuma linha encontrada com este telefone.',
                linha
            );
        }

        function renderMaxplayerResult(data) {
            const maxplayer = data.maxplayer || {};
            const user = (maxplayer.usuarios || [])[0] || {};
            const list = (user.listas || [])[0] || {};
            const iptv = list.iptv || {};
            const rows = maxplayer.status === 'sucesso' ? [
                ['Usuario', user.usuario],
                ['ID', user.id],
                ['Email', user.email],
                ['Lista', list.nome],
                ['Dominio', iptv.fqdn],
                ['Porta', iptv.porta],
                ['Usuario IPTV', iptv.usuario],
                ['Senha IPTV', iptv.senha],
                ['Encontrados', maxplayer.total_encontrado],
                ['Cache', maxplayer.cache]
            ] : [];

            renderResultCard(
                'maxplayerResult',
                'MaxPlayer',
                maxplayer.status,
                rows,
                maxplayer.mensagem || 'Nenhum usuario encontrado no MaxPlayer.',
                maxplayer
            );
        }

        async function runUnifiedSearch(term) {
            const button = document.getElementById('clientSearchButton');
            const results = document.getElementById('clientResults');

            button.disabled = true;
            button.textContent = 'Pesquisando...';
            results.classList.add('show');
            renderResultCard('resellerResult', 'Revenda e pagamento', 'ignorado', [], 'Consultando base das revendas...', {});
            renderResultCard('lineResult', 'Base de linhas', 'ignorado', [], 'Consultando base de linhas...', {});
            renderResultCard('maxplayerResult', 'MaxPlayer', 'ignorado', [], 'Consultando MaxPlayer...', {});

            try {
                const data = await requestJson('/cliente/consulta', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ termo: term })
                });
                renderResellerResult(data);
                renderLineResult(data);
                renderMaxplayerResult(data);
            } catch (error) {
                renderResultCard('resellerResult', 'Revenda e pagamento', 'erro', [], error.message, {});
                renderResultCard('lineResult', 'Base de linhas', 'erro', [], error.message, {});
                renderResultCard('maxplayerResult', 'MaxPlayer', 'erro', [], error.message, {});
            } finally {
                button.disabled = false;
                button.textContent = 'Pesquisar';
            }
        }

        async function runRequest(action, method = 'GET') {
            setResponse(action.responseId, 'loading', 'Carregando...');
            try {
                const data = await requestJson(action.endpoint, { method });
                setResponse(action.responseId, 'success', pretty(data));
                if (action.endpoint === '/status' || action.endpoint === '/reload') {
                    await loadStats();
                }
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
            }
        }

        async function runPostTerm(action) {
            const value = document.getElementById(action.inputId).value.trim();
            if (!value) {
                setResponse(action.responseId, 'error', 'Digite um termo para continuar.');
                return;
            }
            setResponse(action.responseId, 'loading', 'Buscando...');
            try {
                const data = await requestJson(action.endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ termo: value })
                });
                setResponse(action.responseId, 'success', pretty(data));
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
            }
        }

        async function runPhone(action) {
            const value = document.getElementById(action.inputId).value.trim();
            const phone = value.replace(/\\D/g, '');
            if (!phone) {
                setResponse(action.responseId, 'error', 'Digite um telefone para continuar.');
                return;
            }
            setResponse(action.responseId, 'loading', 'Consultando linha...');
            try {
                const data = await requestJson('/consultar-linha/' + phone);
                setResponse(action.responseId, 'success', pretty(data));
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
            }
        }

        async function runDelete(action) {
            const email = document.getElementById(action.inputId).value.trim();
            if (!email) {
                setResponse(action.responseId, 'error', 'Digite o email da revenda.');
                return;
            }
            if (!confirm('Tem certeza que deseja excluir a revenda ' + email + '?\\n\\nEsta acao nao pode ser desfeita.')) {
                return;
            }
            setResponse(action.responseId, 'loading', 'Excluindo revenda...');
            try {
                const data = await requestJson('/revenda/excluir', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                setResponse(action.responseId, data.status === 'sucesso' ? 'success' : 'error', pretty(data));
                if (data.status === 'sucesso') {
                    document.getElementById(action.inputId).value = '';
                }
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
            }
        }

        async function runUpdate(action) {
            setResponse(action.responseId, 'loading', 'Iniciando atualizacao...');
            try {
                const data = await requestJson('/atualizar', { method: 'POST' });
                setResponse(action.responseId, 'success', pretty(data));
                document.getElementById('updateLog').textContent = pretty(data);
                await pollUpdateStatus(true);
            } catch (error) {
                setResponse(action.responseId, 'error', error.message);
                await pollUpdateStatus(false);
            }
        }

        function runManual(action) {
            setResponse(action.responseId, 'loading', 'Este endpoint precisa de nome, email, senha e filename opcional. Use um cliente HTTP para enviar o JSON completo.');
        }

        async function handleAction(action) {
            if (action.type === 'request') return runRequest(action);
            if (action.type === 'postTerm') return runPostTerm(action);
            if (action.type === 'phone') return runPhone(action);
            if (action.type === 'delete') return runDelete(action);
            if (action.type === 'update') return runUpdate(action);
            return runManual(action);
        }

        function renderEndpoints() {
            const term = searchInput.value.trim().toLowerCase();
            const visible = endpoints.filter((item) => {
                const matchesFilter = activeFilter === 'all' || item.method === activeFilter;
                const content = (item.method + ' ' + item.path + ' ' + item.description).toLowerCase();
                return matchesFilter && content.includes(term);
            });

            endpointList.innerHTML = visible.map((item, index) => {
                const field = item.field ? `
                    <div class="field">
                        <label for="${item.field.id}">${escapeHtml(item.field.label)}</label>
                        <input id="${item.field.id}" type="${item.field.type || 'text'}" placeholder="${escapeHtml(item.field.placeholder)}">
                    </div>` : '';
                return `
                    <article class="endpoint-card" data-index="${endpoints.indexOf(item)}">
                        <div class="endpoint-main">
                            <span class="method ${item.method.toLowerCase()}">${item.method}</span>
                            <div>
                                <h3 class="endpoint-path">${escapeHtml(item.path)}</h3>
                                <p class="endpoint-desc">${escapeHtml(item.description)}</p>
                            </div>
                            <button class="btn" data-toggle="${index}">Detalhes</button>
                        </div>
                        <div class="endpoint-body">
                            <pre>${escapeHtml(item.sample)}</pre>
                            ${field}
                            <div class="actions">
                                <button class="btn ${item.method === 'DELETE' ? 'danger' : 'primary'}" data-action-index="${endpoints.indexOf(item)}">${escapeHtml(item.action.label)}</button>
                            </div>
                            <div class="response" id="${item.action.responseId}"></div>
                        </div>
                    </article>`;
            }).join('');

            emptyState.hidden = visible.length !== 0;
            document.getElementById('endpointTotal').textContent = endpoints.length;
        }

        function updateCounts() {
            document.getElementById('countAll').textContent = endpoints.length;
            document.getElementById('countGet').textContent = endpoints.filter((item) => item.method === 'GET').length;
            document.getElementById('countPost').textContent = endpoints.filter((item) => item.method === 'POST').length;
            document.getElementById('countDelete').textContent = endpoints.filter((item) => item.method === 'DELETE').length;
        }

        async function loadStats() {
            try {
                const data = await requestJson('/status');
                document.getElementById('totalRegs').textContent = Number(data.total_registros || 0).toLocaleString('pt-BR');
                document.getElementById('apiState').textContent = 'Online';
                document.getElementById('apiMessage').textContent = data.message || 'API respondendo';
            } catch (error) {
                document.getElementById('totalRegs').textContent = '?';
                document.getElementById('apiState').textContent = 'Erro';
                document.getElementById('apiMessage').textContent = 'Nao foi possivel consultar /status';
            }
        }

        async function pollUpdateStatus(keepPolling) {
            try {
                const data = await requestJson('/atualizar/status');
                document.getElementById('updateState').textContent = data.running ? 'Rodando' : (data.status || 'Idle');
                document.getElementById('updateMessage').textContent = data.message || 'Sem detalhes';
                document.getElementById('updateLog').textContent = pretty(data);

                if (data.running || keepPolling) {
                    window.clearTimeout(updateTimer);
                    updateTimer = window.setTimeout(() => pollUpdateStatus(false), 2500);
                } else if (data.status === 'success') {
                    await loadStats();
                }
            } catch (error) {
                document.getElementById('updateState').textContent = 'Erro';
                document.getElementById('updateMessage').textContent = 'Falha ao consultar status';
                document.getElementById('updateLog').textContent = error.message;
            }
        }

        document.getElementById('navFilters').addEventListener('click', (event) => {
            const button = event.target.closest('button[data-filter]');
            if (!button) return;
            activeFilter = button.dataset.filter;
            document.querySelectorAll('#navFilters button').forEach((item) => item.classList.toggle('active', item === button));
            renderEndpoints();
        });

        document.getElementById('clientSearchForm').addEventListener('submit', async (event) => {
            event.preventDefault();
            const term = document.getElementById('clientSearchInput').value.trim();
            if (!term) {
                document.getElementById('clientSearchInput').focus();
                return;
            }
            await runUnifiedSearch(term);
        });

        document.getElementById('themeToggleBtn').addEventListener('click', () => {
            const isDark = document.body.classList.toggle('theme-dark');
            localStorage.setItem('painel-theme', isDark ? 'dark' : 'light');
            document.getElementById('themeToggleBtn').textContent = isDark ? 'Modo claro' : 'Modo escuro';
        });

        document.getElementById('toggleEndpointsBtn').addEventListener('click', () => {
            const workspace = document.querySelector('.workspace');
            const isOpen = workspace.classList.toggle('show');
            document.getElementById('toggleEndpointsBtn').textContent = isOpen ? 'Ocultar endpoints' : 'Endpoints';
            if (isOpen) {
                workspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });

        document.addEventListener('click', (event) => {
            const rawButton = event.target.closest('button[data-raw-target]');
            if (!rawButton) return;
            const target = document.getElementById(rawButton.dataset.rawTarget);
            if (!target) return;
            const isOpen = target.classList.toggle('show');
            rawButton.textContent = isOpen ? 'Ocultar JSON' : 'Ver JSON';
        });

        endpointList.addEventListener('click', async (event) => {
            const toggle = event.target.closest('button[data-toggle]');
            if (toggle) {
                const card = toggle.closest('.endpoint-card');
                const open = card.classList.toggle('open');
                toggle.textContent = open ? 'Ocultar' : 'Detalhes';
                return;
            }

            const actionButton = event.target.closest('button[data-action-index]');
            if (actionButton) {
                const endpoint = endpoints[Number(actionButton.dataset.actionIndex)];
                await handleAction(endpoint.action);
            }
        });

        searchInput.addEventListener('input', renderEndpoints);
        document.getElementById('refreshStatusBtn').addEventListener('click', async () => {
            await loadStats();
            await pollUpdateStatus(false);
        });
        document.getElementById('runUpdateBtn').addEventListener('click', () => {
            const action = endpoints.find((item) => item.path === '/atualizar').action;
            const card = document.querySelector(`[data-index="${endpoints.findIndex((item) => item.path === '/atualizar')}"]`);
            if (card && !card.classList.contains('open')) {
                card.classList.add('open');
                card.querySelector('button[data-toggle]').textContent = 'Ocultar';
            }
            handleAction(action);
        });

        updateCounts();
        renderEndpoints();
        if (localStorage.getItem('painel-theme') === 'dark') {
            document.body.classList.add('theme-dark');
            document.getElementById('themeToggleBtn').textContent = 'Modo claro';
        }
        loadStats();
        pollUpdateStatus(false);
    </script>
</body>
</html>
'''

@app.get("/painel", response_class=HTMLResponse)
def painel():
    return PAINEL_HTML

@app.post("/atualizar")
def atualizar():
    refresh_update_status()

    with update_lock:
        if update_status["running"]:
            return JSONResponse(
                status_code=409,
                content={
                    "message": "Atualizacao ja esta em andamento.",
                    "status": update_status
                }
            )

        update_status.update({
            "running": True,
            "status": "running",
            "message": "Atualizacao iniciada.",
            "total": len(df) if df is not None else 0,
            "returncode": None
        })
        start_update_process()

    return JSONResponse(
        status_code=202,
        content={
            "message": "Atualizacao iniciada em background.",
            "status_url": "/atualizar/status",
            "status": update_status
        }
    )

@app.get("/atualizar/status")
def atualizar_status():
    return refresh_update_status()




@app.post("/")
def read_root_post(request: SearchRequest):
    """
    Alias para /buscar. Permite POST na raiz.
    """
    return buscar_cliente(request)

@app.post("/buscar")
def buscar_cliente(request: SearchRequest):
    """
    Busca um cliente em todas as colunas pelo termo enviado no corpo da requisiÃ§Ã£o.
    Body: { "termo": "valor da busca" }
    """
    print(f"Recebida busca: {request.termo}")
    if df is None or df.empty:
        raise HTTPException(status_code=503, detail="Dados nÃ£o carregados ou vazios.")
    
    q = request.termo
    if not q:
        return {"resultados": [], "total": 0}
    
    termo = q.lower().strip()
    
    # --- COMANDO INTERNO DE ATUALIZAÃ‡ÃƒO ---
    if termo == "atualizar":
        response = atualizar()
        status_code = getattr(response, "status_code", 202)
        return {
            "Revenda": "SISTEMA",
            "DT_RowId": "CMD_RUNNING" if status_code == 409 else "CMD_STARTED",
            "Id_client": "00000",
            "nome": "Atualizacao ja esta em andamento" if status_code == 409 else "Atualizacao iniciada",
            "telefone": "Rodando em background",
            "data_expiracao": "Consulte /atualizar/status"
        }
    # Remove o sinal de '+' se existir (ex: '+55...' -> '55...')
    # ATENÃ‡ÃƒO: Como agora os dados no Excel tÃªm '+', nÃ£o devemos remover o '+' da busca se o usuÃ¡rio mandar
    # Se o usuÃ¡rio mandar +55... e no banco estÃ¡ +55..., deve casar.
    # Se o usuÃ¡rio mandar 55... e no banco estÃ¡ +55..., o contains nÃ£o vai casar direto se for exato,
    # mas '55...' estÃ¡ contido em '+55...', entÃ£o contains funciona.
    # O problema Ã© se removermos o '+' da busca (+55 -> 55), e no banco Ã© +55.
    # 55 estÃ¡ em +55? Sim.
    # Mas se a lÃ³gica anterior removia, por que falhava?
    # Talvez o usuÃ¡rio mande +555185216088.
    # CÃ³digo remove + -> 555185216088.
    # Banco tem +555185216088 (se foi atualizado corretamente).
    # '555185216088' estÃ¡ em '+555185216088'? Sim.
    # EntÃ£o deveria funcionar.
    # Mas vamos garantir que a busca seja mais flexÃ­vel: buscar com e sem o +
    
    # Se o termo tem +, vamos tentar buscar exatamente como veio primeiro
    # Se nÃ£o encontrar, tentamos sem o +
    
    mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo, regex=False, na=False)).any(axis=1)
    
    # Se nÃ£o achou e tem +, tenta sem o +
    if not mask.any() and "+" in termo:
        termo_sem_plus = termo.replace("+", "")
        mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_sem_plus, regex=False, na=False)).any(axis=1)
    
    # Se nÃ£o achou e NÃƒO tem +, tenta COM o + (caso o usuÃ¡rio mande sem e no banco tenha)
    if not mask.any() and "+" not in termo and termo.isdigit():
         termo_com_plus = "+" + termo
         mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_com_plus, regex=False, na=False)).any(axis=1)
         
    # Se ainda nÃ£o achou, e o termo comeÃ§a com 55 (DDI Brasil), tenta sem o 55
    # Ex: Busca +5551... mas no banco estÃ¡ +51...
    if not mask.any() and "55" in termo:
        # Tenta remover +55 ou apenas 55 do inÃ­cio
        termo_sem_ddi = termo.replace("+55", "").replace("55", "", 1)
        # Se ficou vazio ou muito curto, ignora
        if len(termo_sem_ddi) > 4:
             mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo_sem_ddi, regex=False, na=False)).any(axis=1)

    # BUSCA ROBUSTA POR SUFIXO (ÃšLTIMA TENTATIVA)
    # Se ainda nÃ£o encontrou, vamos comparar apenas os DÃGITOS.
    # Se o usuÃ¡rio mandou um nÃºmero com pelo menos 8 dÃ­gitos,
    # verificamos se esses dÃ­gitos finais existem em algum telefone do banco.
    if not mask.any():
        import re
        # Extrai apenas dÃ­gitos da busca
        digits_busca = re.sub(r'[^\d]', '', termo)
        
        # SÃ³ aplica se tiver pelo menos 8 dÃ­gitos (evitar match falso em nÃºmeros curtos)
        if len(digits_busca) >= 8:
            # Pega os Ãºltimos 8 dÃ­gitos (suficiente para identificar unicamente na maioria dos casos)
            sufixo = digits_busca[-8:]
            
            # FunÃ§Ã£o auxiliar para verificar se o telefone da linha contÃ©m esse sufixo
            def check_suffix(val):
                val_str = str(val)
                # Extrai dÃ­gitos do valor da cÃ©lula
                val_digits = re.sub(r'[^\d]', '', val_str)
                return sufixo in val_digits
            
            # Aplica apenas na coluna 'telefone' (mais eficiente e preciso)
            if 'telefone' in df.columns:
                mask = df['telefone'].apply(check_suffix)
            else:
                # Se nÃ£o tiver coluna telefone explÃ­cita, tenta em todas (mais lento)
                mask = df.apply(lambda row: row.astype(str).apply(lambda x: sufixo in re.sub(r'[^\d]', '', x)).any(), axis=1)

    resultados = df[mask]
    
    # Converte para lista de dicionÃ¡rios
    lista_resultados = resultados.to_dict(orient="records")
    
    if lista_resultados:
        # Pega o primeiro resultado
        item = lista_resultados[0]
        
        # Limpeza extra no telefone da resposta (garantir apenas nÃºmeros e adicionar +)
        if "telefone" in item:
            import re
            phone = str(item["telefone"])
            digits = re.sub(r'[^\d]', '', phone)
            item["telefone"] = f"+{digits}" if digits else phone
        
        # Adiciona o link de pagamento
        dt_row_id = item.get("DT_RowId", "")
        if dt_row_id and dt_row_id != "nao_encontrado":
            item["Link"] = f"https://pagueaqui.top/{dt_row_id}"
        else:
            item["Link"] = "nao_encontrado"
            
        return item
    
    # Se nÃ£o encontrar nada, retorna objeto vazio com campos preenchidos com "nao_encontrado"
    # para evitar erro de mapeamento no BotConversa
    return {
        "Revenda": "nao_encontrado",
        "DT_RowId": "nao_encontrado",
        "Id_client": "nao_encontrado",
        "nome": "nao_encontrado",
        "telefone": "nao_encontrado",
        "plano": "nao_encontrado",
        "data_expiracao": "nao_encontrado",
        "Link": "nao_encontrado"
    }

@app.get("/revenda/adicionar")
def adicionar_revenda_get():
    return {"message": "Para adicionar uma revenda, use o mÃ©todo POST enviando o JSON no corpo da requisiÃ§Ã£o."}

@app.post("/revenda/adicionar")
def adicionar_revenda(request: RevendaRequest):
    """
    Adiciona uma nova revenda ao arquivo de logins.
    """
    LOGINS_FILE = "revendas_logins.json"
    
    if not os.path.exists(LOGINS_FILE):
        logins = []
    else:
        try:
            with open(LOGINS_FILE, 'r', encoding='utf-8') as f:
                logins = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logins: {e}")
    
    # Verifica se jÃ¡ existe
    if any(l['email'] == request.email for l in logins):
        return {"status": "erro", "mensagem": "Revenda com este e-mail jÃ¡ existe."}
    
    # Gera filename se nÃ£o fornecido
    filename = request.filename
    if not filename:
        # Normaliza o nome para ser usado no nome do arquivo
        clean_name = unicodedata.normalize('NFKD', request.nome).encode('ASCII', 'ignore').decode('ASCII')
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', clean_name).lower()
        filename = f"revenda{clean_name}.json"
    
    new_revenda = {
        "nome": request.nome,
        "email": request.email,
        "password": request.password,
        "filename": filename
    }
    
    logins.append(new_revenda)
    
    try:
        with open(LOGINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logins, f, indent=4, ensure_ascii=False)
        return {"status": "sucesso", "mensagem": f"Revenda {request.nome} adicionada com sucesso.", "revenda": new_revenda}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo de logins: {e}")

@app.put("/revenda/credenciais")
def atualizar_credenciais_revenda(request: CredenciaisRevendaRequest):
    """
    Atualiza email e senha de uma revenda existente apos validar o novo login no Gestor.
    Mantem o mesmo arquivo JSON da revenda para preservar os dados locais.
    Body: { "email_atual": "...", "novo_email": "...", "nova_senha": "..." }
    Se nova_senha nao for enviada, reutiliza a senha atual cadastrada.
    """
    LOGINS_FILE = os.path.join(BASE_DIR, "revendas_logins.json")
    email_atual = request.email_atual.strip()
    novo_email = request.novo_email.strip()
    nova_senha = request.nova_senha

    if not email_atual or not novo_email:
        raise HTTPException(status_code=400, detail="Informe email_atual e novo_email.")

    if not os.path.exists(LOGINS_FILE):
        return {"status": "erro", "mensagem": "Arquivo de logins nao encontrado."}

    try:
        with open(LOGINS_FILE, "r", encoding="utf-8") as f:
            logins = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logins: {e}")

    revenda_index = None
    for i, revenda in enumerate(logins):
        if revenda.get("email", "").casefold() == email_atual.casefold():
            revenda_index = i
            break

    if revenda_index is None:
        return {"status": "erro", "mensagem": f"Revenda com email {email_atual} nao encontrada."}

    revenda = logins[revenda_index]
    if nova_senha is None or nova_senha == "":
        nova_senha = revenda.get("password", "")

    if not nova_senha:
        raise HTTPException(status_code=400, detail="Informe nova_senha. A revenda encontrada nao tem senha cadastrada.")

    email_duplicado = any(
        i != revenda_index and revenda.get("email", "").casefold() == novo_email.casefold()
        for i, revenda in enumerate(logins)
    )
    if email_duplicado:
        return {"status": "erro", "mensagem": "Ja existe outra revenda cadastrada com este novo email."}

    login_valido, mensagem_login = testar_login_gestor(novo_email, nova_senha)
    if not login_valido:
        return {
            "status": "erro",
            "mensagem": "As novas credenciais nao foram salvas porque o login no Gestor falhou.",
            "detalhe": mensagem_login
        }

    email_anterior = revenda.get("email")
    revenda["email"] = novo_email
    revenda["password"] = nova_senha

    try:
        with open(LOGINS_FILE, "w", encoding="utf-8") as f:
            json.dump(logins, f, indent=4, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo de logins: {e}")

    return {
        "status": "sucesso",
        "mensagem": f"Credenciais da revenda {revenda.get('nome', '')} atualizadas com sucesso.",
        "login_teste": mensagem_login,
        "revenda": {
            "nome": revenda.get("nome"),
            "email_anterior": email_anterior,
            "email": revenda.get("email"),
            "filename": revenda.get("filename")
        }
    }

class DeleteRevendaRequest(BaseModel):
    email: str

@app.delete("/revenda/excluir")
def excluir_revenda(request: DeleteRevendaRequest):
    """
    Exclui uma revenda do arquivo de logins pelo email.
    Body: { "email": "revenda@email.com" }
    """
    LOGINS_FILE = "revendas_logins.json"
    
    if not os.path.exists(LOGINS_FILE):
        return {"status": "erro", "mensagem": "Arquivo de logins nÃ£o encontrado."}
    
    try:
        with open(LOGINS_FILE, 'r', encoding='utf-8') as f:
            logins = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logins: {e}")
    
    # Procura a revenda pelo email
    revenda_encontrada = None
    for i, revenda in enumerate(logins):
        if revenda['email'] == request.email:
            revenda_encontrada = logins.pop(i)
            break
    
    if not revenda_encontrada:
        return {"status": "erro", "mensagem": f"Revenda com email {request.email} nÃ£o encontrada."}
    
    # Salva o arquivo atualizado
    try:
        with open(LOGINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logins, f, indent=4, ensure_ascii=False)
        
        # TambÃ©m remove o arquivo JSON da revenda se existir
        filename = revenda_encontrada.get('filename')
        if filename and os.path.exists(filename):
            os.remove(filename)
        
        return {
            "status": "sucesso", 
            "mensagem": f"Revenda {revenda_encontrada['nome']} excluÃ­da com sucesso.",
            "revenda_removida": revenda_encontrada
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo de logins: {e}")

@app.get("/revenda/listar")
def listar_revendas():
    """
    Lista todas as revendas cadastradas com quantidade de clientes.
    """
    LOGINS_FILE = "revendas_logins.json"
    
    if not os.path.exists(LOGINS_FILE):
        return {"status": "sucesso", "total": 0, "revendas": []}
    
    try:
        with open(LOGINS_FILE, 'r', encoding='utf-8') as f:
            logins = json.load(f)
        
        # Retorna nome, email, filename e quantidade de clientes
        revendas_lista = []
        for r in logins:
            revenda_info = {
                "nome": r["nome"], 
                "email": r["email"], 
                "filename": r["filename"],
                "total_clientes": 0
            }
            
            # Conta clientes no arquivo JSON da revenda
            filename = r.get('filename')
            if filename and os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        clientes = json.load(f)
                        revenda_info["total_clientes"] = len(clientes)
                except:
                    pass
            
            revendas_lista.append(revenda_info)
        
        return {
            "status": "sucesso",
            "total": len(revendas_lista),
            "revendas": revendas_lista
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo de logins: {e}")

@app.post("/filtrar")
def filtrar_clientes(request: SearchRequest):
    """
    Retorna uma LISTA com todos os clientes encontrados pelo termo.
    Ideal para buscar por data (ex: '19/08/2025').
    """
    if df is None or df.empty:
        raise HTTPException(status_code=503, detail="Dados nÃ£o carregados ou vazios.")
    
    q = request.termo
    if not q:
        return []
    
    termo = q.lower().strip()
    
    # Busca exata ou parcial (neste caso, parcial funciona bem para datas)
    mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(termo, regex=False, na=False)).any(axis=1)
    
    resultados = df[mask]
    
    return resultados.to_dict(orient="records")

@app.get("/reload")
def reload_data():
    """Recarrega os dados do Excel sem reiniciar o servidor."""
    load_data()
    return {"message": "Dados recarregados.", "total_registros": len(df)}

# =============================================================================
# API EXTERNA - Consulta de Linhas
# =============================================================================

API_KEY_EXTERNA = "klxMbmr6pWOGO48GNvG746SWnQk_BMl3In4c_9IDpD4"
API_BASE_URL = "https://api.painel.best/lines/"  # Ajuste para a URL real da API

@app.post("/consultar-linha")
def consultar_linha_externa(request: SearchRequest):
    """
    Consulta a API externa buscando por nÃºmero de telefone.
    Body: { "termo": "5511999999999" }
    """
    telefone = request.termo.strip()
    
    if not telefone:
        raise HTTPException(status_code=400, detail="Telefone nÃ£o informado")
    
    # Remove caracteres nÃ£o numÃ©ricos para a busca
    telefone_limpo = re.sub(r'[^\d]', '', telefone)
    
    headers = {
        'Api-Key': API_KEY_EXTERNA
    }
    
    params = {
        'search': telefone_limpo,
        'page': 1,
        'per_page': 100
    }
    
    try:
        response = requests.get(API_BASE_URL, headers=headers, params=params, timeout=30)
        
        # Debug - log do que foi retornado
        print(f"API Externa - Status: {response.status_code}")
        print(f"API Externa - URL: {response.url}")
        print(f"API Externa - Resposta (primeiros 500 chars): {response.text[:500]}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Formata a resposta de forma apresentÃ¡vel
                if data.get('results') and len(data['results']) > 0:
                    linha = data['results'][0]
                    
                    # Converte timestamps para datas legÃ­veis
                    from datetime import datetime
                    exp_date = datetime.fromtimestamp(linha.get('exp_date', 0)).strftime('%d/%m/%Y') if linha.get('exp_date') else 'N/A'
                    created_at = datetime.fromtimestamp(linha.get('created_at', 0)).strftime('%d/%m/%Y') if linha.get('created_at') else 'N/A'
                    
                    resultado_formatado = {
                        "status": "âœ… ENCONTRADO",
                        "telefone": linha.get('phone', 'N/A'),
                        "usuario": linha.get('username', 'N/A'),
                        "senha": linha.get('password', 'N/A'),
                        "vencimento": exp_date,
                        "dias_restantes": linha.get('countdown_exp_days', 'N/A'),
                        "status_conta": "Ativa" if linha.get('is_enabled') else "Desativada",
                        "e_teste": "Sim" if linha.get('is_trial') else "NÃ£o",
                        "criado_em": created_at,
                        "notas": linha.get('notes', ''),
                        "revenda": linha.get('user_username', 'N/A')
                    }
                    
                    return {
                        "status": "sucesso",
                        "telefone_buscado": telefone,
                        "total_encontrado": data.get('count', 0),
                        "linha": resultado_formatado
                    }
                else:
                    return {
                        "status": "nao_encontrado",
                        "telefone_buscado": telefone,
                        "mensagem": "Nenhuma linha encontrada com este telefone"
                    }
                    
            except json.JSONDecodeError:
                return {
                    "status": "erro",
                    "telefone_buscado": telefone,
                    "erro": "Resposta nÃ£o Ã© JSON vÃ¡lido",
                    "resposta_raw": response.text[:500]
                }
        else:
            return {
                "status": "erro",
                "telefone_buscado": telefone,
                "http_code": response.status_code,
                "resposta": response.text[:500]
            }
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro na API externa: {str(e)}")

@app.get("/consultar-linha/{telefone}")
def consultar_linha_externa_get(telefone: str):
    """
    Consulta a API externa passando o telefone na URL.
    Exemplo: /consultar-linha/5511999999999
    """
    if not telefone:
        raise HTTPException(status_code=400, detail="Telefone nÃ£o informado")
    
    # Remove caracteres nÃ£o numÃ©ricos
    telefone_limpo = re.sub(r'[^\d]', '', telefone)
    
    headers = {
        'Api-Key': API_KEY_EXTERNA
    }
    
    params = {
        'search': telefone_limpo,
        'page': 1,
        'per_page': 100
    }
    
    try:
        response = requests.get(API_BASE_URL, headers=headers, params=params, timeout=30)
        
        # Debug - log do que foi retornado
        print(f"API Externa GET - Status: {response.status_code}")
        print(f"API Externa GET - URL: {response.url}")
        print(f"API Externa GET - Resposta (primeiros 500 chars): {response.text[:500]}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Formata a resposta de forma apresentÃ¡vel
                if data.get('results') and len(data['results']) > 0:
                    linha = data['results'][0]
                    
                    # Converte timestamps para datas legÃ­veis
                    from datetime import datetime
                    exp_date = datetime.fromtimestamp(linha.get('exp_date', 0)).strftime('%d/%m/%Y') if linha.get('exp_date') else 'N/A'
                    created_at = datetime.fromtimestamp(linha.get('created_at', 0)).strftime('%d/%m/%Y') if linha.get('created_at') else 'N/A'
                    
                    resultado_formatado = {
                        "status": "âœ… ENCONTRADO",
                        "telefone": linha.get('phone', 'N/A'),
                        "usuario": linha.get('username', 'N/A'),
                        "senha": linha.get('password', 'N/A'),
                        "vencimento": exp_date,
                        "dias_restantes": linha.get('countdown_exp_days', 'N/A'),
                        "status_conta": "Ativa" if linha.get('is_enabled') else "Desativada",
                        "e_teste": "Sim" if linha.get('is_trial') else "NÃ£o",
                        "criado_em": created_at,
                        "notas": linha.get('notes', ''),
                        "revenda": linha.get('user_username', 'N/A')
                    }
                    
                    return {
                        "status": "sucesso",
                        "telefone_buscado": telefone,
                        "total_encontrado": data.get('count', 0),
                        "linha": resultado_formatado
                    }
                else:
                    return {
                        "status": "nao_encontrado",
                        "telefone_buscado": telefone,
                        "mensagem": "Nenhuma linha encontrada com este telefone"
                    }
                    
            except json.JSONDecodeError:
                return {
                    "status": "erro",
                    "telefone_buscado": telefone,
                    "erro": "Resposta nÃ£o Ã© JSON vÃ¡lido",
                    "resposta_raw": response.text[:500]
                }
        else:
            return {
                "status": "erro",
                "telefone_buscado": telefone,
                "http_code": response.status_code,
                "resposta": response.text[:500]
            }
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro na API externa: {str(e)}")

# =============================================================================
# API EXTERNA - MaxPlayer
# =============================================================================

MAXPLAYER_API_TOKEN = os.getenv("MAXPLAYER_API_TOKEN", "iGQyrhovNMrkrHsPwSbrVtMj")
MAXPLAYER_USERS_URL = "https://api.maxplayer.tv/v3/api/public/users"
MAXPLAYER_CACHE_SECONDS = 60
maxplayer_cache = {
    "loaded_at": 0,
    "users": None
}
maxplayer_cache_lock = threading.Lock()

def get_maxplayer_users(force_refresh=False):
    now = time.time()

    with maxplayer_cache_lock:
        users = maxplayer_cache["users"]
        loaded_at = maxplayer_cache["loaded_at"]
        if users is not None and not force_refresh and now - loaded_at < MAXPLAYER_CACHE_SECONDS:
            return users, True

    headers = {
        "Api-Token": MAXPLAYER_API_TOKEN,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.get(MAXPLAYER_USERS_URL, headers=headers, timeout=45)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erro ao conectar no MaxPlayer: {str(e)}")

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"MaxPlayer retornou HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        data = response.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="MaxPlayer retornou uma resposta que nao e JSON valido.")

    if not isinstance(data, list):
        raise HTTPException(status_code=502, detail="Resposta inesperada do MaxPlayer: era esperado uma lista de usuarios.")

    with maxplayer_cache_lock:
        maxplayer_cache["users"] = data
        maxplayer_cache["loaded_at"] = time.time()

    return data, False

def normalize_search_value(value):
    return str(value or "").strip().lower()

def maxplayer_user_matches(user, termo):
    termo = normalize_search_value(termo)
    termo_numerico = re.sub(r"[^\d]", "", termo)

    candidates = [
        user.get("id"),
        user.get("username"),
        user.get("email")
    ]

    for item in user.get("lists") or []:
        candidates.extend([
            item.get("id"),
            item.get("name")
        ])
        iptv_info = item.get("iptv_info") or {}
        candidates.extend([
            iptv_info.get("username"),
            iptv_info.get("password"),
            iptv_info.get("fqdn")
        ])

    for candidate in candidates:
        value = normalize_search_value(candidate)
        if not value:
            continue

        value_numerico = re.sub(r"[^\d]", "", value)
        if termo == value or termo in value:
            return True
        if termo_numerico and (termo_numerico == value_numerico or termo_numerico in value_numerico):
            return True

    return False

def format_maxplayer_user(user):
    lists = []
    for item in user.get("lists") or []:
        iptv_info = item.get("iptv_info") or {}
        lists.append({
            "id": item.get("id"),
            "nome": item.get("name"),
            "dominio_id": item.get("domain_id"),
            "iptv": {
                "tipo": iptv_info.get("type"),
                "fqdn": iptv_info.get("fqdn"),
                "porta": iptv_info.get("port"),
                "ssl": iptv_info.get("ssl"),
                "usuario": iptv_info.get("username"),
                "senha": iptv_info.get("password")
            }
        })

    return {
        "id": user.get("id"),
        "usuario": user.get("username"),
        "email": user.get("email"),
        "listas": lists
    }

@app.post("/maxplayer/usuario")
def pesquisar_usuario_maxplayer(request: SearchRequest):
    termo = request.termo.strip()
    if not termo:
        raise HTTPException(status_code=400, detail="Usuario nao informado")

    users, from_cache = get_maxplayer_users()
    encontrados = [format_maxplayer_user(user) for user in users if maxplayer_user_matches(user, termo)]

    return {
        "status": "sucesso" if encontrados else "nao_encontrado",
        "termo_buscado": termo,
        "total_base": len(users),
        "total_encontrado": len(encontrados),
        "cache": "sim" if from_cache else "nao",
        "usuarios": encontrados[:20],
        "mensagem": "Usuario encontrado no MaxPlayer." if encontrados else "Nenhum usuario encontrado no MaxPlayer com este termo."
    }

@app.get("/maxplayer/usuario/{usuario}")
def pesquisar_usuario_maxplayer_get(usuario: str):
    return pesquisar_usuario_maxplayer(SearchRequest(termo=usuario))

@app.post("/cliente/consulta")
def consulta_cliente_unificada(request: SearchRequest):
    termo = request.termo.strip()
    if not termo:
        raise HTTPException(status_code=400, detail="Informe um telefone, usuario, ID ou email para pesquisar.")

    telefone_limpo = re.sub(r"[^\d]", "", termo)

    try:
        revenda = buscar_cliente(SearchRequest(termo=termo))
        if isinstance(revenda, dict) and revenda.get("DT_RowId") != "nao_encontrado":
            revenda = {
                **revenda,
                "status": "sucesso",
                "mensagem": "Cadastro encontrado na base das revendas."
            }
        else:
            revenda = {
                **(revenda if isinstance(revenda, dict) else {}),
                "status": "nao_encontrado",
                "mensagem": "Nenhum cadastro encontrado na base das revendas."
            }
    except HTTPException as e:
        revenda = {
            "status": "erro",
            "mensagem": e.detail,
            "Link": "nao_encontrado"
        }
    except Exception as e:
        revenda = {
            "status": "erro",
            "mensagem": str(e),
            "Link": "nao_encontrado"
        }

    if telefone_limpo:
        try:
            linha = consultar_linha_externa_get(telefone_limpo)
        except HTTPException as e:
            linha = {
                "status": "erro",
                "mensagem": e.detail
            }
        except Exception as e:
            linha = {
                "status": "erro",
                "mensagem": str(e)
            }
    else:
        linha = {
            "status": "ignorado",
            "mensagem": "A consulta de linhas precisa de um telefone numerico."
        }

    try:
        maxplayer = pesquisar_usuario_maxplayer(SearchRequest(termo=termo))
    except HTTPException as e:
        maxplayer = {
            "status": "erro",
            "mensagem": e.detail,
            "usuarios": []
        }
    except Exception as e:
        maxplayer = {
            "status": "erro",
            "mensagem": str(e),
            "usuarios": []
        }

    linha_encontrada = linha.get("status") == "sucesso"
    maxplayer_encontrado = maxplayer.get("status") == "sucesso"
    revenda_encontrada = revenda.get("status") == "sucesso"

    return {
        "status": "sucesso" if revenda_encontrada or linha_encontrada or maxplayer_encontrado else "nao_encontrado",
        "termo_buscado": termo,
        "telefone_normalizado": telefone_limpo,
        "resumo": {
            "revenda_encontrada": revenda_encontrada,
            "linha_encontrada": linha_encontrada,
            "maxplayer_encontrado": maxplayer_encontrado
        },
        "revenda": revenda,
        "linha": linha,
        "maxplayer": maxplayer
    }

if __name__ == "__main__":
    import uvicorn
    # Executa o servidor na porta 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
