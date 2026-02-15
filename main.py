import asyncio
import threading
import os
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import (
    API_ID, API_HASH, STRING_SESSION, MEU_CANAL, LOG_CANAL
)

from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict]):
    if not produtos:
        await enviar_log(f"❌ **{nome}**: Nenhum produto encontrado na página.")
        return

    novos = [p for p in produtos if p['status'] == "novo"]
    duplicados = [p for p in produtos if p['status'] == "duplicado"]

    # Relatório detalhado para o Canal de Logs
    relatorio = f"🔍 **VARREDURA {nome}**\n"
    relatorio += f"📦 Total analisado: {len(produtos)}\n"
    relatorio += f"✅ Novos para postar: {len(novos)}\n"
    relatorio += f"♻️ Ignorados (já postados): {len(duplicados)}\n\n"
    
    if novos:
        relatorio += "**Lista de entrada:**\n"
        for idx, p in enumerate(novos, 1):
            relatorio += f"{idx}. {p['titulo'][:30]}... - R$ {p['preco']}\n"
    
    await enviar_log(relatorio)

    # Postagem real no canal principal
    for p in novos:
        try:
            msg = f"🔥 OFERTA {nome}\n\n"
            msg += f"🛍 {p['titulo']}\n"
            msg += f"💰 R$ {p['preco']}\n"
            
            if p.get("tem_pix"):
                msg += "⚡️ Desconto no Pix disponível!\n"
            if p.get("tem_cupom"):
                msg += "🎟 Tem cupom na página!\n"
            if p.get("mais_vendido"):
                msg += "🏆 Destaque: Mais Vendido\n"

            msg += f"\n🔗 Comprar:\n{p['link']}"

            await client.send_message(MEU_CANAL, msg)
            marcar_enviado(p["id"])
            await asyncio.sleep(5) # Evitar flood
        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar item {p['id']}: {e}")

async def enviar_ofertas():
    await enviar_log("🚀 **Iniciando ciclo de busca...**")
    
    # Processa Amazon
    produtos_amz = buscar_amazon()
    await processar_plataforma("AMAZON", produtos_amz)
    
    # Processa Mercado Livre
    produtos_ml = buscar_mercado_livre()
    await processar_plataforma("MERCADO LIVRE", produtos_ml)
    
    await enviar_log("🏁 **Ciclo finalizado. Próximo em 1 hora.**")

async def bot_loop():
    await client.start()
    await enviar_log("✅ **Bot Online e Monitorando!**")
    while True:
        try:
            await enviar_ofertas()
        except Exception as e:
            await enviar_log(f"🚨 **ERRO CRÍTICO NO LOOP:**\n{e}")
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route("/")
def home(): return "Bot Ativo"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(bot_loop())