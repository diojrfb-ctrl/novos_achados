from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import random
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    url = f"https://www.amazon.com.br/s?k={termo}&ref=nb_sb_noss"
    
    try:
        # Simula um delay humano antes da requisição
        time.sleep(random.uniform(1, 3))
        
        response = requests.get(
            url, 
            headers=HEADERS, 
            impersonate="chrome124", 
            timeout=20
        )
        
        if response.status_code != 200:
            print(f"[LOG AMAZON] Erro HTTP {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        # Tenta o seletor principal e um secundário
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"}) or \
                   soup.select(".s-result-item[data-asin]")
        
        print(f"[LOG AMAZON] Brutos: {len(produtos)}")

        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break

            asin = produto.get("data-asin")
            if not asin or len(asin) != 10: continue

            titulo_tag = produto.select_one("h2 span")
            preco_tag = produto.select_one(".a-price-whole")

            if not titulo_tag or not preco_tag:
                continue

            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "tem_pix": "pix" in produto.get_text().lower(),
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
            
        return resultados
    except Exception as e:
        print(f"[LOG AMAZON] Erro: {e}")
        return []