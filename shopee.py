import time
import hashlib
import requests
import json
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """
    Consulta oficial Shopee via API GraphQL.
    Substitui o antigo Scraper por uma chamada autenticada e oficial.
    """
    
    # Validação de credenciais
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        print("❌ Erro: SHOPEE_APP_ID ou SHOPEE_SECRET não configurados no ambiente.")
        return []

    timestamp = int(time.time())
    
    # Query GraphQL conforme seção 1.3 da documentação (Product Offer List)
    # Buscamos 'limite + 10' para garantir que, após os filtros (ja_enviado e segurança), 
    # ainda tenhamos a quantidade solicitada.
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

    # Preparação do payload (minificado conforme exigido para a assinatura)
    payload = {"query": query.replace("\n", " ").strip()}
    body = json.dumps(payload, separators=(',', ':'))
    
    # Cálculo da Assinatura: SHA256(AppId + Timestamp + Payload + Secret)
    auth_base = f"{SHOPEE_APP_ID}{timestamp}{body}{SHOPEE_SECRET}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    # Headers de autenticação conforme documentação oficial
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        # Chamada para a API (muito mais rápido que carregar HTML)
        response = requests.post(SHOPEE_URL, headers=headers, data=body, timeout=20)
        
        if response.status_code != 200:
            print(f"⚠️ Shopee API retornou status {response.status_code}")
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

            # 1. Validação de Segurança (IA/Filtros)
            if not titulo or not eh_produto_seguro(titulo):
                continue
            
            # 2. Validação de Duplicidade (Redis)
            if ja_enviado(item_id):
                continue

            # Formatação do preço para o padrão brasileiro (ex: 20.0 -> 20,0)
            preco_raw = item.get('priceMin', '0')
            preco_formatado = str(preco_raw).replace('.', ',')

            # A API já retorna o link de afiliado pronto no 'offerLink'
            link_final = item.get('offerLink') or item.get('productLink')

            resultados.append({
                "id": item_id,
                "titulo": titulo,
                "preco": preco_formatado,
                "preco_antigo": None,
                "nota": str(round(item.get('ratingStar', 4.8), 1)),
                "avaliacoes": f"{item.get('sales', 0)} vendidos", 
                "imagem": item.get('imageUrl'),
                "link": link_final,
                "parcelas": "Até 12x",
                "frete": "Frete grátis (com cupom)",
                "estoque": "Disponível"
            })

        return resultados

    except Exception as e:
        print(f"💥 Falha crítica na integração Shopee: {e}")
        return []