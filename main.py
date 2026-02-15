import asyncio
import threading
import os
from flask import Flask
from telethon import TelegramClient, events, StringSession

from config import (
    API_ID, API_HASH, STRING_SESSION, MEU_CANAL, LOG_CANAL
)

from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

# Inicialização do Cliente
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro ao enviar log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    if not produtos:
        msg = f"❌ **{nome}**: Nenhum produto capturado. Seletores podem estar desatualizados ou houve bloqueio (403/503)."
        await enviar_log(msg)
        return

    novos = [p for p in produtos if p['status'] == "novo"]
    duplicados = [p for p in produtos if p['status'] == "duplicado"]

    # Relatório Detalhado
    relatorio = f"🔍 **RELATÓRIO {nome}** {'(MODO TESTE)' if modo_teste else ''}\n"
    relatorio += f"📦 Total na página: {len(produtos)}\n"
    relatorio += f"✅ Aptos para postar: {len(novos)}\n"
    relatorio += f"♻️ Já postados: {len(duplicados)}\n\n"
    
    if novos:
        relatorio += "**Top 3 encontrados:**\n"
        for p in novos[:3]:
            pix_str = " (PIX ⚡️)" if p.get('tem_pix') else ""
            relatorio += f"• {p['titulo'][:40]}... - R$ {p['preco']}{pix_str}\n"
    
    await enviar_log(relatorio)

    # Se for apenas teste, não posta no canal principal, apenas avisa
    if modo_teste:
        await enviar_log(f"ℹ️ **{nome}**: Simulação concluída. Nada foi postado no canal principal.")
        return

    # Postagem real
    for p in novos:
        try:
            msg = f"🔥 OFERTA {nome}\n\n"
            msg += f"🛍 {p['titulo']}\n"
            msg += f"💰 R$ {p['preco']}\n"
            if p.get("tem_pix"): msg += "⚡️ Desconto especial no Pix!\n"
            if p.get("tem_cupom"): msg += "🎟 Verifique o cupom na página!\n"
            msg += f"\n🔗 Comprar:\n{p['link']}"

            await client.send_message(MEU_CANAL, msg)
            marcar_enviado(p["id"])
            await asyncio.sleep(5) 
        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar {p['id']}: {e}")

async def executar_ciclo(modo_teste: bool = False):
    status = "🧪 TESTE MANUAL" if modo_teste else "🚀 CICLO AUTOMÁTICO"
    await enviar_log(f"**{status} INICIADO**")
    
    amz = buscar_amazon()
    await processar_plataforma("AMAZON", amz, modo_teste)
    
    ml = buscar_mercado_livre()
    await processar_plataforma("MERCADO LIVRE", ml, modo_teste)
    
    await enviar_log(f"**{status} FINALIZADO**")

# COMANDO DE TESTE: Envie /testar no canal de logs ou privado do bot
@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("Recebido! Iniciando varredura de teste agora...")
    await executar_ciclo(modo_teste=True)

async def bot_loop():
    await client.start()
    await enviar_log("✅ **Bot Online!**\nEnvie `/testar` para validar os seletores agora.")
    
    # Mantém o ouvinte de comandos rodando em paralelo com o loop de tempo
    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            await enviar_log(f"🚨 **Erro Crítico:** {e}")
        await asyncio.sleep(3600)

# FLASK
app = Flask(__name__)
@app.route("/")
def home(): return "Bot Ativo"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    client.loop.run_until_complete(bot_loop())