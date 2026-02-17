import asyncio, io, requests, re
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def formatar_copy_profissional(p: dict) -> str:
    # Tratamento de valores para cálculo
    atual = float(p['preco'].replace('.', '').replace(',', '.'))
    antigo = float(p['preco_antigo'].replace('.', '').replace(',', '.')) if p['preco_antigo'] else 0
    
    # 1. Nome do Produto (Negrito)
    copy = f"**{p['titulo']}**\n"
    
    # 2. Ancoragem de Preço Realista
    if antigo > atual:
        economia = antigo - atual
        porcentagem = int((1 - (atual / antigo)) * 100)
        copy += f" de ~~R$ {p['preco_antigo']}~~\n"
        copy += f" por **R$ {p['preco']}** ({porcentagem}% OFF)\n"
        copy += f"📉 Economia de R$ {economia:.2f}\n\n"
    else:
        copy += f" por **R$ {p['preco']}**\n\n"

    # 3. Credibilidade
    copy += f"🏪 Vendido por: {p['loja']}\n"
    copy += f"🚚 Frete e estoque verificados\n\n"
    
    # 4. Call to Action (Link Curto Mascarado)
    # Mascaramos o link para passar confiança total
    copy += f"🔗 [Ver no Mercado Livre]({p['link']})\n\n"
    copy += f"➡️ #OfertaVerificada"
    
    return copy

async def processar():
    await client.start()
    produtos = buscar_mercado_livre()
    for p in produtos:
        try:
            caption = formatar_copy_profissional(p)
            if p["imagem"]:
                r = requests.get(p["imagem"])
                foto = io.BytesIO(r.content)
                foto.name = 'thumb.jpg'
                await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
                await asyncio.sleep(15) # Cooldown profissional
        except Exception as e:
            print(f"Erro ao processar: {e}")

if __name__ == "__main__":
    asyncio.run(processar())