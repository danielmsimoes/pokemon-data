import requests
import time
import random
from typing import Optional
from src.config import Config


class JwtApiClient:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self._token: Optional[str] = None

    def url(self, endpoint: str) -> str:
        """Monta a URL final unindo base e endpoint"""
        base = self.config.api_base_url.rstrip("/")
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{path}"

    def login(self) -> None:
        url = self.url(self.config.api_login_endpoint)
        payload = {
            "username": self.config.api_username,
            "password": self.config.api_password,
        }

        try:
            resp = self.session.post(url, json=payload, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Falha na requisição de login: {e}") from e

        try:
            data = resp.json()
        except ValueError:
            data = {}

        token = data.get("access_token") or data.get("token") or data.get("jwt")
        token_type = data.get("token_type")
        if isinstance(token_type, str) and token_type.lower() == "bearer":
            token_type = "Bearer"
        if not token_type:
            token_type = "Bearer"
        if not token:
            raise RuntimeError(
                "Não foi possível obter o token JWT no login. Verifique credenciais e o formato do JSON."
            )

        self._token = token
        self.session.headers.update({"Authorization": f"{token_type} {token}"})

    def _request(self, method: str, endpoint: str, *, params=None, json=None, retry_on_401: bool = True):
        """Requisição com autenticação, retry em 401 e tratamento de 429 (rate limit)."""
        url = self.url(endpoint)
        if not self._token:
            self.login()

        max_retries = 5
        base_backoff = 0.5  # segundos

        for attempt in range(max_retries):
            resp = self.session.request(method, url, params=params, json=json, timeout=60)

            # 401: tentar renovar o token uma vez neste ciclo
            if resp.status_code == 401 and retry_on_401:
                self.login()
                resp = self.session.request(method, url, params=params, json=json, timeout=60)

            # 429: respeita Retry-After ou aplica backoff exponencial com jitter
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = base_backoff * (2 ** attempt) + random.uniform(0, 0.2)
                else:
                    delay = base_backoff * (2 ** attempt) + random.uniform(0, 0.2)
                time.sleep(min(delay, 10))
                continue

            # 502/503/504: falhas transitórias
            if resp.status_code in (502, 503, 504):
                delay = base_backoff * (2 ** attempt) + random.uniform(0, 0.2)
                time.sleep(min(delay, 5))
                continue

            resp.raise_for_status()
            return resp

        # Se esgotou tentativas, levanta o último erro
        resp.raise_for_status()
        return resp

    def get_json(self, endpoint: str, *, params=None):
        resp = self._request("GET", endpoint, params=params)
        return resp.json() if resp.content else None

    def health(self):
        return self.get_json(self.config.health_endpoint)

    def list_pokemon(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        params: dict | None = None,
    ) -> dict:
        qparams = dict(params or {})
        if page is not None:
            qparams["page"] = page
        if per_page is not None:
            qparams["per_page"] = per_page

        payload = self.get_json(self.config.pokemon_endpoint, params=qparams) or {}
        result = {
            "pokemons": payload.get("pokemons", []),
            "page": payload.get("page", page or 1),
            "per_page": payload.get("per_page", per_page or 10),
            "total": payload.get("total", len(payload.get("pokemons", []))),
        }
        return result

    def list_all_pokemon(self, *, per_page: int = 50) -> list[dict]:
        page = 1
        all_pokemons: list[dict] = []
        total = None

        while True:
            data = self.list_pokemon(page=page, per_page=per_page)
            pokemons = data["pokemons"]
            total = data["total"]
            all_pokemons.extend(pokemons)

            if page * per_page >= total or len(pokemons) < per_page:
                break
            page += 1
            # Pequeno intervalo para evitar rajadas e 429
            time.sleep(0.4)
        return all_pokemons

    def get_pokemon_attributes(self, pokemon_id):
        ep = self.config.pokemon_attributes_endpoint.format(pokemon_id=pokemon_id)
        return self.get_json(ep)

    def list_combats(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        params: dict | None = None,
    ) -> dict:
        qparams = dict(params or {})
        if page is not None:
            qparams["page"] = page
        if per_page is not None:
            qparams["per_page"] = per_page

        payload = self.get_json(self.config.combats_endpoint, params=qparams) or {}
        combats = payload.get("combats", [])
        return {
            "combats": combats,
            "page": payload.get("page", page or 1),
            "per_page": payload.get("per_page", per_page or 10),
            "total": payload.get("total", len(combats)),
        }

    def list_all_combats(self, *, per_page: int = 50) -> list[dict]:
        page = 1
        all_combats: list[dict] = []
        total = None

        while True:
            data = self.list_combats(page=page, per_page=per_page)
            combats = data.get("combats", [])
            total = data.get("total", len(combats))
            all_combats.extend(combats)

            if page * per_page >= total or len(combats) < per_page:
                break
            page += 1
            time.sleep(0.4)

        return all_combats
