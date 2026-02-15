from curl_cffi import requests
from bs4 import BeautifulSoup
import time, random, re
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    url = f"https://www.amazon.com.br/s?k={termo}"
    try:
        time.sleep(random.uniform(1, 3))
        response = requests.get(url, headers=HEADERS, impersonate="chrome124", timeout=20)
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        resultados = []
        for produto in produtos:
            if len(resultados) >= limite: break
            asin = produto.get("data-asin")
            if not asin: continue

            # --- CAPTURA DE PREÇO E DESCONTO ---
            # Preço Atual (o que o cliente paga)
            preco_venda_container = produto.select_one(".a-price")
            fração = produto.select_one(".a-price-whole")
            centavos = produto.select_one(".a-price-fraction")
            
            if not fração: continue # Se não tem preço, pula o produto
            
            valor_final = fração.get_text(strip=True).replace(".", "")
            if centavos:
                valor_final += f",{centavos.get_text(strip=True)}"

            # Preço Antigo (Preço de Lista / Riscado)
            preco_antigo_tag = produto.select_one(".a-price.a-text-price .a-offscreen")
            preco_antigo = None
            if preco_antigo_tag:
                # Remove o "R$" e espaços para padronizar
                preco_antigo = preco_antigo_tag.get_text(strip=True).replace("R$", "").strip()

            # Desconto (Cálculo ou Tag)
            desconto_tag = produto.select_one(".a-letterpress") # Às vezes aparece como "10% de desconto"
            porcentagem = desconto_tag.get_text(strip=True) if desconto_tag else None
            
            # Se não achou a tag de desconto mas tem preço antigo, podemos deixar o bot calcular 
            # ou apenas exibir o preço riscado.

            # --- TÍTULO E IMAGEM ---
            titulo_tag = produto.select_one("h2 span")
            img_tag = produto.select_one(".s-image")
            
            if not titulo_tag: continue

            texto_todo = produto.get_text().lower()
            
            # --- PARCELAMENTO ---
            parcelas = "Consulte parcelamento no site"
            match_parc = re.search(r"em até (\d+x.*?de\s+r\$\s?[\d,.]+)", texto_todo)
            if match_parc: 
                parcelas = f"Em até {match_parc.group(1)}"

            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": valor_final,
                "preco_antigo": preco_antigo,
                "desconto": porcentagem,
                "imagem": img_tag.get("src") if img_tag else None,
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "parcelas": parcelas,
                "vendas": "🔥 Oferta em destaque" if "mais vendido" in texto_todo else "📦 Novo",
                "avaliacao": "⭐ Ver avaliações" if "estrelas" in texto_todo else None,
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro Amazon: {e}")
        return []