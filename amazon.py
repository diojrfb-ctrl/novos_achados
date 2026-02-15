import requests
from bs4 import BeautifulSoup
from config import HEADERS, AMAZON_TAG
from utils import extrair_asin
from redis_client import ja_enviado

def gerar_link_amazon(url: str) -> str:
    if "tag=" in url:
        return url

    if "?" in url:
        return f"{url}&tag={AMAZON_TAG}"
    else:
        return f"{url}?tag={AMAZON_TAG}"

def buscar_amazon(termo: str = "ofertas", limite: int = 5) -> list[dict]:
    # URL de busca padrão
    url = f"https://www.amazon.com.br/s?k={termo}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        # Seletor para os blocos de produtos
        produtos = soup.select("div[data-component-type='s-search-result']")

        resultados = []

        for produto in produtos:
            if len(resultados) >= limite:
                break

            link_tag = produto.select_one("a.a-link-normal.s-no-outline")
            if not link_tag:
                continue

            link = "https://www.amazon.com.br" + link_tag["href"]
            asin = extrair_asin(link)

            # Verifica se já foi postado antes de continuar
            if not asin or ja_enviado(asin):
                continue

            titulo_tag = produto.select_one("h2 span")
            preco_tag = produto.select_one(".a-price-whole")

            if not titulo_tag or not preco_tag:
                continue

            # Captura o texto para identificar vantagens, mas não bloqueia mais o produto
            texto_completo = produto.get_text(" ", strip=True).lower()
            
            # Identifica se há menção a desconto no Pix ou Cupom
            tem_pix = "pix" in texto_completo or "boleto" in texto_completo
            tem_cupom = "cupom" in texto_completo or "aplicar" in texto_completo

            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "link": gerar_link_amazon(link),
                "tem_pix": tem_pix,
                "tem_cupom": tem_cupom
            })

        return resultados
    except Exception as e:
        print(f"Erro ao buscar na Amazon: {e}")
        return []