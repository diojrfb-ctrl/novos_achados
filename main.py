import asyncio, io, requests, os, threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre
from redis_client import marcar_enviado

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def formatar_copy_limpa(p: dict) -> str:
    try:
        # Cálculos de Preço e Desconto
        atual_num = float(p['preco'].replace('.', '').replace(',', '.'))
        precos_formatados = ""
        desconto_pix = ""
        
        if p['preco_antigo']:
            antigo_num = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
            porcentagem = int((1 - (atual_num / antigo_num)) * 100)
            precos_formatados += f"💰 De: ~~R$ {p['preco_antigo']}~~\n"
            desconto_pix = f"📉 ({porcentagem}% de desconto no Pix)\n"
        
        precos_formatados += f"✅ **POR: R$ {p['preco']}**"

        # Montagem da Copy conforme seu modelo
        copy = f"**{p['titulo']}**\n"
        copy += f"⭐ {p['nota']} ({p['avaliacoes']} opiniões)\n"
        copy += f"{precos_formatados}\n"
        copy += f"{desconto_pix}"
        copy += f"💳 {p['parcelas']}\n"
        copy += f"📦 Frete: {p['frete']}\n"
        copy += f"🔥 Estoque: {p['estoque']}\n\n"
        copy += f"🔗 **LINK DA OFERTA:**\n"
        copy += f"{p['link']}\n\n"
        copy += f"➡️ #Ofertas #MercadoLivre"
        return copy
    except Exception as e:
        print(f"Erro na formatação: {e}")
        return f"**{p['titulo']}**\n\n✅ POR: R$ {p['preco']}\n\n🔗 {p['link']}"

async def loop_bot():
    await client.start()
    while True:
        produtos = buscar_mercado_livre()
        for p in produtos:
            try:
                caption = formatar_copy_limpa(p)
                if p["imagem"]:
                    r = requests.get(p["imagem"], timeout=10)
                    foto = io.BytesIO(r.content)
                    foto.name = 'post.jpg'
                    await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
                    marcar_enviado(p["id"])
                    await asyncio.sleep(25)
            except Exception as e:
                print(f"Erro: {e}")
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

async def main():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await loop_bot()

if __name__ == "__main__":
    asyncio.run(main())