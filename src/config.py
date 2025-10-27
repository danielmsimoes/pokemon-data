"""Leitura de variáveis de ambiente e configuração do app.

Carrega `.env`, garante a pasta `data/` e expõe endpoints/credenciais
para o cliente de API e o pipeline ETL.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Config:
    api_base_url: str
    api_login_endpoint: str
    api_username: str
    api_password: str
    health_endpoint: str
    pokemon_endpoint: str
    pokemon_attributes_endpoint: str
    combats_endpoint: str
    data_dir: Path
    db_url: str


def load_config() -> Config:
    load_dotenv()

    data_dir = Path(os.getenv("DATA_DIR", "data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    return Config(
        api_base_url=os.getenv("API_BASE_URL", "").rstrip("/"),
        api_login_endpoint=os.getenv("API_LOGIN_ENDPOINT", "/auth/login"),
        api_username=os.getenv("API_USERNAME", ""),
        api_password=os.getenv("API_PASSWORD", ""),
        health_endpoint=os.getenv("HEALTH_ENDPOINT", "/health"),
        pokemon_endpoint=os.getenv("POKEMON_ENDPOINT", "/pokemon"),
        pokemon_attributes_endpoint=os.getenv("POKEMON_ATTRIBUTES_ENDPOINT", "/pokemons/{pokemon_id}"),
        combats_endpoint=os.getenv("COMBATS_ENDPOINT", "/combats"),
        data_dir=data_dir,
        db_url=os.getenv("DB_URL", f"sqlite:///{data_dir}/pokemon.db"),
    )
