import asyncio
import threading
import os
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL, LOG_CANAL
from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    if not produtos:
        await enviar_log(f"❌ **FALHA DE CAPTURA: {nome}**\nVerifique bloqueio de IP.")
        return

    novos = [p for p in produtos if p.get('status') == "novo"]
    duplicados = [p for p in produtos if p.get('status') == "duplicado"]

    relatorio = (f"📊 **RELATÓRIO: {nome}**\n"
                 f"Contexto: {'🧪 TESTE' if modo_teste else '📡 AUTO'}\n"
                 f"📦 Total: {len(produtos)} | ✅ Novos: {len(novos)}\n")
    
    if novos:
        relatorio += "\n📝 **Preview:**\n" + "\n".join([f"- {p['titulo'][:30]}" for p in novos[:3]])
    
    await enviar_log(relatorio)

    if not modo_teste:
        for p in novos:
            try:
                msg = f"🔥 **OFERTA {nome}**\n\n🛍 {p['titulo']}\n💰 **R$ {p['preco']}**\n"
                if p.get("tem_pix"): msg += "⚡️ Pix disponível!\n"
                msg += f"\n🔗 **Link:** {p['link']}"
                
                await client.send_message(MEU_CANAL, msg)
                marcar_enviado(p["id"])
                await asyncio.sleep(5)
            except Exception as e:
                await enviar_log(f"⚠️ Erro item {p['id']}: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 Iniciando varredura de teste...")
    await executar_ciclo(modo_teste=True)

async def executar_ciclo(modo_teste: bool = False):
    await processar_plataforma("AMAZON", buscar_amazon(), modo_teste)
    await processar_plataforma("MERCADO LIVRE", buscar_mercado_livre(), modo_teste)

async def main():
    await client.start()
    await enviar_log("✅ **Bot Online e Operacional!**")
    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            await enviar_log(f"🚨 Erro loop: {e}")
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route("/")
def home(): return "Bot Running"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.run(main())