import asyncio
import io
import requests
import os
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Módulos locais
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, CANAL_TESTE, LOG_CANAL
from redis_client import marcar_enviado, ja_enviado
from mercado_livre import buscar_mercado_livre
from amazon import buscar_amazon
from shopee import buscar_shopee
from formatters import formatar_copy_otimizada
from seguranca import eh_produto_seguro

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def enviar_log(mensagem: str):
    """Envia avisos para o @meusachadinhoslog."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        if LOG_CANAL:
            await client.send_message(LOG_CANAL, f"📝 **LOG [{timestamp}]**\n{mensagem}")
    except: pass

COMPONENTES = {
    "ml": {"busca": buscar_mercado_livre, "simplificado": False},
    "amazon": {"busca": buscar_amazon, "simplificado": True},
    "shopee": {"busca": buscar_shopee, "simplificado": True},
}

async def enviar_para_telegram(p: dict, destino: str, simplificado: bool):
    try:
        caption = formatar_copy_otimizada(p, simplificado=simplificado)
        if p.get("imagem"):
            r = requests.get(p["imagem"], timeout=15)
            foto = io.BytesIO(r.content)
            foto.name = 'post.jpg'
            await client.send_file(destino, foto, caption=caption)
        else:
            await client.send_message(destino, caption)
        return True
    except Exception as e:
        await enviar_log(f"❌ Erro envio: {e}")
        return False

@client.on(events.NewMessage(pattern=r'/testar(?:\s+(\w+))?'))
async def handler_teste(event):
    site_key = event.pattern_match.group(1).lower() if event.pattern_match.group(1) else ""
    if site_key not in COMPONENTES:
        await event.reply(f"❌ Use /testar ml, amazon ou shopee")
        return

    await event.reply(f"🔍 Testando {site_key.upper()}...")
    produtos = COMPONENTES[site_key]["busca"](limite=1)
    
    if not produtos:
        await event.reply("⚠️ Nada retornado pelo scraper.")
        return

    p = produtos[0]
    # O comando de teste também respeita a segurança
    if not eh_produto_seguro(p['titulo']):
        await event.reply("🚫 Item de teste bloqueado pelo filtro adulto.")
        return

    await enviar_para_telegram(p, CANAL_TESTE, COMPONENTES[site_key]["simplificado"])
    await event.reply("✅ Enviado para o canal de teste!")

async def loop_bot():
    await client.start()
    await enviar_log("🚀 **Bot Online!** ML, Amazon e Shopee monitorados.")

    while True:
        for nome_site, config in COMPONENTES.items():
            try:
                produtos = config["busca"]()
                for p in produtos:
                    # FILTRO DE SEGURANÇA
                    if not eh_produto_seguro(p['titulo']):
                        continue

                    if ja_enviado(p["id"]):
                        continue

                    if await enviar_para_telegram(p, MEU_CANAL, config["simplificado"]):
                        marcar_enviado(p["id"])
                        await asyncio.sleep(30) 

            except Exception as e:
                await enviar_log(f"⚠️ Erro no ciclo {nome_site}: {e}")

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