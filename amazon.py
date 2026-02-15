import requests
from bs4 import BeautifulSoup
from config import HEADERS, AMAZON_TAG
from utils import extrair_asin
from redis_client import ja_enviado

def gerar_link_amazon(url):
    if "tag=" in url:
        return url

    if "?" in url:
        return f"{url}&tag={AMAZON_TAG}"
    else:
        return f"{url}?tag={AMAZON_TAG}"

def buscar_amazon(termo="ofertas", limite=5):

    url = f"https://www.amazon.com.br/s?k={termo}"
    response = requests.get(url, headers=HEADERS, timeout=15)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    produtos = soup.select("div[data-component-type='s-search-result']")

    resultados = []

    for produto in produtos[:limite]:

        link_tag = produto.select_one("a.a-link-normal.s-no-outline")
        if not link_tag:
            continue

        link = "https://www.amazon.com.br" + link_tag["href"]
        asin = extrair_asin(link)

        if not asin or ja_enviado(asin):
            continue

        titulo_tag = produto.select_one("h2 span")
        preco_tag = produto.select_one(".a-price-whole")

        if not titulo_tag or not preco_tag:
            continue

        texto = produto.get_text(" ", strip=True).lower()

        if not ("off" in texto or "pix" in texto):
            continue

        resultados.append({
            "id": asin,
            "titulo": titulo_tag.get_text(strip=True),
            "preco": preco_tag.get_text(strip=True),
            "link": gerar_link_amazon(link),
            "tem_pix": "pix" in texto
        })

    return resultados
