import asyncio
import threading
import os
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import (
    API_ID, API_HASH, STRING_SESSION, MEU_CANAL, LOG_CANAL
)

from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

# Configuração do Cliente
client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH
)

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro ao enviar log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    if not produtos:
        msg_erro = (
            f"❌ **FALHA DE CAPTURA: {nome}**\n\n"
            f"**Status:** Nenhum dado extraído.\n"
            f"**Sugestão:** O IP do Render pode estar bloqueado ou os seletores mudaram."
        )
        await enviar_log(msg_erro)
        return

    novos = [p for p in produtos if p.get('status') == "novo"]
    duplicados = [p for p in produtos if p.get('status') == "duplicado"]

    tipo_operacao = "🧪 MODO TESTE" if modo_teste else "📡 VARREDURA AUTOMÁTICA"
    relatorio = f"📊 **RELATÓRIO TÉCNICO: {nome}**\n"
    relatorio += f"**Contexto:** {tipo_operacao}\n"
    relatorio += f"────────────────────\n"
    relatorio += f"📦 **Total Analisado:** {len(produtos)}\n"
    relatorio += f"✅ **Novos:** {len(novos)}\n"
    relatorio += f"♻️ **Duplicados:** {len(duplicados)}\n\n"

    if novos:
        relatorio += "📝 **Preview:**\n"
        for idx, p in enumerate(novos[:3], 1):
            relatorio += f"{idx}. {p['titulo'][:30]}... - R$ {p['preco']}\n"
    
    await enviar_log(relatorio)

    if modo_teste: return

    for p in novos:
        try:
            msg_canal = f"🔥 **OFERTA {nome}**\n\n"
            msg_canal += f"🛍 {p['titulo']}\n"
            msg_canal += f"💰 **R$ {p['preco']}**\n\n"
            if p.get("tem_pix"): msg_canal += "⚡️ Desconto no Pix!\n"
            msg_canal += f"🔗 **Compre aqui:**\n{p['link']}"

            await client.send_message(MEU_CANAL, msg_canal)
            marcar_enviado(p["id"])
            await asyncio.sleep(5) # Anti-flood
        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar {p['id']}: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 Iniciando testes...")
    await executar_ciclo(modo_teste=True)

async def executar_ciclo(modo_teste: bool = False):
    # Processa Amazon
    p_amz = buscar_amazon()
    await processar_plataforma("AMAZON", p_amz, modo_teste)
    
    # Processa Mercado Livre
    p_ml = buscar_mercado_livre()
    await processar_plataforma("MERCADO LIVRE", p_ml, modo_teste)

async def main():
    await client.start()
    await enviar_log("✅ **Bot Online!**")
    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            print(f"Erro no loop: {e}")
        await asyncio.sleep(3600) # 1 hora

# Flask para o Render não matar o processo
app = Flask(__name__)
@app.route("/")
def home(): return "Bot Ativo"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    asyncio.run(main())