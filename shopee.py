import time
import hashlib
import requests
import json
import asyncio
from config import SHOPEE_APP_ID, SHOPEE_SECRET, SHOPEE_URL, LOG_CANAL
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

# Função auxiliar para enviar logs em tempo real para o Telegram
def log_telegram(mensagem):
    print(f"[Shopee Debug] {mensagem}")
    try:
        from main import client
        if LOG_CANAL and client.is_connected():
            # Cria uma tarefa para enviar a mensagem sem travar a busca
            loop = asyncio.get_event_loop()
            loop.create_task(client.send_message(LOG_CANAL, f"🔍 **DEBUG SHOPEE:**\n{mensagem}"))
    except Exception as e:
        print(f"Erro ao enviar log para Telegram: {e}")

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    # Limpeza de credenciais
    app_id = str(SHOPEE_APP_ID or "").strip()
    secret = str(SHOPEE_SECRET or "").strip()

    if not app_id or not secret:
        log_telegram("❌ Erro: Credenciais ausentes (APP_ID/SECRET).")
        return []

    timestamp = int(time.time())
    
    # Query limpa para evitar quebras de linha que invalidam a Signature
    query_string = (
        '{productOfferV2(keyword:"%s",listType:1,sortType:5,page:1,limit:%d)'
        '{nodes{itemId,productName,productLink,offerLink,imageUrl,priceMin,ratingStar,sales}}}'
    ) % (termo, limite + 10)

    payload = {"query": query_string}
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    
    # Gerar Signature
    auth_base = f"{app_id}{timestamp}{body}{secret}"
    signature = hashlib.sha256(auth_base.encode('utf-8')).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"
    }

    try:
        response = requests.post(SHOPEE_URL, headers=headers, data=body.encode('utf-8'), timeout=20)
        
        if response.status_code != 200:
            log_telegram(f"⚠️ Erro HTTP {response.status_code}\nResposta: {response.text[:100]}")
            return []

        dados = response.json()
        
        if "errors" in dados:
            erro_api = dados['errors'][0].get('message', 'Erro desconhecido')
            log_telegram(f"❌ Erro na API: {erro_api}")
            return []

        nodes = dados.get('data', {}).get('productOfferV2', {}).get('nodes', [])
        
        if not nodes:
            log_telegram(f"ℹ️ Conectado, mas 0 produtos para '{termo}'.")
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
                "avaliacoes": f"{item.get('sales', 0)}", 
                "imagem": item.get('imageUrl'),
                "link": item.get('offerLink') or item.get('productLink'),
                "parcelas": "Até 12x",
                "frete": "Frete grátis",
                "estoque": "Disponível"
            })

        return resultados

    except Exception as e:
        log_telegram(f"💥 Falha crítica: {str(e)}")
        return []