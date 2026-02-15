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
        self.buscas = ["ofertas do dia", "eletronicos", "casa inteligente", "cozinha"]

    def extrair_ofertas(self):
        termo = random.choice(self.buscas)
        url = f"https://www.amazon.com.br/s?k={termo.replace(' ', '+')}&s=review-rank"

        try:
            res = requests.get(url, headers=self.headers, impersonate="chrome120", timeout=30)
            if res.status_code != 200: return []

            soup = BeautifulSoup(res.text, "html.parser")
            produtos = []

            for item in soup.find_all("div", {"data-component-type": "s-search-result"}):
                link_tag = item.find("a", href=True)
                titulo_tag = item.find("h2")
                img_tag = item.find("img", {"class": "s-image"})
                preco_tag = item.find("span", {"class": "a-price-whole"})

                if link_tag and titulo_tag:
                    href = link_tag['href']
                    asin_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", href)

                    if asin_match:
                        asin = asin_match.group(1)
                        produtos.append({
                            "id": asin,
                            "titulo": titulo_tag.get_text().strip()[:90],
                            "preco": f"R$ {preco_tag.get_text().strip()}" if preco_tag else "Ver no site",
                            "imagem": img_tag['src'] if img_tag else None,
                            "url": f"https://www.amazon.com.br/dp/{asin}?tag={self.store_id}",
                            "premium": "4.5 de 5" in str(item)
                        })
                if len(produtos) >= 3: break
            return produtos
        except Exception as e:
            print(f"Erro Scraper Amazon: {e}")
            return []