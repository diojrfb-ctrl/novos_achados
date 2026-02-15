from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb
from redis_client import ja_enviado

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"
    
    try:
        response = requests.get(url, headers=HEADERS, impersonate="chrome110", timeout=15)
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".ui-search-result__wrapper") or \
                soup.select(".ui-search-layout__item") or \
                soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break

            link_tag = item.select_one("a")
            if not link_tag or not link_tag.get("href"): continue
            
            link = link_tag["href"]
            prod_id = extrair_mlb(link)
            if not prod_id: continue

            titulo_tag = item.select_one(".ui-search-item__title") or \
                         item.select_one(".poly-component__title")
            
            preco_tag = item.select_one(".andes-money-amount__fraction")

            if not titulo_tag or not preco_tag: continue

            status = "duplicado" if ja_enviado(prod_id) else "novo"
            texto_total = item.get_text(" ", strip=True).lower()

            resultados.append({
                "id": prod_id,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "link": f"{link}&matt_tool={MATT_TOOL}",
                "tem_pix": "pix" in texto_total,
                "mais_vendido": "vendido" in texto_total,
                "status": status
            })
            
        return resultados
    except Exception as e:
        print(f"[DEBUG ML] Erro: {e}")
        return []