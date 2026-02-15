import requests
from bs4 import BeautifulSoup
from config import HEADERS, AMAZON_TAG
from utils import extrair_asin
from redis_client import ja_enviado

def gerar_link_amazon(url: str) -> str:
    if "tag=" in url:
        return url
    return f"{url}&tag={AMAZON_TAG}" if "?" in url else f"{url}?tag={AMAZON_TAG}"

def buscar_amazon(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    # URL focada em resultados de busca reais
    url = f"https://www.amazon.com.br/s?k={termo}&ref=nb_sb_noss"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        # Log interno se houver bloqueio
        if response.status_code != 200:
            print(f"Erro Amazon: Status {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Seletores atualizados para 2026
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        resultados = []
        for produto in produtos[:limite]:
            # Pega o ASIN diretamente do atributo do site
            asin = produto.get("data-asin")
            if not asin or ja_enviado(asin):
                continue

            # Busca título e link com seletores mais abrangentes
            h2 = produto.find("h2")
            if not h2: continue
            
            titulo = h2.get_text(strip=True)
            link_tag = h2.find("a", href=True)
            if not link_tag: continue
            
            link = "https://www.amazon.com.br" + link_tag["href"]
            
            # Busca preço (pode variar a classe, tentamos as mais comuns)
            preco_tag = produto.select_one(".a-price-whole")
            if not preco_tag: continue
            
            preco = preco_tag.get_text(strip=True)
            texto_completo = produto.get_text(" ", strip=True).lower()

            resultados.append({
                "id": asin,
                "titulo": titulo,
                "preco": preco,
                "link": gerar_link_amazon(link),
                "tem_pix": "pix" in texto_completo or "boleto" in texto_completo,
                "tem_cupom": "cupom" in texto_completo or "aplicar" in texto_completo,
                "status": "novo"
            })
            
        return resultados
    except Exception as e:
        print(f"Falha na raspagem Amazon: {e}")
        return []