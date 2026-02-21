import time
import hashlib
import requests
import json
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """
    Consulta oficial via API GraphQL da Shopee (Affiliate API v2).
    Recriado para garantir integridade total da Signature.
    """
    
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        print("❌ [Shopee] Erro: SHOPEE_APP_ID ou SHOPEE_SECRET ausentes no config.")
        return []

    timestamp = int(time.time())
    
    # Query em linha única (minificada) para evitar erros de hash
    query_string = (
        '{productOfferV2(keyword:"%s",listType:1,sortType:5,page:1,limit:%d)'
        '{nodes{itemId,productName,productLink,offerLink,imageUrl,priceMin,ratingStar,sales}}}'
    ) % (termo, limite + 10)

    payload = {"query": query_string}
    # O separators=(',', ':') é OBRIGATÓRIO para a assinatura bater com o que a Shopee espera
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    
    # Gerar Assinatura: SHA256(AppId + Timestamp + Payload + Secret)
    auth_base = f"{SHOPEE_APP_ID}{timestamp}{body}{SHOPEE_SECRET}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        response = requests.post(SHOPEE_URL, headers=headers, data=body.encode('utf-8'), timeout=25)
        
        if response.status_code != 200:
            print(f"⚠️ [Shopee] Erro HTTP {response.status_code}: {response.text[:150]}")
            return []

        dados = response.json()
        
        if "errors" in dados:
            print(f"❌ [Shopee] Erro na API: {dados['errors'][0]['message']}")
            return []

        nodes = dados.get('data', {}).get('productOfferV2', {}).get('nodes', [])
        resultados = []

        for item in nodes:
            if len(resultados) >= limite:
                break

            titulo = item.get('productName', '')
            item_id = str(item.get('itemId'))

            if not titulo or not eh_produto_seguro(titulo) or ja_enviado(item_id):
                continue

            resultados.append({
                "id": item_id,
                "titulo": titulo,
                "preco": str(item.get('priceMin', '0')).replace('.', ','),
                "preco_antigo": None,
                "nota": str(round(item.get('ratingStar', 4.8), 1)),
                "avaliacoes": f"{item.get('sales', 0)}", 
                "imagem": item.get('imageUrl'),
                "link": item.get('offerLink') or item.get('productLink'),
                "parcelas": "Até 12x",
                "frete": "Frete grátis (com cupom)",
                "estoque": "Disponível"
            })

        print(f"✅ [Shopee] Busca concluída: {len(resultados)} produtos válidos.")
        return resultados

    except Exception as e:
        print(f"💥 [Shopee] Erro crítico: {e}")
        return []