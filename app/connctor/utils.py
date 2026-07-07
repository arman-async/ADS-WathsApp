from hashlib import sha256

import httpx
import nio


class WhatsAppUser:
    @staticmethod
    def gen_username(identifier: str, domain: str) -> str:
        return f"@wa_{identifier.replace('+', '')}:{domain}"

    @staticmethod
    def gen_password(identifier: str, domain: str) -> str:
        return sha256(
            WhatsAppUser.gen_username(identifier, domain).encode("utf-8")
        ).hexdigest()


class MatrixUserManager:
    @staticmethod
    async def get_token(
        username: str,
        password: str,
        homeserver: str,
    ) -> str | None:
        client = nio.AsyncClient(homeserver, username)
        token = None
        try:
            token = (await client.login(password)).access_token
        except AttributeError:
            pass
        await client.close()
        return token

    @staticmethod
    async def user_create(
        admin_token: str,
        *,
        username: str,
        password: str,
        homeserver: str,
    ) -> bool:
        """
        Create a user in Matrix Synapse server
        """
        url = f"{homeserver}/_synapse/admin/v2/users/{username}"
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "password": password,
            "displayname": username,
            "admin": False,
            "deactivated": False,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.put(url, headers=headers, json=payload)
            if resp.status_code < 300:
                return True
        return False

    @staticmethod
    async def check_user_exists(homeserver: str, username: str, password: str) -> bool:
        client = nio.AsyncClient(homeserver)

        try:
            resp = await client.login(username, password)

            if hasattr(resp, "user_id"):
                await client.close()
                return True

        except Exception:
            await client.close()
            return False

        await client.close()
        return False

    @staticmethod
    async def user_remove(
        admin_token: str,
        *,
        username: str,
        homeserver: str,
    ) -> bool:
        """
        Deactivate and Delete a user completely from Matrix Synapse server
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        async with httpx.AsyncClient() as client:
            # 1. Deactivate
            deactivate_url = f"{homeserver}/_synapse/admin/v1/deactivate/{username}"
            await client.post(deactivate_url, headers=headers, json={"erase": True})

            # 2. Delete completely
            delete_url = f"{homeserver}/_synapse/admin/v2/users/{username}"
            resp = await client.delete(delete_url, headers=headers)

            return resp.status_code in (200, 204)
