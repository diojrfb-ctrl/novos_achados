import asyncio, io, requests, os, threading
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession

# Importações dos seus módulos locais
from config import API_ID, API_HASH, STRING_SESSION, MEU_CANAL
from mercado_livre import buscar_mercado_livre
from redis_client import marcar_enviado

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

def extrair_categoria_hashtag(titulo: str) -> str:
    """Extrai uma hashtag de categoria baseada em palavras-chave no título."""
    titulo_low = titulo.lower()
    categorias = {
        "Cozinha": ["panela", "fritadeira", "airfryer", "prato", "copo", "talher", "cozinha"],
        "Games": ["ps5", "xbox", "nintendo", "jogo", "gamer", "placa de vídeo", "console"],
        "Eletronicos": ["smartphone", "celular", "iphone", "televisao", "tv", "monitor", "fone", "moto g"],
        "Suplementos": ["whey", "creatina", "suplemento", "vitamin", "albumina"],
        "Informatica": ["notebook", "laptop", "teclado", "mouse", "ssd", "memoria"],
        "Casa": ["toalha", "lençol", "aspirador", "iluminação", "móvel", "sofa"]
    }
    
    for cat, keywords in categorias.items():
        if any(kw in titulo_low for kw in keywords):
            return f" #{cat}"
    return ""

def formatar_copy_otimizada(p: dict) -> str:
    """Formata a mensagem seguindo o template do smartphone Motorola."""
    try:
        # Tratamento de Preço Atual e Antigo
        atual_num = float(p['preco'].replace('.', '').replace(',', '.'))
        linha_preco_antigo = ""
        linha_desconto = ""

        if p.get('preco_antigo'):
            antigo_num = float(p['preco_antigo'].replace('.', '').replace(',', '.'))
            if antigo_num > atual_num:
                porcentagem = int((1 - (atual_num / antigo_num)) * 100)
                linha_preco_antigo = f"💰 De: R$ {p['preco_antigo']}\n"
                linha_desconto = f"📉 ({porcentagem}% de desconto no Pix)\n"

        # Formatação do Parcelamento (ou R$ [PRECO] em [PARCELAS])
        linha_cartao = ""
        if p.get('parcelas'):
            # O texto já vem formatado do mercado_livre.py como "em 10x R$ X sem juros"
            linha_cartao = f"💳 ou R$ {p['preco']} {p['parcelas']}\n"

        hashtag_cat = extrair_categoria_hashtag(p['titulo'])

        # Montagem Final do Post
        copy = f"**{p['titulo']}**\n"
        copy += f"⭐ {p['nota']} ({p['avaliacoes']} opiniões)\n"
        copy += linha_preco_antigo
        copy += f"✅ **POR: R$ {p['preco']}**\n"
        copy += linha_desconto
        copy += linha_cartao
        copy += f"📦 Frete: {p['frete']}\n"
        copy += f"🔥 Estoque: {p['estoque']}\n\n"
        copy += f"🔗 **LINK DA OFERTA:**\n"
        copy += f"{p['link']}\n\n"
        copy += f"➡️ #Ofertas #MercadoLivre{hashtag_cat}"
        
        return copy
    except Exception as e:
        print(f"Erro na formatação: {e}")
        return f"**{p['titulo']}**\n\n✅ **POR: R$ {p['preco']}**\n\n🔗 {p['link']}"

async def loop_bot():
    """Ciclo de busca e postagem no Telegram."""
    await client.start()
    print("Bot de Ofertas Online!")
    
    while True:
        produtos = buscar_mercado_livre()
        
        for p in produtos:
            try:
                caption = formatar_copy_otimizada(p)
                
                if p.get("imagem"):
                    r = requests.get(p["imagem"], timeout=15)
                    r.raise_for_status()
                    foto = io.BytesIO(r.content)
                    foto.name = 'post.jpg'
                    
                    await client.send_file(MEU_CANAL, foto, caption=caption, parse_mode='md')
                    marcar_enviado(p["id"]) # Registra no Redis após o sucesso
                    await asyncio.sleep(30) # Delay anti-spam
                    
            except Exception as e:
                print(f"Erro no item {p.get('id')}: {e}")
                continue
        
        print("Aguardando próximo ciclo...")
        await asyncio.sleep(3600)

app = Flask(__name__)
@app.route('/')
def health(): return "OK", 200

async def main():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port), daemon=True).start()
    await loop_bot()

if __name__ == "__main__":
    asyncio.run(main())