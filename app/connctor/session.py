from . import whatsapp


class SessionManager:
    def __init__(self):
        self._sessions = {}

    async def create_session(
        self,
        username: str,
        password: str,
        homeserver: str,
        identifier: str,
    )-> whatsapp.WhatsAppConnected:
        session = whatsapp.WhatsAppInit(username, password, homeserver, identifier)
        try:
            client = await session.login()
        except Exception as e:
            raise e
        
        if not isinstance(client, whatsapp.WhatsAppDisConnected):
            raise Exception("Matrix Login failed")
        
        client_conn = await client.connect()
        if not isinstance(client_conn, whatsapp.WhatsAppConnected):
            raise Exception("WhatsApp Login failed")
        
        self._sessions[identifier] = client_conn
        return client_conn

    async def get_session(self, identifier: str) -> whatsapp.WhatsAppInit | None:
        return self._sessions.get(identifier)

    def remove_session(self, identifier: str):
        return self._sessions.pop(identifier)
