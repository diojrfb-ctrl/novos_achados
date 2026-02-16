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

            # --- CAPTURA DO PREÇO PROMOCIONAL ---
            # O ML coloca o preço atual (promocional) na classe principal
            container_preco = item.select_one(".poly-price__current") or item
            fração = container_preco.select_one(".andes-money-amount__fraction")
            centavos = container_preco.select_one(".andes-money-amount__cents")
            
            valor_promo = fração.get_text(strip=True) if fração else "0"
            if centavos: valor_promo += f",{centavos.get_text(strip=True)}"

            # Preço Antigo (Para cálculo de economia)
            antigo_tag = item.select_one(".andes-money-amount--previous .andes-money-amount__fraction")
            p_antigo = antigo_tag.get_text(strip=True) if antigo_tag else None
            
            desc_tag = item.select_one(".andes-money-amount__discount")
            porcentagem = desc_tag.get_text(strip=True) if desc_tag else "0%"

            # Prova Social
            nota = item.select_one(".poly-reviews__rating").get_text(strip=True) if item.select_one(".poly-reviews__rating") else "4.5"
            aval = re.sub(r'\D', '', item.select_one(".poly-reviews__total").get_text()) if item.select_one(".poly-reviews__total") else "50"

            resultados.append({
                "id": prod_id,
                "titulo": item.select_one(".poly-component__title, .ui-search-item__title").get_text(strip=True),
                "preco": valor_promo, # Este é o preço com desconto
                "preco_antigo": p_antigo,
                "desconto": porcentagem,
                "nota": nota,
                "avaliacoes": aval,
                "imagem": item.select_one("img").get("src") if item.select_one("img") else None,
                "link": limpar_link_ml(url_bruta, MATT_TOOL),
                "parcelas": item.select_one(".poly-component__installments").get_text(strip=True) if item.select_one(".poly-component__installments") else "Confira no site",
                "status": "duplicado" if ja_enviado(prod_id) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro ML: {e}")
        return []