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
    try:
        desc_val = int(re.search(r'\d+', p.get('desconto', '0')).group())
        if desc_val >= 40: score += 45
        elif desc_val >= 20: score += 25
        
        nota = float(str(p.get('nota', '0')).replace(',', '.'))
        if nota >= 4.5: score += 25
        elif nota < 4.0: score -= 50
        
        if int(p.get('avaliacoes', 0)) > 100: score += 20
    except: pass
    return score

def gerar_copy(p: dict, plataforma: str) -> str:
    preco_atual = float(p['preco'].replace('.', '').replace(',', '.'))
    
    copy = f"💥 **PROMOÇÃO VERIFICADA!**\n\n"
    copy += f"🔥 **{p['titulo']}**\n"
    copy += f"⭐ {p['nota']} ({p['avaliacoes']}+ avaliações)\n\n"
    
    if p.get('preco_antigo'):
        preco_velho = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
        economia = preco_velho - preco_atual
        if economia > 1:
            copy += f"💰 ~~R$ {p['preco_antigo']}~~\n"
            copy += f"✅ **POR: R$ {p['preco']}**\n"
            copy += f"📉 **ECONOMIA DE R$ {economia:.2f}**\n\n"
    else:
        copy += f"✅ **OFERTA: R$ {p['preco']}**\n\n"

    copy += f"💳 {p['parcelas']}\n"
    copy += f"⚠️ *O estoque pode acabar logo!*\n\n"
    
    # MASCARAMENTO DE LINK (Segurança e Estética)
    if plataforma == "ML":
        url_visivel = "https://www.mercadolivre.com.br/oferta-exclusiva"
    else:
        url_visivel = "https://www.amazon.com.br/oferta-exclusiva"
        
    copy += f"🔗 **COMPRE NO SITE OFICIAL:**\n[{url_visivel}]({p['link']})\n\n"
    copy += f"➡️ #Oferta #Promoção"
    return copy

async def processar_plataforma(nome: str, produtos: list[dict]):
    for p in produtos:
        if p.get('status') == "duplicado": continue
        if calcular_score(p) < 60: continue

        try:
            caption = gerar_copy(p, nome)
            if p.get("imagem"):
                r = requests.get(p["imagem"], timeout=10)
                if r.status_code == 200:
                    foto = io.BytesIO(r.content)
                    foto.name = 'post.jpg'
                    await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
            
            marcar_enviado(p["id"])
            await asyncio.sleep(20)
        except Exception as e: print(f"Erro: {e}")

async def loop_principal():
    await client.start()
    while True:
        await processar_plataforma("ML", buscar_mercado_livre())
        await asyncio.sleep(30)
        await processar_plataforma("AMZ", buscar_amazon())
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

async def start_everything():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await loop_principal()

if __name__ == "__main__":
    asyncio.run(start_everything())