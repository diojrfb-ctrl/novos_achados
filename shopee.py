import time
import hashlib
import requests
import json
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """
    Consulta oficial via API GraphQL. 
    Elimina o erro de bloqueio (403/404) do scraper antigo.
    """
    
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        print("❌ Erro: SHOPEE_APP_ID ou SHOPEE_SECRET ausentes no config/env.")
        return []

    timestamp = int(time.time())
    
    # Query GraphQL otimizada conforme seção 1.3 do manual
    query = """
    {
      productOfferV2(keyword: "%s", listType: 1, sortType: 5, page: 1, limit: %d) {
        nodes {
          itemId
          productName
          productLink
          offerLink
          imageUrl
          priceMin
          ratingStar
          sales
        }
      }
    }
    """ % (termo, limite + 10)

    # Minificação do body para a assinatura
    payload = {"query": query.replace("\n", " ").strip()}
    body = json.dumps(payload, separators=(',', ':'))
    
    # Assinatura Oficial: SHA256(AppId + Timestamp + Payload + Secret)
    auth_base = f"{SHOPEE_APP_ID}{timestamp}{body}{SHOPEE_SECRET}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    # Headers rigorosos conforme o manual de autenticação
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        # A API oficial não bloqueia o IP do Render
        response = requests.post(SHOPEE_URL, headers=headers, data=body, timeout=20)
        
        if response.status_code != 200:
            print(f"⚠️ Shopee API recusou a conexão (Status {response.status_code})")
            return []

        dados = response.json()
        
        if "errors" in dados:
            print(f"❌ Erro na API Shopee: {dados['errors'][0]['message']}")
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

            # Formatação para o seu template de postagem
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
                "frete": "Frete grátis (com cupom)",
                "estoque": "Disponível"
            })

        print(f"✅ Shopee API: {len(resultados)} produtos encontrados com sucesso.")
        return resultados

    except Exception as e:
        print(f"💥 Falha na busca oficial: {e}")
        return []