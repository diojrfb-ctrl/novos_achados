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

# Função para definir categorias automaticamente
def definir_tag(titulo: str) -> str:
    t = titulo.lower()
    if any(x in t for x in ["piscina", "mesa", "cadeira", "casa", "limpeza", "penteadeira", "cozinha"]): return "Casa"
    if any(x in t for x in ["celular", "samsung", "iphone", "xiaomi", "motorola"]): return "Smartphone"
    if any(x in t for x in ["gamer", "mouse", "teclado", "pc", "monitor", "video game", "ps5"]): return "Gamer"
    if any(x in t for x in ["carro", "pneu", "automotivo", "moto", "capacete"]): return "Veículos"
    if any(x in t for x in ["fone", "relógio", "smartwatch", "carregador"]): return "Acessórios"
    return "Ofertas"

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    novos = [p for p in produtos if p.get('status') == "novo"]
    
    await enviar_log(f"📊 **RELATÓRIO {nome}:** {len(novos)} novos itens identificados.")

    for p in novos:
        try:
            tag = definir_tag(p['titulo'])
            
            # Formatação da Mensagem
            caption = (
                f"🔥 **{p['titulo']}**\n\n"
                f"💰 **R$ {p['preco']}**\n"
                f"💳 {p['parcelas']}\n"
            )
            
            if p.get("tem_pix"):
                caption += "⚡️ 15% de desconto no pix\n"
            
            caption += f"\n🔗 **Compre aqui:** {p['link']}\n\n"
            caption += f"➡️ Clique aqui para ver mais parecidos ➡️ #{tag}"

            # Envio da FOTO com legenda (force_document=False evita que vire arquivo)
            if p.get("imagem") and p["imagem"].startswith("http"):
                await client.send_file(
                    MEU_CANAL, 
                    p["imagem"], 
                    caption=caption,
                    parse_mode='md',
                    force_document=False
                )
            else:
                await client.send_message(MEU_CANAL, caption, parse_mode='md')
            
            if not modo_teste:
                marcar_enviado(p["id"])
            
            # Intervalo de 15 segundos entre as postagens para não bombardear o canal
            await asyncio.sleep(15)

        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar item {p.get('id')}: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 Teste iniciado! Verifique os canais.")
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
            print(f"Erro no loop: {e}")
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route("/")
def home(): return "Bot Ativo"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.run(main())