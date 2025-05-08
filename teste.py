import json


def ler_json_para_objeto(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
            dados_json = json.load(arquivo)
            return dados_json
    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado em '{caminho_arquivo}'")
        return None
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar o arquivo JSON '{caminho_arquivo}': {e}")
        return None


# Exemplo de uso:
caminho_do_arquivo_json = 'lua/nemertea/nemertea.json'  # Substitua pelo caminho do seu arquivo JSON
objeto_json = ler_json_para_objeto(caminho_do_arquivo_json)

if objeto_json is not None:
    print("Arquivo JSON carregado com sucesso:")
    print(objeto_json)
    print(objeto_json['cycle'])
    try:
        print(objeto_json['teste'])
    except KeyError:
        print("None")
    # Você pode agora acessar os dados como faria com um dicionário ou lista Python
    if isinstance(objeto_json, dict) and 'nome' in objeto_json:
        print(f"Nome: {objeto_json['nome']}")
    elif isinstance(objeto_json, list) and len(objeto_json) > 0:
        print(f"Primeiro elemento da lista: {objeto_json[0]}")
