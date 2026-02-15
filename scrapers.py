import re
import random
from curl_cffi import requests
from bs4 import BeautifulSoup

class AmazonScraper:
    def __init__(self, store_id):
        self.store_id = store_id
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        # Termos que costumam ter descontos agressivos
        self.termos_promocionais = [
            "ofertas relampago", 
            "eletronicos em promocao", 
            "cozinha liquidacao", 
            "smartphone desconto",
            "casa inteligente alexa"
        ]

    def extrair_ofertas(self):
        termo = random.choice(self.termos_promocionais)
        # pct-off=15- filtra produtos com no mínimo 15% de desconto
        url = f"https://www.amazon.com.br/s?k={termo.replace(' ', '+')}&pct-off=15-&s=review-rank"
        
        print(f"🕵️ Investigando promoções para: '{termo}'")
        
        try:
            res = requests.get(url, headers=self.headers, impersonate="chrome120", timeout=30)
            if res.status_code != 200: return []

            soup = BeautifulSoup(res.text, "html.parser")
            produtos = []
            
            for item in soup.find_all("div", {"data-component-type": "s-search-result"}):
                link_tag = item.find("a", href=True)
                titulo_tag = item.find("h2")
                img_tag = item.find("img", {"class": "s-image"})
                
                # Preços: Atual e Antigo
                preco_atual_inteiro = item.find("span", {"class": "a-price-whole"})
                preco_atual_fracao = item.find("span", {"class": "a-price-fraction"})
                preco_antigo_tag = item.find("span", {"class": "a-offscreen"}) # Preço de lista

                if link_tag and titulo_tag and preco_atual_inteiro:
                    href = link_tag['href']
                    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", href)
                    
                    if asin_match:
                        asin = asin_match.group(1)
                        
                        # Formata preço atual
                        fracao = preco_atual_fracao.get_text().strip() if preco_atual_fracao else "00"
                        valor_atual = f"R$ {preco_atual_inteiro.get_text().strip()},{fracao}"
                        
                        # Captura preço antigo para mostrar o desconto
                        valor_antigo = preco_antigo_tag.get_text().strip() if preco_antigo_tag else ""
                        
                        # Se o preço antigo for igual ou menor (erro de scrap), ignoramos
                        if valor_antigo == valor_atual: valor_antigo = ""

                        produtos.append({
                            "id": asin,
                            "titulo": titulo_tag.get_text().strip()[:90],
                            "preco": valor_atual,
                            "preco_antigo": valor_antigo,
                            "imagem": img_tag['src'] if img_tag else None,
                            "url": f"https://www.amazon.com.br/dp/{asin}?tag={self.store_id}"
                        })
                
                if len(produtos) >= 3: break
            return produtos
        except Exception as e:
            print(f"❌ Erro no Scraper Amazon: {e}")
            return []