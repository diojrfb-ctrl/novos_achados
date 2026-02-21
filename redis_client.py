from upstash_redis import Redis
from config import UPSTASH_URL, UPSTASH_TOKEN

redis_client = Redis(url=UPSTASH_URL, token=UPSTASH_TOKEN)

def ja_enviado(prod_id: str) -> bool:
    try:
        # Usamos sets para busca rápida O(1)
        return redis_client.sismember("produtos_enviados", prod_id)
    except Exception:
        return False

def marcar_enviado(prod_id: str):
    try:
        redis_client.sadd("produtos_enviados", prod_id)
        # Opcional: Expira o ID após 7 dias para não encher o Redis
        # redis_client.expire("produtos_enviados", 604800)
    except Exception:
        pass