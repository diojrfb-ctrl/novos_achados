import asyncio, threading, os, io, requests, re
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def gerar_copy(p: dict, plataforma: str) -> str:
    # Preparação dos valores para cálculo
    preco_atual_num = float(p['preco'].replace('.', '').replace(',', '.'))
    
    copy = f"💥 **OPORTUNIDADE DE OURO DETECTADA!**\n\n"
    copy += f"🔥 **{p['titulo']}**\n"
    copy += f"⭐ {p['nota']} ({p['avaliacoes']}+ avaliações)\n\n"
    
    if p.get('preco_antigo'):
        try:
            # Limpa o preço antigo para garantir que o float funcione
            antigo_limpo = re.sub(r'[^\d,]', '', p['preco_antigo']).replace(',', '.')
            preco_velho_num = float(antigo_limpo)
            economia = preco_velho_num - preco_atual_num
            
            if economia > 1:
                copy += f"💰 **R$ {int(preco_velho_num)}**\n"
                copy += f"✅ **POR APENAS: R$ {p['preco']}**\n"
                copy += f"📉 **VOCÊ ECONOMIZA: R$ {economia:.2f}** ({p['desconto']})\n\n"
            else:
                copy += f"✅ **POR APENAS: R$ {p['preco']}**\n\n"
        except:
            copy += f"✅ **POR APENAS: R$ {p['preco']}**\n\n"
    else:
        copy += f"✅ **POR APENAS: R$ {p['preco']}**\n\n"

    copy += f"💳 {p.get('parcelas', 'Confira no site')}\n"
    
    if plataforma == "AMZ":
        copy += f"🚚 *Frete GRÁTIS para membros Prime*\n"
    else:
        copy += f"🚀 *Envio rápido garantido*\n"
        
    copy += f"⚠️ *Estoque limitado, pode subir a qualquer momento!* \n\n"
    
    # Mascaramento de Link Seguro
    site_url = "https://www.mercadolivre.com.br/oferta-exclusiva" if plataforma == "ML" else "https://www.amazon.com.br/oferta-exclusiva"
    
    copy += f"🔗 **COMPRE NO SITE OFICIAL:**\n[{site_url}]({p['link']})\n\n"
    copy += f"➡️ #Ofertas #OfertaVerificada"
    return copy

async def processar_plataforma(nome: str, produtos: list[dict]):
    for p in produtos:
        if p.get('status') == "duplicado": continue
        
        # Filtro de Score (Mínimo 60)
        # (Sua função calcular_score deve estar aqui)

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
        try:
            await processar_plataforma("ML", buscar_mercado_livre())
            await asyncio.sleep(30)
            await processar_plataforma("AMZ", buscar_amazon())
        except: pass
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