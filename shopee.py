import time
import hashlib
import requests
import json
# Importamos as configurações protegidas
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """Busca produtos via API Oficial GraphQL usando credenciais do .env"""
    
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        print("❌ Erro: Credenciais da Shopee não configuradas no .env")
        return []

    timestamp = int(time.time())
    
    # Query minificada para garantir integridade da assinatura
    query = '{productOfferV2(keyword:"%s",listType:1,sortType:5,page:1,limit:%d){nodes{itemId,productName,offerLink,imageUrl,priceMin,ratingStar,sales}}}' % (termo, limite + 5)
    
    payload = {"query": query}
    body = json.dumps(payload, separators=(',', ':'))
    
    # Cálculo da Assinatura conforme documentação
    # Signature = SHA256(AppId + Timestamp + Payload + Secret)
    auth_base = f"{SHOPEE_APP_ID}{timestamp}{body}{SHOPEE_SECRET}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        # Usamos requests puro (mais leve que curl_cffi para chamadas de API)
        response = requests.post(SHOPEE_URL, headers=headers, data=body, timeout=15)
        
        if response.status_code != 200:
            print(f"⚠️ Shopee API Status: {response.status_code}")
            return []

        dados = response.json()
        
        if "errors" in dados:
            print(f"❌ Erro Shopee GraphQL: {dados['errors'][0]['message']}")
            return []

        nodes = dados.get('data', {}).get('productOfferV2', {}).get('nodes', [])
        resultados = []

        for item in nodes:
            if len(resultados) >= limite:
                break

            titulo = item.get('productName', '')
            item_id = str(item.get('itemId'))

            # Filtros de Segurança e Redis
            if not titulo or not eh_produto_seguro(titulo):
                continue
            
            if ja_enviado(item_id):
                continue

            # Formatação de saída para manter compatibilidade com seu bot de postagem
            resultados.append({
                "id": item_id,
                "titulo": titulo,
                "preco": str(item.get('priceMin', '0')).replace('.', ','),
                "preco_antigo": None,
                "nota": str(round(item.get('ratingStar', 4.8), 1)),
                "avaliacoes": f"{item.get('sales', 0)} vendidos", 
                "imagem": item.get('imageUrl'),
                "link": item.get('offerLink'), # Link já com seu tracking de afiliado
                "parcelas": "Até 12x",
                "frete": "Frete grátis (com cupom)",
                "estoque": "Disponível"
            })

        return resultados

    except Exception as e:
        print(f"💥 Erro na integração Shopee: {e}")
        return []