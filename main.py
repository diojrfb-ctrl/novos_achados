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

def definir_tag(titulo: str) -> str:
    t = titulo.lower()
    if any(x in t for x in ["piscina", "mesa", "cadeira", "casa", "limpeza", "purificador", "penteadeira"]): return "Casa"
    if any(x in t for x in ["celular", "samsung", "iphone", "xiaomi"]): return "Smartphone"
    if any(x in t for x in ["gamer", "mouse", "teclado", "pc", "monitor", "cadeira gamer"]): return "Gamer"
    if any(x in t for x in ["carro", "pneu", "automotivo", "moto"]): return "Veículos"
    return "Acessórios"

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro ao enviar log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    novos = [p for p in produtos if p.get('status') == "novo"]
    
    # Relatório de Log
    await enviar_log(f"📊 **RELATÓRIO {nome}:** {len(novos)} itens novos prontos para envio.")

    for p in novos:
        try:
            tag = definir_tag(p['titulo'])
            
            # Montagem da legenda (Caption)
            caption = (
                f"🔥 **{p['titulo']}**\n\n"
                f"💰 **R$ {p['preco']}**\n"
                f"💳 {p['parcelas']}\n"
            )
            
            if p.get("tem_pix"):
                caption += "⚡️ 15% de desconto no pix\n"
            
            caption += f"\n🔗 **Compre aqui:** {p['link']}\n\n"
            caption += f"➡️ Clique aqui para ver mais parecidos ➡️ #{tag}"

            # --- ENVIO DA FOTO COM LEGENDA ---
            if p.get("imagem") and p["imagem"].startswith("http"):
                # O send_file com caption garante que o texto não se separe da imagem
                await client.send_file(
                    MEU_CANAL, 
                    p["imagem"], 
                    caption=caption,
                    parse_mode='md'
                )
            else:
                # Backup caso a imagem falhe
                await client.send_message(MEU_CANAL, caption, parse_mode='md')
            
            if not modo_teste:
                marcar_enviado(p["id"])
            
            # Intervalo de 12 segundos entre as postagens (Anti-Spam)
            await asyncio.sleep(12)

        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar item {p.get('id')}: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 Teste iniciado! Verifique os canais.")
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