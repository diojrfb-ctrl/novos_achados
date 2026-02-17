from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"
    try:
        response = requests.get(url, headers=HEADERS, impersonate="chrome110", timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break
            
            # Tenta capturar se existe uma variação específica no texto (ex: "250g")
            titulo_bruto = item.select_one(".poly-component__title, .ui-search-item__title").get_text(strip=True)
            
            # Captura do preço promocional
            f = item.select_one(".poly-price__current .andes-money-amount__fraction")
            c = item.select_one(".poly-price__current .andes-money-amount__cents")
            valor_promo = f.get_text(strip=True) if f else "0"
            if c: valor_promo += f",{c.get_text(strip=True)}"
            
            # Preço Antigo
            antigo_tag = item.select_one(".andes-money-amount--previous .andes-money-amount__fraction")
            preco_antigo = antigo_tag.get_text(strip=True) if antigo_tag else None
            
            link_tag = item.select_one("a")
            if not link_tag: continue
            
            id_mlb = extrair_mlb(link_tag["href"])
            if not id_mlb: continue

            # Link limpo para o Hyperlink
            link_final = f"https://www.mercadolivre.com.br/p/{id_mlb}?matt_tool={MATT_TOOL}"

            resultados.append({
                "id": id_mlb,
                "titulo": titulo_bruto,
                "preco": valor_promo,
                "preco_antigo": preco_antigo,
                "loja": item.select_one(".poly-component__seller").get_text(strip=True) if item.select_one(".poly-component__seller") else "Loja Oficial",
                "link": link_final,
                "imagem": item.select_one("img").get("src")
            })
        return resultados
    except: return []