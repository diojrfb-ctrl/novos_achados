from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb
from redis_client import ja_enviado

def buscar_mercado_livre(termo="ofertas", limite=5):
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"
    try:
        response = requests.get(url, headers=HEADERS, impersonate="chrome110", timeout=15)
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".ui-search-result__wrapper") or soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break
            link_tag = item.select_one("a")
            if not link_tag: continue
            
            link = link_tag["href"].split("#")[0].split("?")[0]
            prod_id = extrair_mlb(link)
            if not prod_id or ja_enviado(prod_id): continue

            titulo_tag = item.select_one(".ui-search-item__title") or item.select_one(".poly-component__title")
            preco_tag = item.select_one(".andes-money-amount__fraction")
            img_tag = item.select_one("img")

            if not titulo_tag or not preco_tag: continue

            # ML usa lazy load (data-src) para imagens
            img_url = img_tag.get("data-src") or img_tag.get("src")

            resultados.append({
                "id": prod_id,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "link": f"{link}?matt_tool={MATT_TOOL}",
                "imagem": img_url,
                "tem_pix": "pix" in item.get_text().lower()
            })
        return resultados
    except: return []