import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb
from redis_client import ja_enviado

def gerar_link_ml(url):
    if "matt_tool=" in url:
        return url

    if "?" in url:
        return f"{url}&matt_tool={MATT_TOOL}"
    else:
        return f"{url}?matt_tool={MATT_TOOL}"

def buscar_mercado_livre(termo="ofertas", limite=5):

    url = f"https://lista.mercadolivre.com.br/{termo}"
    response = requests.get(url, headers=HEADERS, timeout=15)

    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    produtos = soup.select(".ui-search-result__wrapper")

    resultados = []

    for produto in produtos[:limite]:

        link_tag = produto.select_one("a.ui-search-link")
        if not link_tag:
            continue

        link = link_tag["href"]
        prod_id = extrair_mlb(link)

        if not prod_id or ja_enviado(prod_id):
            continue

        preco_tag = produto.select_one(".andes-money-amount__fraction")
        if not preco_tag:
            continue

        texto = produto.get_text(" ", strip=True).lower()

        if not ("off" in texto or "pix" in texto or "vendido" in texto):
            continue

        resultados.append({
            "id": prod_id,
            "titulo": link_tag.get_text(strip=True),
            "preco": preco_tag.get_text(strip=True),
            "link": gerar_link_ml(link),
            "tem_pix": "pix" in texto,
            "mais_vendido": "vendido" in texto
        })

    return resultados
