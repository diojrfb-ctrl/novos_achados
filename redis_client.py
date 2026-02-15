from upstash_redis import Redis
from config import UPSTASH_URL, UPSTASH_TOKEN

# Inicializa o cliente uma única vez
redis_client = Redis(
    url=UPSTASH_URL,
    token=UPSTASH_TOKEN
)

def ja_enviado(prod_id: str) -> bool:
    """Verifica se o ID já existe no set do Redis."""
    try:
        return redis_client.sismember("produtos_enviados", prod_id)
    except Exception as e:
        print(f"Erro Redis (check): {e}")
        return False

def marcar_enviado(prod_id: str):
    """Adiciona o ID ao set do Redis."""
    try:
        redis_client.sadd("produtos_enviados", prod_id)
    except Exception as e:
        print(f"Erro Redis (save): {e}")