# -*- coding: utf-8 -*-

"""
Script para inicializar câmeras IP Dahua/Intelbras em lote.
"""

import socket
import requests
import csv
import re

def parse_discovery_response(raw_data_hex):
    """
    Tenta extrair o endereço MAC de uma resposta de descoberta bruta.

    Args:
        raw_data_hex (str): A resposta bruta da câmera, codificada em hexadecimal.

    Returns:
        str or None: O endereço MAC se encontrado, caso contrário None.
    """
    try:
        raw_data = bytes.fromhex(raw_data_hex)
        text_content = raw_data.decode('ascii', errors='ignore')
        mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
        match = re.search(mac_pattern, text_content)
        if match:
            mac_address = match.group(0).replace('-', ':').upper()
            print(f"  -> Endereço MAC encontrado: {mac_address}")
            return mac_address
    except Exception as e:
        print(f"  -> Erro ao analisar a resposta para encontrar o MAC: {e}")
    print("  -> Endereço MAC não encontrado na resposta.")
    return None

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

    print(f"Tentando inicializar a câmera em {camera_ip}...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        response_json = response.json()
        if "error" not in response_json:
            print(f"Sucesso! A câmera em {camera_ip} foi inicializada.")
            return True
        else:
            print(f"Erro na resposta da câmera: {response_json.get('error')}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Erro de comunicação ao tentar inicializar a câmera {camera_ip}: {e}")
        return False
    except Exception as e:
        print(f"Ocorreu um erro inesperado durante a inicialização: {e}")
        return False

def discover_cameras(timeout=5):
    """
    Envia um pacote de broadcast UDP para a rede para descobrir câmeras Dahua/Intelbras.
    """
    discovery_port = 37020
    broadcast_address = '255.255.255.255'
    discovery_payload = b'\x00\x00\x00\x00'
    discovered_cameras = []

    print(f"Enviando broadcast de descoberta para {broadcast_address}:{discovery_port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            sock.sendto(discovery_payload, (broadcast_address, discovery_port))

            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    print(f"Resposta recebida de {addr}")
                    camera_info = { "ip": addr[0], "port": addr[1], "raw_response": data.hex() }
                    discovered_cameras.append(camera_info)
                    print(f"  -> Câmera encontrada: {camera_info}")
                except socket.timeout:
                    print("Tempo de espera esgotado.")
                    break
    except Exception as e:
        print(f"Falha ao criar ou usar o socket de descoberta: {e}")
    return discovered_cameras

def load_config(csv_filepath='cameras_config.csv'):
    """Carrega a configuração das câmeras de um arquivo CSV."""
    config = {}
    try:
        with open(csv_filepath, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                mac = row['mac_address'].upper()
                config[mac] = {
                    'ip': row['ip_address'],
                    'subnet_mask': row['subnet_mask'],
                    'gateway': row['gateway'],
                    'admin_password': row['admin_password']
                }
        print(f"Configuração carregada para {len(config)} câmeras.")
        return config
    except FileNotFoundError:
        print(f"Erro: Arquivo de configuração '{csv_filepath}' não encontrado.")
        return None
    except Exception as e:
        print(f"Erro ao ler o arquivo de configuração: {e}")
        return None

if __name__ == '__main__':
    print("--- Iniciando Processo de Inicialização de Câmeras em Lote ---")

    # 1. Carregar a configuração
    camera_configs = load_config()

    if camera_configs:
        # 2. Descobrir câmeras na rede
        uninitialized_cameras = discover_cameras()

        if not uninitialized_cameras:
            print("\nNenhuma câmera não inicializada foi encontrada na rede.")
        else:
            initialized_count = 0
            # 3. Iterar, corresponder e inicializar
            print("\n--- Comparando câmeras encontradas com a configuração ---")
            for cam in uninitialized_cameras:
                print(f"\nAnalisando câmera com IP temporário: {cam['ip']}")
                mac_address = parse_discovery_response(cam['raw_response'])

                if mac_address and mac_address in camera_configs:
                    print(f"Correspondência encontrada para MAC {mac_address}. Tentando inicializar...")
                    config = camera_configs[mac_address]

                    success = initialize_camera(
                        camera_ip=cam['ip'],
                        new_password=config['admin_password'],
                        new_ip_config={
                            'ip': config['ip'],
                            'subnet_mask': config['subnet_mask'],
                            'gateway': config['gateway']
                        }
                    )
                    if success:
                        initialized_count += 1
                else:
                    print(f"Nenhuma configuração correspondente encontrada para esta câmera (MAC: {mac_address}).")

            print("\n--- Resumo do Processo ---")
            print(f"{initialized_count} câmera(s) foram inicializada(s) com sucesso.")

    print("\n--- Processo Concluído ---")
