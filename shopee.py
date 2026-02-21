import time
import hashlib
import requests
import json
import os
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """
    Versão reconstruída com Logs de Depuração para o Render.
    """
    # Garante que as chaves sejam strings puras e sem espaços
    app_id = str(SHOPEE_APP_ID or "").strip()
    secret = str(SHOPEE_SECRET or "").strip()

    if not app_id or not secret:
        print("❌ [Shopee] Erro: SHOPEE_APP_ID ou SHOPEE_SECRET não encontrados no ambiente.")
        return []

    timestamp = int(time.time())
    
    # Query minificada (padrão que funcionou no seu teste local)
    query_string = (
        '{productOfferV2(keyword:"%s",listType:1,sortType:5,page:1,limit:%d)'
        '{nodes{itemId,productName,productLink,offerLink,imageUrl,priceMin,ratingStar,sales}}}'
    ) % (termo, limite + 10)

    payload = {"query": query_string}
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    
    # Geração da Assinatura
    auth_base = f"{app_id}{timestamp}{body}{secret}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        # Usando a URL oficial
        url_oficial = "https://open-api.affiliate.shopee.com.br/graphql"
        response = requests.post(url_oficial, headers=headers, data=body.encode('utf-8'), timeout=30)
        
        if response.status_code != 200:
            print(f"⚠️ [Shopee] Erro HTTP {response.status_code}: {response.text[:200]}")
            return []

        dados = response.json()
        
        if "errors" in dados:
            msg_erro = dados['errors'][0].get('message', 'Erro desconhecido')
            print(f"❌ [Shopee] A API respondeu com erro: {msg_erro}")
            # Se o erro for "Signature Not Match", o problema está no APP_ID ou SECRET no Render
            return []

        nodes = dados.get('data', {}).get('productOfferV2', {}).get('nodes', [])
        
        if not nodes:
            print(f"ℹ️ [Shopee] API conectou, mas não encontrou produtos para '{termo}'.")
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
                "preco_antigo": None,
                "nota": str(round(item.get('ratingStar', 4.8), 1)),
                "avaliacoes": f"{item.get('sales', 0)} vendidos", 
                "imagem": item.get('imageUrl'),
                "link": item.get('offerLink') or item.get('productLink'),
                "parcelas": "Até 12x",
                "frete": "Frete grátis (cupom)",
                "estoque": "Disponível"
            })

        print(f"✅ [Shopee] {len(resultados)} produtos encontrados.")
        return resultados

    except Exception as e:
        print(f"💥 [Shopee] Erro na requisição: {e}")
        return []