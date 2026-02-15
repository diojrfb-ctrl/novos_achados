import asyncio
import threading
import os
from flask import Flask

# Importações corrigidas para Telethon
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

# Criamos o objeto client fora para que os decorators (@client.on) funcionem
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
        await enviar_log(f"❌ **{nome}**: Nenhum produto encontrado. Verifique os seletores.")
        return

    novos = [p for p in produtos if p.get('status') == "novo"]
    duplicados = [p for p in produtos if p.get('status') == "duplicado"]

    # --- Relatório Detalhado de Logs ---
    status_label = "🧪 TESTE" if modo_teste else "📡 VARREDURA"
    relatorio = f"🔍 **{status_label} - {nome}**\n"
    relatorio += f"📦 Analisados: {len(produtos)} | ✅ Novos: {len(novos)} | ♻️ Repetidos: {len(duplicados)}\n\n"
    
    if novos:
        relatorio += "**Top encontrados:**\n"
        for idx, p in enumerate(novos[:3], 1):
            relatorio += f"{idx}. {p['titulo'][:30]}... - R$ {p['preco']}\n"
    
    await enviar_log(relatorio)

    if modo_teste:
        return

    # --- Postagem no Canal ---
    for p in novos:
        try:
            msg = f"🔥 OFERTA {nome}\n\n"
            msg += f"🛍 {p['titulo']}\n"
            msg += f"💰 R$ {p['preco']}\n"
            
            if p.get("tem_pix"): msg += "⚡️ Economize pagando no Pix!\n"
            if p.get("tem_cupom"): msg += "🎟 Tem cupom na página!\n"
            if p.get("mais_vendido"): msg += "🏆 Destaque: Mais Vendido\n"

            msg += f"\n🔗 Comprar:\n{p['link']}"

            await client.send_message(MEU_CANAL, msg)
            marcar_enviado(p["id"])
            await asyncio.sleep(5)
        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar item {p['id']}: {e}")

# =========================
# COMANDO DE TESTE MANUAL
# =========================

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 Teste iniciado! Olhe o canal de logs.")
    await executar_ciclo(modo_teste=True)

# =========================
# LÓGICA DE CICLO
# =========================

async def executar_ciclo(modo_teste: bool = False):
    produtos_amz = buscar_amazon()
    await processar_plataforma("AMAZON", produtos_amz, modo_teste)
    
    produtos_ml = buscar_mercado_livre()
    await processar_plataforma("MERCADO LIVRE", produtos_ml, modo_teste)

async def main():
    """Função principal que gerencia o loop assíncrono."""
    # Inicia o cliente Telethon corretamente
    await client.start()
    await enviar_log("✅ **Bot Online e Operacional!**\nUse `/testar` para validar.")

    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            await enviar_log(f"🚨 **ERRO CRÍTICO NO LOOP:**\n{e}")
        
        # Dorme por 1 hora
        await asyncio.sleep(3600)

# =========================
# SERVIDOR FLASK (RENDER)
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot de ofertas rodando!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# INICIALIZAÇÃO FINAL
# =========================

if __name__ == "__main__":
    # Inicia o Flask em uma thread separada (daemon para fechar com o processo pai)
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    # Inicia o asyncio da maneira correta para Python 3.14
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass