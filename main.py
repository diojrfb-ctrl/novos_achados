import asyncio, threading, os, io, requests, re
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def calcular_score(p: dict) -> int:
    score = 0
    # 1. Desconto (Pega o número da string '20% OFF')
    desc_val = int(re.search(r'\d+', p['desconto']).group()) if p.get('desconto') else 0
    if desc_val >= 40: score += 40
    elif desc_val >= 20: score += 20

    # 2. Avaliação (Filtro mínimo de 4.2)
    nota_float = float(p['nota'].replace(',', '.'))
    if nota_float >= 4.5: score += 25
    elif nota_float >= 4.2: score += 15
    else: score -= 20 # Penaliza produtos com nota baixa

    # 3. Popularidade (Mínimo 50 avaliações)
    qtd_aval = int(p['avaliacoes'])
    if qtd_aval > 100: score += 20
    elif qtd_aval > 50: score += 10

    # 4. Ticket Médio (Acima de 200 reais)
    preco_num = float(p['preco'].replace('.', '').replace(',', '.'))
    if preco_num > 200: score += 15

    return score

def gerar_copy_inteligente(p: dict) -> str:
    preco_atual = float(p['preco'].replace('.', '').replace(',', '.'))
    
    # Cabeçalho de Impacto
    copy = f"🤑 **ECONOMIA REAL DETECTADA**\n"
    copy += f"🔥 **{p['titulo']}**\n"
    copy += f"⭐ {p['nota']} ({p['avaliacoes']}+ avaliações)\n\n"
    
    if p.get('preco_antigo'):
        preco_antigo = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
        economia_reais = preco_antigo - preco_atual
        if economia_reais > 0:
            copy += f"💰 ~~R$ {p['preco_antigo']}~~\n"
            copy += f"✅ **R$ {p['preco']}**\n"
            copy += f"📉 **VOCÊ ECONOMIZA: R$ {economia_reais:.2f}**\n"
    else:
        copy += f"💰 **PREÇO: R$ {p['preco']}**\n"

    copy += f"\n💳 {p['parcelas']}\n"
    copy += f"⏱️ *OFERTA POR TEMPO LIMITADO!*\n\n"
    
    # Link Limpo com UTM de categoria para rastreio
    tag = "ofertas" # Poderia ser dinâmico por categoria
    link_final = f"{p['link']}&utm_campaign={tag}"
    
    copy += f"🔗 **COMPRE NO SITE OFICIAL:**\n{link_final}\n\n"
    copy += f"➡️ #OfertaVerificada #MercadoLivre"
    return copy

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    for p in produtos:
        if p.get('status') == "duplicado" and not modo_teste: continue
        
        # FILTRO DE SCORE (Só posta se for acima de 60)
        score = calcular_score(p)
        if score < 60 and not modo_teste:
            print(f"Low score ({score}): {p['titulo']}")
            continue

        try:
            caption = gerar_copy_inteligente(p)
            if p.get("imagem"):
                r = requests.get(p["imagem"], timeout=10)
                if r.status_code == 200:
                    foto = io.BytesIO(r.content)
                    foto.name = 'post.jpg'
                    await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
            
            if not modo_teste:
                marcar_enviado(p["id"])
                await asyncio.sleep(20) # Cooldown
        except Exception as e:
            print(f"Erro ao postar: {e}")

async def main():
    await client.start()
    while True:
        try:
            # Roda as buscas
            await processar_plataforma("ML", buscar_mercado_livre())
            await asyncio.sleep(60)
            await processar_plataforma("AMZ", buscar_amazon())
        except Exception as e:
            print(f"Erro no loop: {e}")
        await asyncio.sleep(3600)

if __name__ == "__main__":
    # Flask para Health Check no Render
    app = Flask(__name__)
    @app.route('/')
    def health(): return "OK", 200
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.run(main())