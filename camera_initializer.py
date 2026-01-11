# -*- coding: utf-8 -*-

"""
Script para inicializar câmeras IP Dahua/Intelbras em lote.
"""

import requests

def initialize_camera(camera_ip, new_password, new_ip_config):
    """
    Inicializa uma câmera Dahua definindo a senha do administrador e as configurações de rede.

    Args:
        camera_ip (str): O endereço IP atual da câmera a ser inicializada.
        new_password (str): A nova senha para a conta 'admin'.
        new_ip_config (dict): Um dicionário com a nova configuração de rede.
                              Ex: {'ip': '192.168.1.108', 'subnet_mask': '255.255.255.0', 'gateway': '192.168.1.1'}

    Returns:
        bool: True se a inicialização for bem-sucedida, False caso contrário.
    """
    url = f"http://{camera_ip}/RPC2"
    request_id = 1

    payload = {
        "method": "magicBox.initialize",
        "params": {
            "password": new_password,
            "userName": "admin",
            "net": {
                "ip": new_ip_config['ip'],
                "subnetMask": new_ip_config['subnet_mask'],
                "gateWay": new_ip_config['gateway'],
                "dns": { "server1": new_ip_config.get('gateway', '8.8.8.8'), "server2": "8.8.4.4" },
                "tcpPort": 37777, "udpPort": 37778, "httpPort": 80, "rtspPort": 554, "ipVersion": 0
            }
        },
        "id": request_id,
        "session": 0
    }

    print(f"\nTentando inicializar a câmera em {camera_ip}...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        response_json = response.json()
        if "error" not in response_json:
            print(f"SUCESSO: A câmera foi inicializada e agora está em {new_ip_config['ip']}.")
            return True
        else:
            print(f"FALHA: A câmera respondeu com um erro: {response_json.get('error')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"FALHA: Erro de comunicação ao tentar inicializar a câmera: {e}")
        return False
    except Exception as e:
        print(f"FALHA: Ocorreu um erro inesperado: {e}")
        return False

if __name__ == '__main__':
    print("--- Ferramenta de Inicialização Interativa de Câmeras ---")
    print("Você pode configurar até 3 câmeras nesta sessão.")

    for i in range(3):
        print(f"\n--- Configurando Câmera {i + 1} de 3 ---")

        current_ip = input("Digite o endereço IP ATUAL da câmera (ou pressione Enter para sair): ").strip()
        if not current_ip:
            break

        new_password = input("Digite a NOVA senha para o usuário 'admin': ").strip()

        print("\nAgora, digite as novas configurações de rede:")
        new_ip = input("Novo Endereço IP: ").strip()
        new_subnet = input("Nova Máscara de Sub-rede (ex: 255.255.255.0): ").strip()
        new_gateway = input("Novo Gateway Padrão: ").strip()

        # Validação simples para garantir que os campos não estão vazios
        if not all([new_password, new_ip, new_subnet, new_gateway]):
            print("\nERRO: Todos os campos são obrigatórios. Esta câmera será ignorada.")
            continue

        new_config = {
            'ip': new_ip,
            'subnet_mask': new_subnet,
            'gateway': new_gateway
        }

        initialize_camera(current_ip, new_password, new_config)

        if i < 2:
            another = input("\nDeseja configurar outra câmera? (s/n): ").strip().lower()
            if another != 's':
                break

    print("\n--- Processo de configuração concluído ---")
