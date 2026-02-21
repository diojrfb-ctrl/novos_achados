import time
import hashlib
import requests
import json
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """
    Consulta oficial via API GraphQL da Shopee.
    """
    
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        print("❌ Erro: SHOPEE_APP_ID ou SHOPEE_SECRET ausentes.")
        return []

    timestamp = int(time.time())
    
    # 1. Definição da Query (Mantenha simples e sem f-strings dentro para evitar confusão com chaves)
    # Aumentamos o limite na busca para compensar produtos que serão filtrados (segurança/repetidos)
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
    """ % (termo, limite + 20)

    # 2. LIMPEZA CRÍTICA: Removendo quebras de linha e espaços duplos
    # A Shopee é extremamente rigorosa com a assinatura do JSON exato enviado no body
    query_limpa = " ".join(query.split())
    payload = {"query": query_limpa}
    
    # O separators=(',', ':') remove espaços entre chaves e valores, essencial para a Signature
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    
    # 3. Geração da Assinatura (Exatamente como no seu teste funcional)
    auth_base = f"{SHOPEE_APP_ID}{timestamp}{body}{SHOPEE_SECRET}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        # Nota: SHOPEE_URL deve ser https://open-api.affiliate.shopee.com.br/graphql
        response = requests.post(SHOPEE_URL, headers=headers, data=body.encode('utf-8'), timeout=20)
        
        if response.status_code != 200:
            print(f"⚠️ Shopee API recusou (Status {response.status_code}): {response.text[:100]}")
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

            # Filtros
            if not titulo or not eh_produto_seguro(titulo):
                continue
            
            if ja_enviado(item_id):
                continue

            # Parsing dos dados
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

        print(f"✅ Shopee API: {len(resultados)} produtos processados.")
        return resultados

    except Exception as e:
        print(f"💥 Falha na busca oficial: {e}")
        return []