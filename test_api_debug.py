import requests
import json

def test_search(termo):
    url = "http://localhost:8080/buscar"
    payload = {"termo": termo}
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Headers:", response.headers)
        try:
            data = response.json()
            print("JSON Response:")
            print(json.dumps(data, indent=2))
        except:
            print("Response Text (not JSON):", response.text)
    except Exception as e:
        print(f"Erro ao conectar: {e}")

if __name__ == "__main__":
    print("--- Teste 1: Termo que deve existir (ex: um número ou nome comum) ---")
    # Vou usar um termo genérico que provavelmente existe ou algo que vi no histórico
    test_search("1373064") # ID que vi no exemplo anterior

    print("\n--- Teste 2: Termo inexistente ---")
    test_search("xyz123naoexiste")
