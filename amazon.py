from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    # URL com parâmetros de busca mais naturais
    url = f"https://www.amazon.com.br/s?k={termo}&ref=nb_sb_noss"
    
    try:
        # impersonate="chrome124" é mais atualizado contra WAF
        response = requests.get(
            url, 
            headers=HEADERS, 
            impersonate="chrome124", 
            timeout=20
        )
        
        print(f"[LOG AMAZON] Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[LOG AMAZON] Bloqueio detectado ou erro: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        # Seletor robusto para 2026
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        if not produtos:
            # Tentativa secundária se o layout mudar
            produtos = soup.select(".s-result-item[data-asin]")

        print(f"[LOG AMAZON] Itens brutos encontrados: {len(produtos)}")

        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break

            asin = produto.get("data-asin")
            if not asin or asin == "": continue

            # Seletores atualizados
            titulo_tag = produto.select_one("h2 span")
            preco_tag = produto.select_one(".a-price-whole")

            if not titulo_tag or not preco_tag:
                continue

            titulo = titulo_tag.get_text(strip=True)
            preco = preco_tag.get_text(strip=True)

            resultados.append({
                "id": asin,
                "titulo": titulo,
                "preco": preco,
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "tem_pix": "pix" in produto.get_text().lower(),
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
            
        return resultados
    except Exception as e:
        print(f"[LOG AMAZON] Erro crítico: {e}")
        return []