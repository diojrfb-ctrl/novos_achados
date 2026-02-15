from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo="ofertas", limite=5):
    url = f"https://www.amazon.com.br/s?k={termo}"
    try:
        # impersonate="chrome120" evita o bloqueio que você viu antes
        response = requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=15)
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.select("div[data-component-type='s-search-result']")
        
        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break
            asin = produto.get("data-asin")
            if not asin or ja_enviado(asin): continue

            titulo_tag = produto.select_one("h2 span")
            preco_tag = produto.select_one(".a-price-whole")
            img_tag = produto.select_one(".s-image")
            
            if not titulo_tag or not preco_tag: continue

            # Tenta pegar a imagem de alta resolução se disponível
            img_url = img_tag["src"] if img_tag else None

            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "imagem": img_url,
                "tem_pix": "pix" in produto.get_text().lower()
            })
        return resultados
    except: return []