from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb, limpar_link_ml
from redis_client import ja_enviado
import re

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"
    try:
        response = requests.get(url, headers=HEADERS, impersonate="chrome110", timeout=15)
        if response.status_code != 200: return []
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break
            link_tag = item.select_one("a")
            if not link_tag: continue
            
            url_bruta = link_tag["href"]
            prod_id = extrair_mlb(url_bruta)
            if not prod_id: continue

            # Preço e Desconto
            fração = item.select_one(".andes-money-amount__fraction")
            valor_final = fração.get_text(strip=True) if fração else "0"
            
            antigo_tag = item.select_one(".andes-money-amount--previous .andes-money-amount__fraction")
            preco_antigo = antigo_tag.get_text(strip=True) if antigo_tag else None
            
            desc_tag = item.select_one(".andes-money-amount__discount")
            porcentagem = desc_tag.get_text(strip=True) if desc_tag else "0%"

            # Prova Social
            nota_tag = item.select_one(".poly-reviews__rating")
            qtd_tag = item.select_one(".poly-reviews__total")
            nota = nota_tag.get_text(strip=True) if nota_tag else "4.0"
            avaliacoes = re.sub(r'\D', '', qtd_tag.get_text()) if qtd_tag else "0"

            resultados.append({
                "id": prod_id,
                "titulo": item.select_one(".poly-component__title, .ui-search-item__title").get_text(strip=True),
                "preco": valor_final,
                "preco_antigo": preco_antigo,
                "desconto": porcentagem,
                "nota": nota,
                "avaliacoes": avaliacoes,
                "imagem": item.select_one("img").get("src") if item.select_one("img") else None,
                "link": limpar_link_ml(url_bruta, MATT_TOOL), # Link Limpo aqui
                "parcelas": item.select_one(".poly-component__installments").get_text(strip=True) if item.select_one(".poly-component__installments") else "Confira no site",
                "status": "duplicado" if ja_enviado(prod_id) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro ML: {e}")
        return []