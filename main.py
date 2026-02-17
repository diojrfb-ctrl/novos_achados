import asyncio
import io
import requests
import os
import threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession

# Importações do seu projeto
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre
from redis_client import marcar_enviado # Garante que o ID seja salvo após o envio

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def formatar_copy_limpa(p: dict) -> str:
    """Formata a mensagem do Telegram com os dados do produto."""
    try:
        # Lógica de cálculo de preço e economia
        atual_num = float(p['preco'].replace('.', '').replace(',', '.'))
        if p.get('preco_antigo'):
            antigo_num = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
            economia = antigo_num - atual_num
            porcentagem = int((1 - (atual_num / antigo_num)) * 100)
            
            precos = f"💰 ~~R$ {p['preco_antigo']}~~\n"
            precos += f"✅ **POR APENAS: R$ {p['preco']}**\n"
            precos += f"📉 **ECONOMIA DE R$ {economia:.2f} ({porcentagem}% OFF)**"
        else:
            precos = f"✅ **POR APENAS: R$ {p['preco']}**"
    except Exception:
        precos = f"✅ **POR APENAS: R$ {p['preco']}**"

    # Construção da cópia profissional
    copy = f"**{p['titulo']}**\n"
    copy += f"⭐ {p['nota']} ({p['avaliacoes']}+ avaliações)\n\n"
    copy += f"{precos}\n\n"
    copy += f"🏪 Vendido por: {p['loja']}\n"
    copy += f"🚀 Envio rápido garantido\n"
    copy += f"⚠️ Estoque limitado!\n\n"
    copy += f"🔗 **LINK DO PRODUTO:**\n"
    copy += f"{p['link']}\n\n" # Agora envia a URL completa e funcional
    copy += f"➡️ #Ofertas #MercadoLivre"
    return copy

async def loop_bot():
    """Loop principal de busca e postagem."""
    await client.start()
    print("Bot iniciado com sucesso!")
    
    while True:
        # A busca agora já filtra duplicatas internamente via redis_client.ja_enviado
        produtos = buscar_mercado_livre()
        
        for p in produtos:
            try:
                caption = formatar_copy_limpa(p)
                
                if p.get("imagem"):
                    # Download da imagem para envio como arquivo (evita expiração de links)
                    r = requests.get(p["imagem"], timeout=15)
                    r.raise_for_status()
                    
                    foto = io.BytesIO(r.content)
                    foto.name = 'post.jpg'
                    
                    # Envio para o Telegram
                    await client.send_file(
                        MEU_CANAL, 
                        foto, 
                        caption=caption, 
                        parse_mode='md'
                    )
                    
                    # Registra no Redis para não postar novamente
                    marcar_enviado(p["id"])
                    
                    # Intervalo entre postagens para evitar spam/ban
                    await asyncio.sleep(30)
                    
            except Exception as e:
                print(f"Erro ao processar produto {p.get('id')}: {e}")
        
        # Espera 1 hora antes da próxima varredura de ofertas
        print("Varredura concluída. Aguardando próximo ciclo...")
        await asyncio.sleep(3600)

# Configuração do Flask para manter o serviço ativo (Health Check)
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot Online", 200

async def main():
    # Porta dinâmica para ambientes como Render ou Heroku
    port = int(os.environ.get("PORT", 10000))
    
    # Inicia o Flask em uma thread separada
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port), 
        daemon=True
    ).start()
    
    # Inicia o loop do Telegram
    await loop_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot desligado.")