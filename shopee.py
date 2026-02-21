import time
import hashlib
import requests
import json
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    # Importamos o disparador de log do main
    from main import disparar_log_sync

    app_id = str(SHOPEE_APP_ID or "").strip()
    secret = str(SHOPEE_SECRET or "").strip()

    if not app_id or not secret:
        disparar_log_sync("❌ [Shopee] Erro: Credenciais APP_ID ou SECRET vazias.")
        return []

    timestamp = int(time.time())
    
    # Query minificada (idêntica ao seu teste que funcionou)
    query_string = (
        '{productOfferV2(keyword:"%s",listType:1,sortType:5,page:1,limit:%d)'
        '{nodes{itemId,productName,productLink,offerLink,imageUrl,priceMin,ratingStar,sales}}}'
    ) % (termo, limite + 5)

    payload = {"query": query_string}
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    
    auth_base = f"{app_id}{timestamp}{body}{secret}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        # Forçamos a URL correta diretamente aqui para evitar erros de config
        url_api = "https://open-api.affiliate.shopee.com.br/graphql"
        response = requests.post(url_api, headers=headers, data=body.encode('utf-8'), timeout=20)
        
        if response.status_code != 200:
            disparar_log_sync(f"⚠️ [Shopee] Erro HTTP {response.status_code}\nResponda: {response.text[:100]}")
            return []

        dados = response.json()
        
        if "errors" in dados:
            msg = dados['errors'][0].get('message', 'Erro desconhecido')
            disparar_log_sync(f"❌ [Shopee] Erro na API: {msg}")
            return []

        nodes = dados.get('data', {}).get('productOfferV2', {}).get('nodes', [])
        
        if not nodes:
            disparar_log_sync(f"ℹ️ [Shopee] Busca por '{termo}' retornou 0 produtos.")
            return []

        resultados = []
        for item in nodes:
            if len(resultados) >= limite: break
            
            titulo = item.get('productName', '')
            item_id = str(item.get('itemId'))

            if not titulo or not eh_produto_seguro(titulo) or ja_enviado(item_id):
                continue

            resultados.append({
                "id": item_id,
                "titulo": titulo,
                "preco": str(item.get('priceMin', '0')).replace('.', ','),
                "nota": str(round(item.get('ratingStar', 4.8), 1)),
                "avaliacoes": f"{item.get('sales', 0)}", 
                "imagem": item.get('imageUrl'),
                "link": item.get('offerLink') or item.get('productLink'),
                "parcelas": "Até 12x",
                "frete": "Frete grátis",
                "estoque": "Disponível"
            })

        return resultados

    except Exception as e:
        disparar_log_sync(f"💥 [Shopee] Falha Crítica: {e}")
        return []