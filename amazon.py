import requests
from bs4 import BeautifulSoup
from config import HEADERS, AMAZON_TAG
from utils import extrair_asin
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    # URL com parâmetros que simulam uma busca orgânica
    url = f"https://www.amazon.com.br/s?k={termo}&ref=nb_sb_noss"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        # Seleciona os containers de produtos
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break

            asin = produto.get("data-asin")
            if not asin: continue

            # Tenta pegar o título de várias formas
            titulo_tag = produto.select_one("h2 span") or produto.select_one(".a-size-base-plus")
            if not titulo_tag: continue
            titulo = titulo_tag.get_text(strip=True)

            # Tenta pegar o preço
            preco_tag = produto.select_one(".a-price-whole")
            if not preco_tag: continue
            preco = preco_tag.get_text(strip=True)

            status = "duplicado" if ja_enviado(asin) else "novo"
            texto_todo = produto.get_text(" ").lower()

            resultados.append({
                "id": asin,
                "titulo": titulo,
                "preco": preco,
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "tem_pix": "pix" in texto_todo or "boleto" in texto_todo,
                "status": status
            })
        return resultados
    except:
        return []