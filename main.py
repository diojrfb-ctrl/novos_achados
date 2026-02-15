import asyncio
import threading
import os
import io
import requests # Para download da imagem
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
    if any(x in t for x in ["piscina", "mesa", "cadeira", "casa", "limpeza", "penteadeira"]): return "Casa"
    if any(x in t for x in ["celular", "samsung", "iphone", "xiaomi"]): return "Smartphone"
    if any(x in t for x in ["gamer", "mouse", "teclado", "ps5", "xbox"]): return "Gamer"
    if any(x in t for x in ["carro", "pneu", "moto", "capacete"]): return "Veículos"
    return "Ofertas"

async def enviar_log(texto: str):
    try:
        await client.send_message(LOG_CANAL, texto)
    except Exception as e:
        print(f"Erro log: {e}")

async def processar_plataforma(nome: str, produtos: list[dict], modo_teste: bool = False):
    novos = [p for p in produtos if p.get('status') == "novo"]
    await enviar_log(f"📊 **RELATÓRIO {nome}:** {len(novos)} novos itens encontrados.")

    for p in novos:
        try:
            tag = definir_tag(p['titulo'])
            caption = (
                f"🔥 **{p['titulo']}**\n\n"
                f"💰 **R$ {p['preco']}**\n"
                f"💳 {p['parcelas']}\n"
            )
            if p.get("tem_pix"): caption += "⚡️ 15% de desconto no pix\n"
            caption += f"\n🔗 **Compre aqui:** {p['link']}\n\n"
            caption += f"➡️ Clique aqui para ver mais parecidos ➡️ #{tag}"

            # Download da imagem para evitar o erro "Webpage media empty"
            if p.get("imagem") and p["imagem"].startswith("http"):
                response = requests.get(p["imagem"], timeout=10)
                if response.status_code == 200:
                    foto = io.BytesIO(response.content)
                    foto.name = 'produto.jpg' # Nome fictício para o Telethon reconhecer como imagem
                    await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
                else:
                    await client.send_message(MEU_CANAL, caption, parse_mode='md')
            else:
                await client.send_message(MEU_CANAL, caption, parse_mode='md')

            if not modo_teste:
                marcar_enviado(p["id"])
            
            # Intervalo de 15 segundos entre postagens
            await asyncio.sleep(15)

        except Exception as e:
            await enviar_log(f"⚠️ Erro ao postar item {p.get('id')}: {e}")

@client.on(events.NewMessage(pattern='/testar'))
async def handler_teste(event):
    await event.reply("🧪 Teste iniciado!")
    await executar_ciclo(modo_teste=True)

async def executar_ciclo(modo_teste: bool = False):
    await processar_plataforma("AMAZON", buscar_amazon(), modo_teste)
    await processar_plataforma("MERCADO LIVRE", buscar_mercado_livre(), modo_teste)

async def main():
    await client.start()
    await enviar_log("✅ **Bot Online!**")
    while True:
        try:
            await executar_ciclo(modo_teste=False)
        except Exception as e:
            print(f"Erro loop: {e}")
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route("/")
def home(): return "Bot Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    asyncio.run(main())