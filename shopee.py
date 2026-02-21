import time
import hashlib
import requests
import json
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """
    Componente oficial Shopee Affiliate API v2 (GraphQL).
    Recriado para garantir integridade da Signature e parsing correto.
    """
    
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        print("❌ [Shopee] Erro: Credenciais (APP_ID/SECRET) não configuradas.")
        return []

    # 1. Configuração do Timestamp
    timestamp = int(time.time())
    
    # 2. Construção da Query GraphQL
    # Importante: A query deve ser uma string limpa sem quebras de linha complexas
    query_string = (
        '{productOfferV2(keyword:"%s",listType:1,sortType:5,page:1,limit:%d)'
        '{nodes{itemId,productName,productLink,offerLink,imageUrl,priceMin,ratingStar,sales}}}'
    ) % (termo, limite + 10)

    # 3. Preparação do Payload
    # Usamos separators para remover espaços em branco do JSON (padrão Shopee)
    payload = {"query": query_string}
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    
    # 4. Geração da Assinatura
    # Ordem: AppID + Timestamp + Body + Secret
    auth_base = f"{SHOPEE_APP_ID}{timestamp}{body}{SHOPEE_SECRET}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    # 5. Headers de Autenticação
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        # A URL deve ser: https://open-api.affiliate.shopee.com.br/graphql
        response = requests.post(
            SHOPEE_URL, 
            headers=headers, 
            data=body.encode('utf-8'), 
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"⚠️ [Shopee] Erro de Conexão: Status {response.status_code}")
            return []

        dados = response.json()
        
        # Verifica erros internos da API (como assinatura inválida)
        if "errors" in dados:
            erro_msg = dados['errors'][0].get('message', 'Erro desconhecido')
            print(f"❌ [Shopee] Erro na API: {erro_msg}")
            return []

        # Extração dos produtos (nodes)
        nodes = dados.get('data', {}).get('productOfferV2', {}).get('nodes', [])
        if not nodes:
            print(f"ℹ️ [Shopee] Nenhum produto encontrado para o termo: {termo}")
            return []

        resultados = []

        for item in nodes:
            # Limite de resultados desejados
            if len(resultados) >= limite:
                break

            titulo = item.get('productName', 'Produto sem título')
            item_id = str(item.get('itemId'))

            # Filtros de Segurança e Duplicidade
            if not eh_produto_seguro(titulo):
                continue
            
            if ja_enviado(item_id):
                continue

            # Formatação dos dados para o seu formatador (formatar_copy_otimizada)
            resultados.append({
                "id": item_id,
                "titulo": titulo,
                "preco": str(item.get('priceMin', '0.00')).replace('.', ','),
                "preco_antigo": None,
                "nota": str(round(item.get('ratingStar', 4.8), 1)),
                "avaliacoes": f"{item.get('sales', 0)}", 
                "imagem": item.get('imageUrl'),
                "link": item.get('offerLink') or item.get('productLink'),
                "parcelas": "Até 12x no cartão",
                "frete": "Frete grátis (confira no app)",
                "estoque": "Disponível"
            })

        print(f"✅ [Shopee] Sucesso: {len(resultados)} produtos filtrados.")
        return resultados

    except Exception as e:
        print(f"💥 [Shopee] Falha Crítica: {str(e)}")
        return []