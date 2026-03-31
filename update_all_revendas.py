import requests
import json
import time
import os
import pandas as pd
import re
from datetime import datetime

# Configuration
LOGIN_URL = "https://app.gestorinove.com.br/valida"
DATA_URL = "https://app.gestorinove.com.br/modulos/cliente/ajax.php"
CREDENTIALS_FILE = "revendas_logins.json"

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session

def login(session, email, password):
    print(f"Tentando login como {email}...")
    payload = {
        'email': email,
        'senha': password,
        'redir': ''
    }
    
    try:
        session.get("https://app.gestorinove.com.br/login")
        response = session.post(LOGIN_URL, data=payload)
        
        if response.url == "https://app.gestorinove.com.br/painel" or "painel" in response.url:
            print("Login com sucesso!")
            return True
        elif "Erro" in response.text or "inválido" in response.text:
            print("Login falhou: Credenciais inválidas.")
            return False
        elif 'GESTOR_SESSION' in session.cookies:
             print("Login com sucesso (Cookie de sessão encontrado).")
             return True
        else:
            print(f"Login incerto. URL: {response.url}")
            return True 
            
    except Exception as e:
        print(f"Erro no login: {e}")
        return False

def fetch_data(session):
    print("Buscando dados...")
    params = {
        "draw": "3",
        "start": "0",
        "length": "20000", # Aumentado para garantir pegar tudo
        "search[value]": "",
        "search[regex]": "false",
        "colunas": '["id_externo","nome","sobrenome","email","whatsapp","id_plano","id_categoria","data_vencimento","status"]',
        "modulo": "cliente",
        "plano": "",
        "categoria": "",
        "dataIni": "",
        "dataFim": "",
        "idStatus": "",
        "_": str(int(time.time() * 1000))
    }
    
    for i in range(10):
        params[f"columns[{i}][data]"] = str(i)
        params[f"columns[{i}][name]"] = ""
        params[f"columns[{i}][searchable]"] = "true"
        params[f"columns[{i}][orderable]"] = "true" if i < 9 else "false"
        params[f"columns[{i}][search][value]"] = ""
        params[f"columns[{i}][search][regex]"] = "false"
        
    params["order[0][column]"] = "0"
    params["order[0][dir]"] = "desc"

    try:
        response = session.get(DATA_URL, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Falha na busca: {response.status_code}")
            return None
    except Exception as e:
        print(f"Erro na busca: {e}")
        return None

def process_and_save(raw_data, filename):
    if not raw_data or 'data' not in raw_data:
        print(f"Sem dados válidos para processar em {filename}")
        return False

    raw_list = raw_data['data']
    processed_list = []
    seen_ids = set()
    
    print(f"Processando {len(raw_list)} registros...")

    for item in raw_list:
        dt_row_id = item.get('DT_RowId')
        id_client = item.get('0')
        nome = item.get('1')
        telefone = item.get('4')
        plano = item.get('5')
        data_expiracao = item.get('7')
        
        if id_client in seen_ids:
            continue
        seen_ids.add(id_client)
        
        processed_list.append({
            "DT_RowId": dt_row_id,
            "Id_client": id_client,
            "nome": nome,
            "telefone": telefone,
            "plano": plano,
            "data_expiracao": data_expiracao
        })
        
    print(f"Salvando {len(processed_list)} registros únicos em {filename}")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(processed_list, f, indent=4, ensure_ascii=False)
    return True

def consolidate_excel(accounts):
    print("\n--- Consolidando arquivos no Excel ---")
    all_data = []

    for acc in accounts:
        filename = acc['filename']
        revenda_name = acc['nome']
        
        if os.path.exists(filename):
            print(f"Lendo {filename} como '{revenda_name}'...")
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for item in data:
                        # Adicionar formatação de telefone
                        if "telefone" in item:
                            phone = str(item["telefone"])
                            digits = re.sub(r'[^\d]', '', phone)
                            if digits:
                                item["telefone"] = f"+{digits}"
                        
                        # Converter data_expiracao para timestamp
                        if "data_expiracao" in item:
                            date_str = item["data_expiracao"]
                            if date_str and isinstance(date_str, str):
                                try:
                                    dt = datetime.strptime(date_str, "%d/%m/%Y")
                                    item["data_expiracao"] = int(dt.timestamp())
                                except ValueError:
                                    # Mantém o valor original se falhar a conversão
                                    pass

                        item['Revenda'] = revenda_name
                        all_data.append(item)
            except Exception as e:
                print(f"Erro ao ler {filename}: {e}")
        else:
            print(f"Arquivo {filename} não encontrado. Pulando.")

    if all_data:
        df = pd.DataFrame(all_data)
        
        # Reordenar colunas para 'Revenda' ser a primeira
        cols = ['Revenda'] + [c for c in df.columns if c != 'Revenda']
        df = df[cols]
        
        output_file = 'revendas_consolidadas.xlsx'
        df.to_excel(output_file, index=False)
        print(f"\nSucesso! Criado '{output_file}' com {len(df)} registros.")
    else:
        print("\nNenhum dado encontrado para consolidar.")

def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Arquivo de credenciais {CREDENTIALS_FILE} não encontrado.")
        return

    with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
        accounts = json.load(f)

    print(f"Encontradas {len(accounts)} revendas para processar.\n")

    for acc in accounts:
        print(f"--- Iniciando processamento de {acc['nome']} ---")
        session = get_session()
        if login(session, acc['email'], acc['password']):
            data = fetch_data(session)
            if data:
                process_and_save(data, acc['filename'])
            else:
                print(f"Nenhum dado retornado para {acc['nome']}.")
        else:
            print(f"PULANDO {acc['nome']} devido a falha no login.")
        
        session.close()
        print("-" * 30 + "\n")

    # Consolida tudo no final
    consolidate_excel(accounts)

if __name__ == "__main__":
    main()
