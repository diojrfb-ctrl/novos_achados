import os
from upstash_redis import Redis
from dotenv import load_dotenv

load_dotenv()

class DB:
    def __init__(self):
        self.client = Redis(
            url=os.getenv("UPSTASH_REDIS_REST_URL"),
            token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
        )

    def ja_postado(self, site, id_produto):
        return self.client.get(f"postado:{site}:{id_produto}")

    def salvar_postado(self, site, id_produto):
        # Salva por 48 horas (172800 segundos)
        self.client.set(f"postado:{site}:{id_produto}", "true", ex=172800)