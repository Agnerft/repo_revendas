import requests
import json

def test_search(termo):
    url = "http://localhost:8080/buscar"
    payload = {"termo": termo}
    try:
        response = requests.post(url, json=payload)
        print(f"Termo: '{termo}' -> Status: {response.status_code}")
        if response.status_code == 200:
            print("Response:", json.dumps(response.json(), indent=2))
        else:
            print("Error:", response.text)
    except Exception as e:
        print(f"Erro ao conectar: {e}")

if __name__ == "__main__":
    # Teste com caractere especial que quebra regex se não tratado
    print("--- Teste de Caractere Especial ---")
    test_search("*")
    test_search("?")
    test_search("+55") 
