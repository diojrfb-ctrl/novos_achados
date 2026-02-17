from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb, limpar_para_link_normal
from redis_client import ja_enviado # Importado para evitar duplicatas
import re

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"
    try:
        response = requests.get(url, headers=HEADERS, impersonate="chrome110", timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break
            link_tag = item.select_one("a")
            if not link_tag: continue
            
            url_original = link_tag["href"]
            prod_id = extrair_mlb(url_original)
            
            # Se não conseguir extrair o ID (MLB), usamos a URL como ID para o Redis
            id_referencia = prod_id if prod_id else url_original
            
            # Verifica se já foi enviado para não repetir ofertas patrocinadas
            if ja_enviado(id_referencia):
                continue

            # Agora o link final mantém toda a estrutura original + seu matt_tool
            link_final = limpar_para_link_normal(url_original, MATT_TOOL)

            # Preço e Título
            f = item.select_one(".poly-price__current .andes-money-amount__fraction")
            c = item.select_one(".poly-price__current .andes-money-amount__cents")
            valor_promo = f.get_text(strip=True) if f else "0"
            if c: valor_promo += f",{c.get_text(strip=True)}"

            antigo_tag = item.select_one(".andes-money-amount--previous .andes-money-amount__fraction")
            p_antigo = antigo_tag.get_text(strip=True) if antigo_tag else None
            
            resultados.append({
                "id": id_referencia,
                "titulo": item.select_one(".poly-component__title, .ui-search-item__title").get_text(strip=True),
                "preco": valor_promo,
                "preco_antigo": p_antigo,
                "loja": item.select_one(".poly-component__seller").get_text(strip=True) if item.select_one(".poly-component__seller") else "Mercado Livre",
                "link": link_final,
                "imagem": item.select_one("img").get("src"),
                "nota": item.select_one(".poly-reviews__rating").get_text(strip=True) if item.select_one(".poly-reviews__rating") else "4.8",
                "avaliacoes": re.sub(r'\D', '', item.select_one(".poly-reviews__total").get_text()) if item.select_one(".poly-reviews__total") else "100"
            })
        return resultados
    except Exception as e:
        print(f"Erro ao buscar ML: {e}")
        return []