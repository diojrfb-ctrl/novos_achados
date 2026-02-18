from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import random
import re
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """
    Busca produtos na Amazon Brasil mantendo apenas a nota (estrelas).
    """
    url = f"https://www.amazon.com.br/s?k={termo}"

    try:
        # Delay para evitar bloqueios
        time.sleep(random.uniform(1.5, 3.0))

        response = requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome124",
            timeout=25
        )

        if response.status_code != 200:
            print(f"Erro Amazon: Status {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})

        resultados = []

        for produto in produtos:
            if len(resultados) >= limite:
                break

            asin = produto.get("data-asin")
            if not asin:
                continue

            # Verificação de duplicados (Redis)
            if ja_enviado(asin):
                continue

            # =========================
            # TÍTULO
            # =========================
            titulo_tag = (
                produto.select_one("h2 a span") or 
                produto.select_one(".a-size-base-plus.a-color-base.a-text-normal") or
                produto.select_one("h2 span")
            )
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(" ", strip=True)

            # =========================
            # PREÇO ATUAL
            # =========================
            container = produto.select_one(".priceToPay") or produto.select_one(".a-price")
            if not container or container.find_parent(class_="pricePerUnit"):
                continue

            whole = container.select_one(".a-price-whole")
            fraction = container.select_one(".a-price-fraction")

            if not whole:
                continue

            valor_inteiro = re.sub(r"\D", "", whole.get_text())
            valor_centavos = re.sub(r"\D", "", fraction.get_text()) if fraction else "00"
            valor = f"{valor_inteiro},{valor_centavos}"

            # =========================
            # PREÇO ANTIGO
            # =========================
            antigo = produto.select_one(".a-price.a-text-price .a-offscreen")
            p_antigo = None
            if antigo:
                p_antigo = antigo.get_text(" ", strip=True).replace("R$", "").replace(".", "").strip()

            # =========================
            # APENAS A NOTA (ESTRELAS)
            # =========================
            nota_tag = (
                produto.select_one("i.a-icon-star-small span") or 
                # Seletor para página de detalhes se necessário
                produto.select_one("#acrPopover") or
                produto.select_one(".a-icon-star")
            )
            
            if nota_tag:
                nota_texto = nota_tag.get_text(" ", strip=True).replace(",", ".")
                match_nota = re.search(r"(\d+\.\d+|\d+)", nota_texto)
                nota = match_nota.group(1) if match_nota else "4.7"
            else:
                nota = "4.7"

            # =========================
            # IMAGEM E LINK
            # =========================
            img_tag = produto.select_one(".s-image")
            imagem = img_tag.get("src") if img_tag else None
            link = f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}"

            # =========================
            # RESULTADO FINAL (Sem 'avaliacoes')
            # =========================
            resultados.append({
                "id": asin,
                "titulo": titulo,
                "preco": valor,
                "preco_antigo": p_antigo,
                "nota": nota,
                "avaliacoes": "", # Removido o valor numérico
                "imagem": imagem,
                "link": link,
                "parcelas": "Confira no site",
                "frete": "Consulte o frete",
                "estoque": "Disponível"
            })

        return resultados

    except Exception as e:
        print(f"Erro crítico Amazon: {e}")
        return []