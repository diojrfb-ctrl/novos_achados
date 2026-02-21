import time
import hashlib
import requests
import json
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    from main import disparar_log_sync

    app_id = str(SHOPEE_APP_ID or "").strip()
    secret = str(SHOPEE_SECRET or "").strip()

    if not app_id or not secret:
        disparar_log_sync("❌ [Shopee] Erro: Credenciais ausentes.")
        return []

    timestamp = int(time.time())
    
    # MUDANÇA CRÍTICA: sortType: 2 (Ordena pelos mais vendidos/populares)
    # Aumentamos o limite para 50 para termos margem de filtro
    query_string = (
        '{productOfferV2(keyword:"%s",listType:1,sortType:2,page:1,limit:50)'
        '{nodes{itemId,productName,productLink,offerLink,imageUrl,priceMin,ratingStar,sales}}}'
    ) % (termo)

    payload = {"query": query_string}
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    
    auth_base = f"{app_id}{timestamp}{body}{secret}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        url_api = "https://open-api.affiliate.shopee.com.br/graphql"
        response = requests.post(url_api, headers=headers, data=body.encode('utf-8'), timeout=20)
        
        if response.status_code != 200:
            return []

        dados = response.json()
        nodes = dados.get('data', {}).get('productOfferV2', {}).get('nodes', [])
        
        resultados = []
        for item in nodes:
            if len(resultados) >= limite: break
            
            titulo = item.get('productName', '')
            item_id = str(item.get('itemId'))
            vendas = item.get('sales', 0)

            # --- FILTRO DE QUALIDADE ---
            # Ignora produtos com menos de 10 vendas para evitar "anúncios fantasmas"
            if vendas < 10:
                continue

            if not titulo or not eh_produto_seguro(titulo) or ja_enviado(item_id):
                continue

            try:
                nota_raw = item.get('ratingStar', 4.8)
                nota_formatada = str(round(float(nota_raw), 1))
            except:
                nota_formatada = "4.8"

            resultados.append({
                "id": item_id,
                "titulo": titulo,
                "preco": str(item.get('priceMin', '0')).replace('.', ','),
                "nota": nota_formatada,
                "avaliacoes": f"{vendas}", 
                "imagem": item.get('imageUrl'),
                "link": item.get('offerLink') or item.get('productLink'),
                "parcelas": "Até 12x",
                "frete": "Frete grátis",
                "estoque": "Disponível"
            })

        disparar_log_sync(f"✅ [Shopee] Encontrados {len(resultados)} produtos de alta relevância.")
        return resultados

    except Exception as e:
        disparar_log_sync(f"💥 [Shopee] Erro Interno: {e}")
        return []