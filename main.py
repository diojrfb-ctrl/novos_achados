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
    """
    Processa a lista de produtos capturados, gera relatórios técnicos detalhados 
    no canal de logs e gerencia a postagem no canal de ofertas.
    """
    
    # 1. LOG DE DIAGNÓSTICO INICIAL
    if not produtos:
        # Se a lista está vazia, o problema é na raspagem (HTML/Bloqueio)
        msg_erro = (
            f"❌ **FALHA DE CAPTURA: {nome}**\n\n"
            f"**Status:** Nenhum dado extraído.\n"
            f"**Possíveis Causas:**\n"
            f"1. IP do Render bloqueado pelo WAF (403 Forbidden).\n"
            f"2. O site exibiu um Captcha em vez da lista de produtos.\n"
            f"3. Os Seletores CSS (BeautifulSoup) estão desatualizados.\n"
            f"**Sugestão:** Verifique os logs do console no Render para ver o Status Code."
        )
        await enviar_log(msg_erro)
        return

    # 2. SEPARAÇÃO DE DADOS (NOVOS VS DUPLICADOS)
    # Filtramos baseado no campo 'status' que as funções de busca preenchem
    novos = [p for p in produtos if p.get('status') == "novo"]
    duplicados = [p for p in produtos if p.get('status') == "duplicado"]

    # 3. CONSTRUÇÃO DO RELATÓRIO DETALHADO PARA O CANAL DE LOGS
    tipo_operacao = "🧪 MODO TESTE" if modo_teste else "📡 VARREDURA AUTOMÁTICA"
    
    relatorio = f"📊 **RELATÓRIO TÉCNICO: {nome}**\n"
    relatorio += f"**Contexto:** {tipo_operacao}\n"
    relatorio += f"────────────────────\n"
    relatorio += f"📦 **Total Analisado:** {len(produtos)} itens\n"
    relatorio += f"✅ **Aptos para Postar:** {len(novos)}\n"
    relatorio += f"♻️ **Já Enviados (Redis):** {len(duplicados)}\n\n"

    if novos:
        relatorio += "📝 **Preview dos itens capturados:**\n"
        for idx, p in enumerate(novos[:5], 1): # Mostra os 5 primeiros para não inundar o log
            pix = "⚡️[PIX]" if p.get('tem_pix') else ""
            relatorio += f"{idx}. {p['titulo'][:35]}... | R$ {p['preco']} {pix}\n"
    else:
        relatorio += "ℹ️ *Nenhuma oferta nova encontrada nesta rodada.*\n"

    # Envia o relatório detalhado ao canal de logs
    await enviar_log(relatorio)

    # 4. LÓGICA DE POSTAGEM (PULA SE FOR MODO TESTE)
    if modo_teste:
        await enviar_log(f"ℹ️ **{nome}**: Simulação finalizada. Nada foi enviado ao canal principal.")
        return

    # Se não for teste, percorre a lista de novos e envia ao canal principal
    for p in novos:
        try:
            # Montagem da mensagem formatada para o usuário final
            msg_canal = f"🔥 **OFERTA {nome}**\n\n"
            msg_canal += f"🛍 {p['titulo']}\n"
            msg_canal += f"💰 **R$ {p['preco']}**\n\n"
            
            # Adição de selos de destaque
            if p.get("tem_pix"):
                msg_canal += "⚡️ Desconto especial no Pix!\n"
            if p.get("tem_cupom"):
                msg_canal += "🎟 Verifique o cupom na página!\n"
            if p.get("mais_vendido"):
                msg_canal += "🏆 Destaque: Um dos mais vendidos!\n"

            msg_canal += f"\n🔗 **Compre aqui:**\n{p['link']}"

            # Envio para o Canal Principal
            await client.send_message(MEU_CANAL, msg_canal)
            
            # Salva no Redis para nunca repetir este ID
            marcar_enviado(p["id"])
            
            # Log de sucesso individual
            print(f"[OK] Postado: {p['id']}")
            
            # Anti-Spam: espera 5 segundos entre uma oferta e outra
            await asyncio.sleep(5)

        except Exception as e:
            await enviar_log(f"⚠️ **ERRO AO POSTAR ITEM:**\nID: {p.get('id')}\nErro: {str(e)}")
            
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