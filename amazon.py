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

            # --- CAPTURA DE PREÇO APERFEIÇOADA ---
            # Buscamos especificamente o container 'priceToPay' para evitar o preço por litro/unidade
            preco_venda_container = produto.select_one(".priceToPay .a-price") or produto.select_one(".a-price")
            
            if not preco_venda_container: continue

            fração = preco_venda_container.select_one(".a-price-whole")
            centavos = preco_venda_container.select_one(".a-price-fraction")
            
            if not fração: continue
            
            # Limpeza do valor (remove pontos de milhar se houver)
            valor_final = fração.get_text(strip=True).replace(".", "").replace(",", "")
            if centavos:
                valor_final += f",{centavos.get_text(strip=True)}"

            # --- PREÇO ANTIGO (DE LISTA) ---
            # Na Amazon, o preço antigo costuma ficar em um span separado com classe 'a-text-price'
            # e NÃO deve estar dentro de 'priceToPay'
            preco_antigo_tag = produto.select_one(".a-price.a-text-price:not(.priceToPay) .a-offscreen")
            preco_antigo = None
            if preco_antigo_tag:
                preco_antigo = preco_antigo_tag.get_text(strip=True).replace("R$", "").strip()

            # --- TÍTULO E IMAGEM ---
            titulo_tag = produto.select_one("h2 span")
            img_tag = produto.select_one(".s-image")
            if not titulo_tag: continue

            texto_todo = produto.get_text().lower()
            
            # --- PARCELAMENTO ---
            parcelas = "Consulte parcelamento no site"
            # Regex para pegar algo como "10x de R$ 50,00"
            match_parc = re.search(r"em até (\d+x.*?de\s+r\$\s?[\d,.]+)", texto_todo)
            if match_parc: 
                parcelas = f"Em até {match_parc.group(1)}"

            # --- DESCONTO ---
            # Tenta pegar a tag de porcentagem (ex: -15%)
            desconto_tag = produto.select_one(".a-color-base.a-text-bold") # Comum em badges de oferta
            porcentagem = None
            if desconto_tag and "%" in desconto_tag.get_text():
                porcentagem = desconto_tag.get_text(strip=True)

            resultados.append({
                "id": asin,
                "titulo": titulo_tag.get_text(strip=True),
                "preco": valor_final,
                "preco_antigo": preco_antigo,
                "desconto": porcentagem or "OFERTA",
                "imagem": img_tag.get("src") if img_tag else None,
                "link": f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}",
                "parcelas": parcelas,
                "vendas": "🔥 1º mais vendido" if "1º mais vendido" in texto_todo else "📦 +10 mil compras no mês passado" if "10 mil" in texto_todo else "📦 Novo",
                "avaliacao": "⭐ Ver avaliações" if "estrelas" in texto_todo else None,
                "status": "duplicado" if ja_enviado(asin) else "novo"
            })
        return resultados
    except Exception as e:
        print(f"Erro Amazon: {e}")
        return []