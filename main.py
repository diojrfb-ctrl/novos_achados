import asyncio, io, requests, os, threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def formatar_copy(p: dict) -> str:
    # Lógica de Preço
    try:
        atual_val = p['preco'].replace('.', '').replace(',', '.')
        atual_num = float(atual_val)
        if p['preco_antigo']:
            antigo_val = p['preco_antigo'].replace('.', '').replace(',', '.')
            antigo_num = float(antigo_val)
            economia = antigo_num - atual_num
            porcentagem = int((1 - (atual_num / antigo_num)) * 100)
            
            bloco_preco = f"💰 R$ {p['preco_antigo']}\n"
            bloco_preco += f"✅ **POR APENAS: R$ {p['preco']}**\n"
            bloco_preco += f"📉 **VOCÊ ECONOMIZA: R$ {economia:.2f} ({porcentagem}% OFF)**"
        else:
            bloco_preco = f"✅ **POR APENAS: R$ {p['preco']}**"
    except:
        bloco_preco = f"✅ **POR APENAS: R$ {p['preco']}**"

    # Construção da Curadoria
    copy = f"**{p['titulo']}**\n"
    copy += f"⭐ {p['nota']} ({p['avaliacoes']}+ avaliações)\n\n"
    copy += f"{bloco_preco}\n\n"
    copy += f"🏪 Vendido por: {p['loja']}\n"
    copy += f"🚀 Envio rápido garantido\n"
    copy += f"⚠️ Estoque limitado, pode subir a qualquer momento!\n\n"
    copy += f"🔗 **APROVEITAR OFERTA:**\n"
    copy += f"{p['link']}\n\n"
    copy += f"➡️ #Ofertas #MercadoLivre"
    
    return copy

async def processar():
    await client.start()
    produtos = buscar_mercado_livre()
    for p in produtos:
        try:
            caption = formatar_copy(p)
            if p["imagem"]:
                r = requests.get(p["imagem"], timeout=10)
                foto = io.BytesIO(r.content)
                foto.name = 'produto.jpg'
                await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
                await asyncio.sleep(20)
        except Exception as e:
            print(f"Erro: {e}")

app = Flask(__name__)
@app.route('/')
def h(): return "OK", 200

async def main():
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    await processar()

if __name__ == "__main__":
    asyncio.run(main())