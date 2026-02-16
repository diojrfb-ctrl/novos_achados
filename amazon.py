from curl_cffi import requests
from bs4 import BeautifulSoup
import time, random, re
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    url = f"https://www.amazon.com.br/s?k={termo}"
    try:
        time.sleep(random.uniform(1, 2))
        response = requests.get(url, headers=HEADERS, impersonate="chrome124", timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break
            asin = produto.get("data-asin")
            if not asin: continue

            # Preço Final (Proteção contra preço por litro)
            container = produto.select_one(".priceToPay") or produto.select_one(".a-price")
            if not container or container.find_parent(class_="pricePerUnit"): continue
            
            f = container.select_one(".a-price-whole")
            c = container.select_one(".a-price-fraction")
            if not f: continue
            valor = f"{re.sub(r'\D', '', f.get_text())},{re.sub(r'\D', '', c.get_text()) if c else '00'}"

            # Preço Antigo
            antigo = produto.select_one(".a-price.a-text-price .a-offscreen")
            p_antigo = antigo.get_text(strip=True).replace("R$", "").strip() if antigo else None

            # Nota e Avaliações
            nota_str = produto.select_one("i.a-icon-star-small span")
            qtd_str = produto.select_one("span.a-size-base.s-underline-text")
            
            nota = nota_str.get_text(strip=True).split()[0].replace(",", ".") if nota_str else "4.0"
            avaliacoes = re.sub(r'\D', '', qtd_str.get_text()) if qtd_str else "0"

            resultados.append({
                "id": asin,
                "titulo": produto.select_one("h2 span").get_text(strip=True),
                "preco": valor,
                "preco_antigo": p_antigo,
                "desconto": "OFERTA",
                "nota": nota,
                "avaliacoes": avaliacoes,
                "imagem": produto.select_one(".s-image").get("src"),
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "parcelas": "Confira no site",
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
        return resultados
    except: return []