import asyncio, io, requests, os, threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def formatar_copy(p: dict) -> str:
    # Cálculos de Economia
    try:
        atual_num = float(p['preco'].replace('.', '').replace(',', '.'))
        if p['preco_antigo']:
            antigo_num = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
            economia = antigo_num - atual_num
            porcentagem = int((1 - (atual_num / antigo_num)) * 100)
            
            linha_preco = f"💰 ~~R$ {p['preco_antigo']}~~\n"
            linha_preco += f"✅ **POR APENAS: R$ {p['preco']}**\n"
            linha_preco += f"📉 **VOCÊ ECONOMIZA: R$ {economia:.2f} ({porcentagem}% OFF)**"
        else:
            linha_preco = f"✅ **POR APENAS: R$ {p['preco']}**"
    except:
        linha_preco = f"✅ **POR APENAS: R$ {p['preco']}**"

    # Construção do Post (Foco em Escaneabilidade)
    copy = f"**{p['titulo']}**\n"
    copy += f"⭐ {p['nota']} ({p['avaliacoes']}+ avaliações)\n\n"
    copy += f"{linha_preco}\n\n"
    copy += f"🏪 Vendido por: {p['loja']}\n"
    copy += f"🚀 Envio rápido garantido\n"
    copy += f"⚠️ Estoque limitado, pode subir a qualquer momento!\n\n"
    copy += f"🔗 **APROVEITAR OFERTA:**\n"
    copy += f"{p['link']}\n\n" # Link exposto e reduzido
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
                await asyncio.sleep(20) # Intervalo de segurança
        except Exception as e:
            print(f"Erro: {e}")

# Servidor para o Render
app = Flask(__name__)
@app.route('/')
def h(): return "Bot Online", 200

async def main():
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    await processar()

if __name__ == "__main__":
    asyncio.run(main())