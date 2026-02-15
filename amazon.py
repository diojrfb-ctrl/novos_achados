from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, AMAZON_TAG
from utils import extrair_asin
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    url = f"https://www.amazon.com.br/s?k={termo}"
    
    try:
        # curl_cffi imita o Chrome 120 perfeitamente
        response = requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=15)
        
        print(f"[LOG AMAZON] Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[LOG AMAZON] Erro de acesso. Status: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        print(f"[LOG AMAZON] Itens brutos encontrados: {len(produtos)}")

        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break

            asin = produto.get("data-asin")
            if not asin: continue

            titulo_tag = produto.select_one("h2 span")
            preco_tag = produto.select_one(".a-price-whole")

            if not titulo_tag or not preco_tag:
                continue

            # OK: Produto válido capturado
            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": preco_tag.get_text(strip=True),
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "tem_pix": "pix" in produto.get_text().lower(),
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
            
        return resultados
    except Exception as e:
        print(f"[LOG AMAZON] Erro crítico: {e}")
        return []