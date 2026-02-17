import asyncio, io, requests, os, threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def formatar_post(p: dict) -> str:
    try:
        atual_num = float(p['preco'].replace('.', '').replace(',', '.'))
        if p['preco_antigo']:
            antigo_num = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
            economia = antigo_num - atual_num
            porcentagem = int((1 - (atual_num / antigo_num)) * 100)
            
            precos = f"💰 ~~R$ {p['preco_antigo']}~~\n"
            precos += f"✅ **POR APENAS: R$ {p['preco']}**\n"
            precos += f"📉 **VOCÊ ECONOMIZA: R$ {economia:.2f} ({porcentagem}% OFF)**"
        else:
            precos = f"✅ **POR APENAS: R$ {p['preco']}**"
    except:
        precos = f"✅ **POR APENAS: R$ {p['preco']}**"

    copy = f"**{p['titulo']}**\n"
    copy += f"⭐ {p['nota']} ({p['avaliacoes']}+ avaliações)\n\n"
    copy += f"{precos}\n\n"
    copy += f"🏪 Vendido por: {p['loja']}\n"
    copy += f"🚀 Envio rápido garantido\n"
    copy += f"⚠️ Estoque limitado, pode subir a qualquer momento!\n\n"
    copy += f"🔗 **APROVEITAR OFERTA:**\n"
    copy += f"{p['link']}\n\n"
    copy += f"➡️ #Ofertas #MercadoLivre"
    return copy

async def tarefa_principal():
    await client.start()
    while True:
        produtos = buscar_mercado_livre()
        for p in produtos:
            try:
                caption = formatar_post(p)
                if p["imagem"]:
                    r = requests.get(p["imagem"], timeout=15)
                    foto = io.BytesIO(r.content)
                    foto.name = 'produto.jpg'
                    await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
                    await asyncio.sleep(20)
            except Exception as e:
                print(f"Erro ao postar: {e}")
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

async def start():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await tarefa_principal()

if __name__ == "__main__":
    asyncio.run(start())