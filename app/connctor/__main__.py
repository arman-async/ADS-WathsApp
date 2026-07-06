import asyncio

import httpx
import nio

from . import whatsapp


async def admin_token(homeserver: str, username: str, password: str) -> str:
    client = nio.AsyncClient(homeserver, username)
    token = None
    try:
        token = (await client.login(password)).access_token
    except AttributeError:
        pass
    return token


async def user_create(
    homeserver: str,
    domain: str,
    admin_token: str,
    username: str,
    password: str,
):
    """
    Create a user in Matrix Synapse server
    """
    url = f"{homeserver}/_synapse/admin/v2/users/@{username}:{domain}"
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "password": password,
        "displayname": username,
        "admin": False,
        "deactivated": False,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.put(url, headers=headers, json=payload)
        return {"status": resp.status_code, "data": resp.json()}


async def user_remove(homeserver: str, domain: str, admin_token: str, username: str):
    """
    Remove (deactivate) a user from Matrix Synapse server
    """
    mxid = f"@{username}:{domain}"
    url = f"{homeserver}/_synapse/admin/v1/deactivate/{mxid}"
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {"erase": True}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        return {"status": resp.status_code, "data": resp.json()}

async def test():
    # token = await admin_token(
    #     homeserver="http://localhost:8008",
    #     username="root",
    #     password="root",
    # )
    # resp = await user_create(
    #     homeserver="http://localhost:8008",
    #     domain="matrix.local",
    #     admin_token=token,
    #     username="wa_989370466248",
    #     password="12345678",
    # )
    # print(f"Create New User : {resp}")
    
    
    ws = whatsapp.WhatsAppInit(
        username="@wa_989370466248:matrix.local",
        password="12345678",
        homeserver="http://localhost:8008",
        identifier="+989370466248"
    )

    ws = await ws.login()
    # code = await ws.login()
    # print(f"Login Code: {code}")
    # input("Press Enter Connected")
    from app.services.whatsapp import filter_whatsapp_group
    connected = await ws.connect()
    chat = await connected.start_chat("+989014948464")
    print(f"Chat ID: {chat.room_id}")
    await connected.send_text(chat.room_id, "hii")
    while True:
        
        await connected.sync()
        await connected.accept_invites()
        await connected.sync()
        dilogs = await connected.get_dialogs(filter=filter_whatsapp_group)
        print(f"Dialogs: {dilogs}")
        input()
        breakpoint()
    
async def main():
    token = await admin_token(
        homeserver="http://localhost:8008",
        username="root",
        password="root",
    )

    print(token)
    # # await user_remove(
    # #     homeserver="http://localhost:8008",
    # #     domain="matrix.local",
    # #     admin_token=token,
    # #     username="wa_989370466248",
    # # )
    # # resp = await user_create(
    # #     homeserver="http://localhost:8008",
    # #     domain="matrix.local",
    # #     admin_token=token,
    # #     username="wa_989370466248",
    # #     password="12345678",
    # # )
    # # print(resp)

    # ws = whatsapp.WhatsAppInit(
    #     username="@wa_989370466248:matrix.local",
    #     password="12345678",
    #     homeserver="http://localhost:8008",
    #     identifier="+989370466248"
    # )

    # ws = await ws.login()
    # # # code = await ws.login()
    # # # print(code)

    # connected = await ws.connect()
    # chat = await connected.start_chat("+989014948464")
    # print(chat)
    # await connected.send_text(chat.room_id, "hii")
    # # breakpoint()


asyncio.run(test())
