from curl_cffi import requests
from bs4 import BeautifulSoup
import time
import random
import re
from config import HEADERS, AMAZON_TAG
from redis_client import ja_enviado

def buscar_amazon(termo: str = "ofertas", limite: int = 15) -> list[dict]:
    """
    Busca produtos na Amazon Brasil e retorna uma lista de dicionários formatados.
    Ajustado para capturar o título completo do produto e não apenas a marca.
    """
    url = f"https://www.amazon.com.br/s?k={termo}"

    try:
        # Delay randômico para evitar detecção de bot
        time.sleep(random.uniform(1.2, 2.5))

        response = requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome124",
            timeout=20
        )

        if response.status_code != 200:
            print(f"Erro Amazon: Status {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        # Seleciona os containers de produtos
        produtos = soup.find_all("div", {"data-component-type": "s-search-result"})

        resultados = []

        for produto in produtos:
            if len(resultados) >= limite:
                break

            asin = produto.get("data-asin")
            if not asin:
                continue

            # ❌ Ignora se já enviado (pode ser removido se o controle for feito apenas no main)
            if ja_enviado(asin):
                continue

            # =========================
            # PREÇO ATUAL
            # =========================
            container = (
                produto.select_one(".priceToPay")
                or produto.select_one(".a-price")
            )

            # Ignora se for preço por unidade (ex: R$ 0,10/unidade)
            if not container or container.find_parent(class_="pricePerUnit"):
                continue

            whole = container.select_one(".a-price-whole")
            fraction = container.select_one(".a-price-fraction")

            if not whole:
                continue

            valor_inteiro = re.sub(r"\D", "", whole.get_text())
            valor_centavos = (
                re.sub(r"\D", "", fraction.get_text())
                if fraction else "00"
            )

            if not valor_inteiro:
                continue

            valor = f"{valor_inteiro},{valor_centavos}"

            # =========================
            # PREÇO ANTIGO (Mantido para o dicionário, o main decide se exibe)
            # =========================
            antigo = produto.select_one(".a-price.a-text-price .a-offscreen")
            p_antigo = None

            if antigo:
                antigo_texto = antigo.get_text(" ", strip=True)
                # Limpa para formato numérico caso precise de cálculo
                p_antigo = (
                    antigo_texto
                    .replace("R$", "")
                    .replace(".", "")
                    .strip()
                )

            # =========================
            # TÍTULO (CORRIGIDO)
            # =========================
            # Busca especificamente dentro do H2, que contém o nome completo do produto
            titulo_tag = (
                produto.select_one("h2 a span") 
                or produto.select_one(".a-size-base-plus.a-color-base.a-text-normal")
            )
            
            if not titulo_tag:
                continue

            titulo = titulo_tag.get_text(" ", strip=True)

            # =========================
            # AVALIAÇÃO
            # =========================
            nota_tag = produto.select_one("i.a-icon-star-small span")
            qtd_tag = produto.select_one("span.a-size-base.s-underline-text")

            nota = (
                nota_tag.get_text(" ", strip=True)
                .split()[0]
                .replace(",", ".")
                if nota_tag else "4.7"
            )

            avaliacoes = (
                re.sub(r"\D", "", qtd_tag.get_text())
                if qtd_tag else "50"
            )

            # =========================
            # IMAGEM
            # =========================
            img_tag = produto.select_one(".s-image")
            imagem = img_tag.get("src") if img_tag else None

            # =========================
            # LINK AFILIADO
            # =========================
            link = f"https://www.amazon.com.br/dp/{asin}?tag={AMAZON_TAG}"

            # Append dos dados normalizados
            resultados.append({
                "id": asin,
                "titulo": titulo,
                "preco": valor,
                "preco_antigo": p_antigo,
                "nota": nota,
                "avaliacoes": avaliacoes,
                "imagem": imagem,
                "link": link,
                "parcelas": "Confira no site",
                "frete": "Consulte o frete",
                "estoque": "Disponível"
            })

        return resultados

    except Exception as e:
        print(f"Erro ao buscar Amazon: {e}")
        return []