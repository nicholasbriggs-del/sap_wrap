import json
import requests
from json import JSONDecodeError
from random import Random


class SAPClient:
    def __init__(self, credentials_list=None, sap_client_id=None, timeout=30, csrf_fetch_timeout=5, verify_ssl=False):
        # credentials_list: string of space/newline separated 'user:pass'
        if isinstance(credentials_list, str):
            parts = [p for p in credentials_list.replace("\n", " ").split(" ") if p]
            creds = [(p.split(":", 1)[0], p.split(":", 1)[1]) for p in parts if ":" in p]
        elif isinstance(credentials_list, (list, tuple)):
            creds = credentials_list
        else:
            creds = []
        self._credentials = creds or []
        self._sap_usercontext = f"sap-client={sap_client_id}" if sap_client_id else None
        self.timeout = int(timeout) if timeout else 30
        self.csrf_fetch_timeout = int(csrf_fetch_timeout) if csrf_fetch_timeout else 5
        self.verify = bool(verify_ssl)
        self.csrf_token_map = {}

    def _get_credential(self):
        if not self._credentials:
            return None
        index = Random().randint(0, len(self._credentials) - 1)
        return self._credentials[index]

    def _get_usercontext_cookie(self):
        if not self._sap_usercontext:
            return {}
        return {"Cookie": f"sap-usercontext={self._sap_usercontext}"}

    def _fetch_csrf(self, client: requests.Session, url: str):
        headers = {"x-csrf-token": "fetch", "Accept": "application/json"}
        headers.update(self._get_usercontext_cookie())
        r = client.get(url=url, headers=headers, timeout=self.csrf_fetch_timeout, verify=self.verify)
        token = r.headers.get("x-csrf-token")
        cookie = r.headers.get("set-cookie")
        return token, cookie

    def _prepare_get(self, client):
        h = {"Accept": "application/json"}
        h.update(self._get_usercontext_cookie())
        client.headers.update(h)

    def _prepare_post_delete(self, client, url):
        client.headers.update(self._get_usercontext_cookie())
        token, cookie = self._fetch_csrf(client, url)
        if cookie:
            existing_cookie = client.headers.get("Cookie", "")
            client.headers.update({"Cookie": f"{cookie};{existing_cookie}"})
        client.headers.update({
            "x-csrf-token": token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _handle_client_error(self, resp):
        try:
            data = resp.json()
            err = data.get("error", {})
            msg = err.get("message", {})
            return msg.get("value") or resp.text
        except JSONDecodeError:
            return resp.text

    def get(self, url, params=None, headers=None, timeout=None):
        client = requests.Session()
        client.auth = self._get_credential()
        self._prepare_get(client)
        if headers:
            client.headers.update(headers)
        try:
            r = client.get(url=url, params=params or {}, timeout=timeout or self.timeout, verify=self.verify)
            r.raise_for_status()
            return r
        finally:
            client.close()

    def post(self, url, data=None, headers=None, timeout=None, retry=True, raw_text: str | None = None):
        client = requests.Session()
        client.auth = self._get_credential()
        self._prepare_post_delete(client, url)
        if headers:
            client.headers.update(headers)
        body = raw_text if isinstance(raw_text, str) else json.dumps(data or {})
        try:
            r = client.post(url=url, data=body, timeout=timeout or self.timeout, verify=self.verify)
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError as exc:
            if r.status_code == 403 and retry:
                # refresh CSRF and retry once
                self._prepare_post_delete(client, url)
                r = client.post(url=url, data=body, timeout=timeout or self.timeout, verify=self.verify)
                r.raise_for_status()
                return r
            raise exc
        finally:
            client.close()

    def delete(self, url, data=None, headers=None, timeout=None, retry=True):
        client = requests.Session()
        client.auth = self._get_credential()
        self._prepare_post_delete(client, url)
        if headers:
            client.headers.update(headers)
        # DELETE with parameters embedded as OData key predicate if needed
        try:
            if data and isinstance(data, dict):
                param_string = ",".join([f"{k}='{v}'" for k, v in data.items()])
                param_string = f"({param_string})" if param_string else ""
                url = f"{url}{param_string}"
            r = client.delete(url=url, timeout=timeout or self.timeout, verify=self.verify)
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError as exc:
            if r.status_code == 403 and retry:
                self._prepare_post_delete(client, url)
                r = client.delete(url=url, timeout=timeout or self.timeout, verify=self.verify)
                r.raise_for_status()
                return r
            raise exc
        finally:
            client.close()
