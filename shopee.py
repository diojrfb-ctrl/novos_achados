from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import random
import re
from config import HEADERS, SHOPEE_AFFILIATE_ID
from redis_client import ja_enviado

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """Scraper para busca de produtos na Shopee."""
    # A Shopee usa uma estrutura de URL de busca específica
    url = f"https://shopee.com.br/search?keyword={termo}"

    try:
        time.sleep(random.uniform(2.0, 4.0)) # Delay maior para Shopee

        response = requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome124",
            timeout=30
        )

        if response.status_code != 200:
            print(f"Erro Shopee: Status {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Seleciona os cards de produto (a classe pode mudar, esta é a comum)
        produtos = soup.select('div[data-sqe="item"]')
        resultados = []

        for produto in produtos:
            if len(resultados) >= limite:
                break

            # Título
            titulo_tag = produto.select_one('div[data-sqe="name"]')
            if not titulo_tag: continue
            titulo = titulo_tag.get_text(strip=True)

            # Preço (A Shopee separa em partes às vezes)
            preco_tag = produto.select_one('span[class*="price"]')
            if not preco_tag: continue
            preco = preco_tag.get_text(strip=True).replace("R$", "").strip()

            # Link e ID (Extraído do href)
            link_tag = produto.find("a", href=True)
            if not link_tag: continue
            link_original = "https://shopee.com.br" + link_tag['href']
            
            # ID único para o Redis (geralmente o final da URL da Shopee)
            item_id = link_original.split("-i.")[-1].replace(".", "_")

            if ja_enviado(item_id):
                continue

            # Imagem
            img_tag = produto.find("img")
            imagem = img_tag.get("src") if img_tag else None

            # Link Afiliado (Exemplo de construção manual, verifique seu painel Shopee)
            # A Shopee geralmente exige conversão via API ou Deeplink
            link_afiliado = f"{link_original}?smtt=9&utm_source=an_18339480979"

            resultados.append({
                "id": item_id,
                "titulo": titulo,
                "preco": preco,
                "preco_antigo": None,
                "nota": "4.8",
                "avaliacoes": "100+",
                "imagem": imagem,
                "link": link_afiliado,
                "parcelas": "Até 12x",
                "frete": "Frete Grátis (consulte cupom)",
                "estoque": "Em estoque"
            })

        return resultados

    except Exception as e:
        print(f"Erro Shopee: {e}")
        return []