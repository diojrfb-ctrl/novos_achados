import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# Suas credenciais
API_ID = 32407152
API_HASH = 'db653015ecc7401831ad83298cb6605d'


async def main():
    print("--- 🛠 Gerador de Sessão Forçado ---")
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    phone = input("Digite seu telefone (ex: +5581999999999): ")
    sent = await client.send_code_request(phone)

    code = input("Digite o código que recebeu no Telegram: ")

    try:
        # Tenta logar com o código
        await client.sign_in(phone, code)
        print("✅ Logado sem 2FA (estranho, mas ok).")
    except Exception as e:
        # Se cair aqui, é porque o 2FA é necessário
        print(f"ℹ️ Status: {e}")
        password = input("Digite sua senha de 2FA (Nuvem): ")
        await client.sign_in(password=password)
        print("✅ Logado com 2FA com sucesso!")

    string_final = client.session.save()
    print("\n--- COPIE SUA NOVA STRING_SESSION ABAIXO ---")
    print(string_final)
    print("--- FIM DA STRING ---")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())