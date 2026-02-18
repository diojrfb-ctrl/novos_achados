import re

def extrair_categoria_hashtag(titulo: str) -> str:
    """Identifica a categoria com base em palavras-chave no título."""
    titulo_low = titulo.lower()
    categorias = {
        "Cozinha": ["panela", "fritadeira", "airfryer", "prato", "copo", "talher", "cozinha"],
        "Games": ["ps5", "xbox", "nintendo", "jogo", "gamer", "console"],
        "Eletronicos": ["smartphone", "celular", "iphone", "televisao", "tv", "monitor", "fone"],
        "Suplementos": ["whey", "creatina", "suplemento", "vitamin", "albumina", "protein"],
        "Informatica": ["notebook", "laptop", "teclado", "mouse", "ssd", "memoria"],
        "Casa": ["toalha", "lençol", "aspirador", "iluminação", "móvel", "sofa"]
    }
    for cat, keywords in categorias.items():
        if any(kw in titulo_low for kw in keywords):
            return f" #{cat}"
    return ""

def formatar_copy_otimizada(p: dict, simplificado: bool = False) -> str:
    """Formata a mensagem final para o Telegram."""
    try:
        hashtag_cat = extrair_categoria_hashtag(p['titulo'])
        copy = f"**{p['titulo']}**\n"
        copy += f"⭐ {p['nota']} ({p['avaliacoes']} opiniões)\n"

        if simplificado:
            # Layout Amazon: Exibe apenas o preço promocional
            copy += f"✅ **Por apenas R$ {p['preco']}**\n"
        else:
            # Layout Padrão (ML): Exibe preço antigo e cálculo de desconto
            preco_limpo = re.sub(r'[^\d,]', '', p['preco']).replace(',', '.')
            atual_num = float(preco_limpo)
            
            if p.get('preco_antigo'):
                # Limpeza para garantir que o cálculo não falhe
                antigo_limpo = re.sub(r'[^\d,]', '', str(p['preco_antigo'])).replace(',', '.')
                try:
                    antigo_num = float(antigo_limpo)
                    if antigo_num > atual_num:
                        porcentagem = int((1 - (atual_num / antigo_num)) * 100)
                        copy += f"💰 De: R$ {p['preco_antigo']}\n"
                        copy += f"📉 ({porcentagem}% de desconto)\n"
                except:
                    pass
            
            copy += f"✅ **POR: R$ {p['preco']}**\n"

        # Linhas comuns a todos os componentes
        linha_cartao = f"💳 ou {p['parcelas'].replace('ou', '').strip()}\n" if p.get('parcelas') else ""
        copy += linha_cartao
        copy += f"📦 Frete: {p['frete']}\n"
        copy += f"🔥 Estoque: {p['estoque']}\n\n"
        copy += f"🔗 **LINK DA OFERTA:**\n{p['link']}\n\n"
        copy += f"➡️ #Ofertas{hashtag_cat}"
        
        return copy
    except Exception as e:
        print(f"Erro na formatação: {e}")
        return f"**{p['titulo']}**\n\n✅ POR: R$ {p['preco']}\n\n🔗 {p['link']}"