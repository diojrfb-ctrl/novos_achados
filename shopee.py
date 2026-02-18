from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import random
import re
from config import HEADERS
from redis_client import ja_enviado
from seguranca import eh_produto_seguro

def buscar_shopee(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """Scraper robusto para Shopee com integração de segurança."""
    url = f"https://shopee.com.br/search?keyword={termo}"
    
    # Cookie aleatório para simular visita real
    cookies = {"shopee_web_id": str(random.randint(10**10, 10**11))}

    try:
        time.sleep(random.uniform(4.0, 6.0)) 

        response = requests.get(
            url,
            headers=HEADERS,
            cookies=cookies,
            impersonate="chrome124",
            timeout=30
        )

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        # Seletores variados (Shopee muda as classes toda hora)
        produtos = soup.select('div[data-sqe="item"]') or soup.select('.shopee-search-item-result__item')
        
        resultados = []

        for produto in produtos:
            if len(resultados) >= limite:
                break

            # Título (Busca em múltiplos lugares)
            titulo_tag = produto.select_one('div[data-sqe="name"]') or produto.select_one('img[alt]')
            titulo = ""
            if titulo_tag:
                titulo = titulo_tag.get_text(strip=True) if not titulo_tag.get('alt') else titulo_tag.get('alt')
            
            if not titulo or not eh_produto_seguro(titulo):
                continue

            # Link e ID
            link_tag = produto.find("a", href=True)
            if not link_tag: continue
            link_original = "https://shopee.com.br" + link_tag['href']
            
            match_id = re.search(r"i\.(\d+\.\d+)", link_original)
            item_id = match_id.group(1) if match_id else link_original.split("/")[-1]

            if ja_enviado(item_id):
                continue

            # Preço
            preco_tag = produto.find("span", string=re.compile(r'R\$')) or produto.select_one('div[class*="price"]')
            preco = re.sub(r'[^\d,]', '', preco_tag.get_text()).strip() if preco_tag else "Confira"
            
            # Imagem
            img_tag = produto.find("img")
            imagem = img_tag.get("src") if img_tag else None

            resultados.append({
                "id": item_id,
                "titulo": titulo,
                "preco": preco,
                "preco_antigo": None,
                "nota": "4.8",
                "avaliacoes": "", 
                "imagem": imagem,
                "link": f"{link_original}?utm_source=an_18339480979",
                "parcelas": "Até 12x",
                "frete": "Frete grátis (com cupom)",
                "estoque": "Disponível"
            })

        return resultados
    except Exception as e:
        print(f"Erro Shopee: {e}")
        return []