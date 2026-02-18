# Termos proibidos para manter o canal SFW (Safe For Work)
TERMOS_ADULTOS = [
    "vibrador", "sex shop", "sexshop", "dildo", "estimulador", "lubrificante intimo", 
    "lingerie sexy", "fantasia sexy", "masturbador", "algema", "chicote",
    "pênis", "vagina", "anal", "erótico", "sensual", "sadomasoquismo",
    "calcinha aberta", "cueca sexy", "gel lubrificante", "egg", "plug anal",
    "fio dental sexy", "transparente sexy", "erotica"
]

def eh_produto_seguro(titulo: str) -> bool:
    """Verifica se o título do produto contém termos proibidos."""
    if not titulo:
        return False
        
    titulo_low = titulo.lower()
    for termo in TERMOS_ADULTOS:
        if termo in titulo_low:
            return False
    return True