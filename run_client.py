"""Script rápido para testar o cliente de API.

Executa login, health e exemplos de listagem de recursos.
"""

from src.config import load_config
from src.api.client import JwtApiClient
import json


def main() -> None:
    config = load_config()
    client = JwtApiClient(config)

    print("Testando login e autenticação...")
    client.login()

    print("\nTestando /health:")
    print(client.health())

    print("\nListando Pokémons (page=1, per_page=10):")
    pokemons = client.list_pokemon(page=1, per_page=10)
    print(json.dumps(pokemons, indent=2, ensure_ascii=False))

    print("\nAtributos do Pokémon (ex: ID 25):")
    details = client.get_pokemon_attributes(25)
    print(json.dumps(details, indent=2, ensure_ascii=False))

    print("\nListando combates:")
    combats = client.list_combats()
    print(json.dumps(combats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

