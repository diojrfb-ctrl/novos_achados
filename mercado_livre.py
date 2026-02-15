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
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break

            link_tag = item.select_one("a")
            if not link_tag: continue
            
            link = link_tag["href"]
            prod_id = extrair_mlb(link)
            if not prod_id: continue

            # Captura de Imagem Original
            img_tag = item.select_one("img")
            img_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else None
            if img_url:
                img_url = img_url.replace("-I.jpg", "-O.jpg").replace("-V.jpg", "-O.jpg")

            # Título
            titulo = item.select_one(".poly-component__title, .ui-search-item__title").get_text(strip=True)
            
            # Preços: O ML mostra o preço atual na classe principal
            preco_atual = item.select_one(".andes-money-amount__fraction").get_text(strip=True)
            
            # Tenta capturar preço antigo/original para mostrar o desconto
            preco_antigo_tag = item.select_one(".andes-money-amount__price--previous .andes-money-amount__fraction")
            preco_antigo = preco_antigo_tag.get_text(strip=True) if preco_antigo_tag else None

            # Prova Social e Descontos
            texto_item = item.get_text(" ", strip=True).lower()
            
            desconto_tag = item.select_one(".andes-money-amount__discount, .ui-search-price__discount")
            porcentagem_off = desconto_tag.get_text(strip=True) if desconto_tag else None

            vendas = "Novo"
            if "vendido" in texto_item:
                if "+500" in texto_item: vendas = "📦 +500 vendidos"
                elif "+10mil" in texto_item: vendas = "📦 +10mil vendidos"
                else: vendas = "📦 Destaque em vendas"

            avaliacao = "⭐ 4.8+" if "4." in texto_item else None

            resultados.append({
                "id": prod_id,
                "titulo": titulo,
                "preco": preco_atual,
                "preco_antigo": preco_antigo,
                "desconto": porcentagem_off,
                "imagem": img_url,
                "link": f"{link}&matt_tool={MATT_TOOL}",
                "vendas": vendas,
                "avaliacao": avaliacao,
                "parcelas": item.select_one(".poly-component__installments").get_text(strip=True) if item.select_one(".poly-component__installments") else "Confira parcelas",
                "status": "duplicado" if ja_enviado(prod_id) else "novo"
            })
            
        return resultados
    except Exception as e:
        print(f"Erro ML: {e}")
        return []