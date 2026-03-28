import json
import os
import re
import unicodedata
import sys

def add_revenda(nome, email, password, filename=None):
    LOGINS_FILE = "revendas_logins.json"
    
    if not os.path.exists(LOGINS_FILE):
        logins = []
    else:
        try:
            with open(LOGINS_FILE, 'r', encoding='utf-8') as f:
                logins = json.load(f)
        except Exception as e:
            print(f"Erro ao ler arquivo de logins: {e}")
            return
    
    # Verifica se já existe
    if any(l['email'] == email for l in logins):
        print(f"Erro: Revenda com o e-mail {email} já existe.")
        return
    
    # Gera filename se não fornecido
    if not filename:
        # Normaliza o nome para ser usado no nome do arquivo
        clean_name = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', clean_name).lower()
        filename = f"revenda{clean_name}.json"
    
    new_revenda = {
        "nome": nome,
        "email": email,
        "password": password,
        "filename": filename
    }
    
    logins.append(new_revenda)
    
    try:
        with open(LOGINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logins, f, indent=4, ensure_ascii=False)
        print(f"Sucesso! Revenda '{nome}' adicionada.")
        print(f"Dados: {json.dumps(new_revenda, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"Erro ao salvar arquivo de logins: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python add_revenda.py <nome> <email> <password> [filename]")
        print("Exemplo: python add_revenda.py 'Nova Revenda' 'contato@email.com' 'senha123'")
    else:
        nome = sys.argv[1]
        email = sys.argv[2]
        password = sys.argv[3]
        filename = sys.argv[4] if len(sys.argv) > 4 else None
        add_revenda(nome, email, password, filename)
