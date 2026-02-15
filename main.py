import asyncio
import threading
import os
import io
import requests
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Importações de configuração e scrapers
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
# LÓGICA DE CATEGORIAS (TAGS)
# =========================
def definir_tag(titulo: str) -> str:
    """Define a hashtag baseada em palavras-chave no título."""
    t = titulo.lower()
    if any(x in t for x in ["tv", "televisao", "smart tv", "led", "monitor"]): return "Eletrónicos"
    if any(x in t for x in ["iphone", "samsung galaxy", "celular", "xiaomi", "motorola", "smartphone"]): return "Smartphone"
    if any(x in t for x in ["piscina", "cozinha", "casa", "penteadeira", "fritadeira", "air fryer", "limpeza"]): return "Casa"
    if any(x in t for x in ["carro", "pneu", "automotivo", "moto", "capacete"]): return "Veículos"
    if any(x in t for x in ["gamer", "ps5", "nintendo", "xbox", "pc gamer", "mouse gamer", "teclado"]): return "Gamer"
    if any(x in t for x in ["fone", "relógio", "smartwatch", "carregador", "caixa de som"]): return "Acessórios"
    return "Ofertas"

# =========================
# FUNÇÕES DE AUXÍLIO
# =========================
async def enviar_log(texto: str):
    """Envia logs técnicos para o canal de monitorização."""
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro ao enviar log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    """
    Processa os produtos, baixa a imagem e envia para o Telegram
    com formatação detalhada e hashtags.
    """
    novos = [p for p in produtos if p.get('status') == "novo"]
    
    await enviar_log(f"📊 **RELATÓRIO {nome}:** {len(novos)} novos itens identificados.")

    for p in novos:
        try:
            tag = definir_tag(p['titulo'])
            
            # Montagem da Legenda Detalhada
            # Inclui Prova Social (Avaliação e Vendas) se existirem no dicionário
            caption = f"🔥 **{p['titulo']}**\n"
            if p.get('avaliacao'): caption += f"{p['avaliacao']}\n"
            if p.get('vendas'): caption += f"📦 {p['vendas']}\n"
            
            caption += f"\n💰 **R$ {p['preco']}**\n"
            
            # Exibe o desconto real do Pix capturado pelo scraper
            if p.get('desconto'):
                caption += f"⚡️ **{p['desconto']}** à vista no Pix!\n"
            elif p.get('tem_pix'):
                caption += f"⚡️ Desconto especial no Pix!\n"
            
            caption += f"💳 {p['parcelas']}\n"
            caption += f"\n🔗 **Compre aqui:** {p['link']}\n\n"
            caption += f"➡️ Clique aqui para ver mais parecidos ➡️ #{tag}"

            # ENVIO DE MÍDIA (Download para a memória para evitar erros de URL)
            enviado_com_sucesso = False
            if p.get("imagem") and p["imagem"].startswith("http"):
                try:
                    r = requests.get(p["imagem"], timeout=15)
                    if r.status_code == 200:
                        foto = io.BytesIO(r.content)
                        foto.name = 'oferta.jpg' # Nome essencial para o Telegram reconhecer como foto
                        await client.send_file(
                            MEU_CANAL, 
                            foto, 
                            caption=caption, 
                            parse_mode='md',
                            force_document=False
                        )
                        enviado_com_sucesso = True
                except Exception as e_img:
                    print(f"Erro ao baixar imagem: {e_img}")

            # Backup: Se a imagem falhar, envia apenas o texto
            if not enviado_com_sucesso:
                await client.send_message(MEU_CANAL, caption, parse_mode='md')
            
            # Registo no Redis para não repetir
            if not modo_teste:
                marcar_enviado(p["id"])
            
            # INTERVALO DE SEGURANÇA (15 segundos)
            await asyncio.sleep(15)

        except Exception as e:
            await enviar_log(f"⚠️ **Erro ao postar item {p.get('id')}:**\n{e}")

# =========================
# COMANDOS E LOOP PRINCIPAL
# =========================
@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 **Teste iniciado!** Verificando ofertas agora...")
    await executar_ciclo(modo_teste=True)

async def executar_ciclo(modo_teste: bool = False):
    """Executa a varredura nas duas plataformas."""
    # Amazon
    produtos_amz = buscar_amazon()
    await processar_plataforma("AMAZON", produtos_amz, modo_teste)
    
    # Mercado Livre
    produtos_ml = buscar_mercado_livre()
    await processar_plataforma("MERCADO LIVRE", produtos_ml, modo_teste)

async def main():
    """Loop principal do bot."""
    await client.start()
    await enviar_log("✅ **Bot Online e Operacional!**\nMonitorização iniciada.")

    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            await enviar_log(f"🚨 **ERRO CRÍTICO NO LOOP:**\n{e}")
        
        # Dorme por 1 hora entre varreduras automáticas
        await asyncio.sleep(3600)

# =========================
# SERVIDOR FLASK (MANTER VIVO NO RENDER)
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot de Ofertas Ativo"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# INICIALIZAÇÃO
# =========================
if __name__ == "__main__":
    # Inicia o Flask numa thread separada
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    # Inicia o loop assíncrono do Telethon
    asyncio.run(main())