import asyncio
import threading
import os
from flask import Flask

# Correção da importação para evitar o ImportError no Python 3.14
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import (
    API_ID, API_HASH, STRING_SESSION, MEU_CANAL, LOG_CANAL
)

from redis_client import marcar_enviado
from amazon import buscar_amazon
from mercado_livre import buscar_mercado_livre

# =========================
# CONFIGURAÇÃO DO CLIENTE
# =========================

client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH
)

# =========================
# FUNÇÕES DE AUXÍLIO
# =========================

async def enviar_log(texto: str):
    """Envia mensagens detalhadas para o canal de logs."""
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro ao enviar log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    """Processa a lista de produtos, gera relatório de log e posta se necessário."""
    
    if not produtos:
        await enviar_log(f"❌ **{nome}**: Nenhum produto encontrado. Seletores podem estar desatualizados ou o site bloqueou o acesso.")
        return

    novos = [p for p in produtos if p.get('status') == "novo"]
    duplicados = [p for p in produtos if p.get('status') == "duplicado"]

    # --- Relatório Detalhado de Logs ---
    status_label = "🧪 TESTE" if modo_teste else "📡 VARREDURA"
    relatorio = f"🔍 **{status_label} - {nome}**\n"
    relatorio += f"📦 Analisados na página: {len(produtos)}\n"
    relatorio += f"✅ Novos encontrados: {len(novos)}\n"
    relatorio += f"♻️ Ignorados (já postados): {len(duplicados)}\n\n"
    
    if novos:
        relatorio += "**Prontos para postagem:**\n"
        for idx, p in enumerate(novos[:5], 1): # Mostra os 5 primeiros no log
            pix_info = "⚡️ [Pix]" if p.get('tem_pix') else ""
            relatorio += f"{idx}. {p['titulo'][:35]}... - R$ {p['preco']} {pix_info}\n"
    
    await enviar_log(relatorio)

    # Se estiver em modo teste, não envia para o canal principal
    if modo_teste:
        return

    # --- Postagem no Canal de Ofertas ---
    for p in novos:
        try:
            msg = f"🔥 OFERTA {nome}\n\n"
            msg += f"🛍 {p['titulo']}\n"
            msg += f"💰 R$ {p['preco']}\n"
            
            # Vantagens Dinâmicas
            if p.get("tem_pix"):
                msg += "⚡️ Economize pagando no Pix!\n"
            if p.get("tem_cupom"):
                msg += "🎟 Tem cupom disponível na página!\n"
            if p.get("mais_vendido"):
                msg += "🏆 Um dos mais vendidos da categoria\n"

            msg += f"\n🔗 Comprar:\n{p['link']}"

            await client.send_message(MEU_CANAL, msg)
            marcar_enviado(p["id"])
            
            # Delay anti-spam
            await asyncio.sleep(5)
        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar item {p['id']}: {e}")

# =========================
# COMANDO DE TESTE MANUAL
# =========================

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    """Responde ao comando /testar no Telegram."""
    await event.reply("🧪 Iniciando varredura de teste... Verifique o canal de logs.")
    await executar_ciclo(modo_teste=True)

# =========================
# LÓGICA DE CICLO
# =========================

async def executar_ciclo(modo_teste: bool = False):
    """Executa a busca nas duas plataformas."""
    # Amazon
    produtos_amz = buscar_amazon()
    await processar_plataforma("AMAZON", produtos_amz, modo_teste)
    
    # Mercado Livre
    produtos_ml = buscar_mercado_livre()
    await processar_plataforma("MERCADO LIVRE", produtos_ml, modo_teste)

async def bot_loop():
    """Loop principal que roda a cada 1 hora."""
    await client.start()
    await enviar_log("✅ **Bot Online e Operacional!**\nUse `/testar` para validar agora.")

    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            await enviar_log(f"🚨 **ERRO CRÍTICO NO LOOP:**\n{e}")
        
        await asyncio.sleep(3600)

# =========================
# SERVIDOR FLASK (RENDER)
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot de ofertas rodando com sucesso!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# INICIALIZAÇÃO
# =========================

if __name__ == "__main__":
    # Flask em thread separada
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Execução do Telethon
    client.loop.run_until_complete(bot_loop())