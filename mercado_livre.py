from curl_cffi import requests
from bs4 import BeautifulSoup
from config import HEADERS, MATT_TOOL
from utils import extrair_mlb
from redis_client import ja_enviado

def buscar_mercado_livre(termo: str = "ofertas", limite: int = 10) -> list[dict]:
    # Alteramos para a URL de ofertas oficiais que é mais estável
    url = f"https://www.mercadolivre.com.br/ofertas?keywords={termo}"
    
    try:
        # Usamos impersonate chrome110 para variar um pouco da Amazon
        response = requests.get(url, headers=HEADERS, impersonate="chrome110", timeout=15)
        
        # Log para você ver no console do Render se o erro é 403 (Bloqueio)
        print(f"[DEBUG ML] Status Code: {response.status_code}")
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        
        # O ML mudou muitos seletores para 'poly-card'. Vamos tentar todos os conhecidos:
        items = soup.select(".ui-search-result__wrapper") or \
                soup.select(".ui-search-layout__item") or \
                soup.select(".poly-card") or \
                soup.select(".promotion-item")

        print(f"[DEBUG ML] Itens brutos encontrados: {len(items)}")

        resultados = []
        for item in items:
            if len(resultados) >= limite: break

            # Tenta pegar o link de diferentes formas
            link_tag = item.select_one("a")
            if not link_tag or not link_tag.get("href"): continue
            
            link = link_tag["href"]
            if "click.mercadolivre" in link: continue # Pula anúncios pagos/externos
            
            prod_id = extrair_mlb(link)
            if not prod_id: continue

            # Seletores de Título e Preço atualizados 2026
            titulo_tag = item.select_one(".ui-search-item__title") or \
                         item.select_one(".poly-component__title") or \
                         item.select_one(".promotion-item__title")
            
            preco_tag = item.select_one(".andes-money-amount__fraction")

            if not titulo_tag or not preco_tag: continue

            titulo = titulo_tag.get_text(strip=True)
            preco = preco_tag.get_text(strip=True)
            
            # Verifica no Redis
            status = "duplicado" if ja_enviado(prod_id) else "novo"
            
            texto_completo = item.get_text(" ", strip=True).lower()

            resultados.append({
                "id": prod_id,
                "titulo": titulo,
                "preco": preco,
                "link": f"{link}&matt_tool={MATT_TOOL}",
                "tem_pix": "pix" in texto_completo,
                "mais_vendido": "vendido" in texto_completo,
                "status": status
            })
            
        return resultados
    except Exception as e:
        print(f"[DEBUG ML] Erro crítico: {e}")
        return []