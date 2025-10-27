"""ETL em CSV a partir da API Pokémon.

Extrai dados paginados (pokemons, combats, atributos), trata e salva em
arquivos CSV sob `data/`, com pequenos sleeps para evitar 429.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Iterable, List, Dict, Any, Iterable as TIterable

import pandas as pd

from src.config import load_config
from src.api.client import JwtApiClient


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _extract_list(
    payload: Any,
    *,
    keys: Iterable[str] = ("items", "results", "data", "pokemons", "combats"),
) -> List[Dict[str, Any]]:
    """Extrai uma lista de um payload possivelmente paginado."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in keys:
            v = payload.get(k)
            if isinstance(v, list):
                return v
    return []


def extract_pokemons(client: JwtApiClient, *, per_page: int = 50) -> pd.DataFrame:
    """Extrai todos os pokémons com feedback de progresso por página."""
    page = 1
    all_items: list[dict] = []
    total = None
    total_pages = None
    while True:
        payload = client.list_pokemon(page=page, per_page=per_page)
        items = payload.get("pokemons", [])
        total = payload.get("total", total or 0)
        if total and per_page:
            total_pages = total_pages or int(math.ceil(total / per_page))
        all_items.extend(items)

        if total_pages:
            print(f"Pokémons: página {page}/{total_pages} (acumulados: {len(all_items)}/{total})")
        else:
            print(f"Pokémons: página {page} (acumulados: {len(all_items)})")

        if not items or (page * per_page >= total):
            break
        page += 1
        time.sleep(0.2)

    df = pd.DataFrame.from_records(all_items) if all_items else pd.DataFrame()
    return df


def extract_combats(client: JwtApiClient, *, per_page: int = 50) -> pd.DataFrame:
    """Extrai combats com feedback de progresso por página."""
    page = 1
    all_items: list[dict] = []
    total = None
    total_pages = None
    while True:
        payload = client.list_combats(page=page, per_page=per_page)
        items = payload.get("combats", [])
        total = payload.get("total", total or 0)
        if total and per_page:
            total_pages = total_pages or int(math.ceil(total / per_page))
        all_items.extend(items)

        if total_pages:
            print(f"Combats: página {page}/{total_pages} (acumulados: {len(all_items)}/{total})")
        else:
            print(f"Combats: página {page} (acumulados: {len(all_items)})")

        if not items or (page * per_page >= total):
            break
        page += 1
        time.sleep(0.2)

    df = pd.json_normalize(all_items) if all_items else pd.DataFrame()
    if not df.empty and df.shape[1] == 1 and isinstance(df.iloc[0, 0], dict):
        df = pd.json_normalize(df.iloc[:, 0].tolist())
    return df


def extract_pokemon_attributes(
    client: JwtApiClient,
    ids: TIterable[Any],
    *,
    sleep: float = 0.2,
) -> pd.DataFrame:
    """Extrai atributos com progresso textual (itens concluídos / total)."""
    ids_list = list(ids)
    total = len(ids_list)
    records: list[dict] = []
    for i, pid in enumerate(ids_list, start=1):
        try:
            data = client.get_pokemon_attributes(pid)
        except Exception:
            data = None
        if isinstance(data, dict):
            if "id" not in data:
                data["id"] = pid
            records.append(data)
        if total:
            if i == total or i % max(1, total // 20) == 0:
                pct = (i / total) * 100
                print(f"Atributos: {i}/{total} ({pct:.0f}%)")
        time.sleep(sleep)
    return pd.json_normalize(records) if records else pd.DataFrame()


def transform_pokemons(df_pokemons: pd.DataFrame) -> pd.DataFrame:
    if df_pokemons.empty:
        return df_pokemons
    cols = [c for c in df_pokemons.columns if c in ("id", "name")]
    out = df_pokemons[cols].drop_duplicates()
    if "id" in out.columns:
        out = out.sort_values(by="id")
    return out.reset_index(drop=True)


def transform_combats(
    df_combats: pd.DataFrame,
    df_pokemons: pd.DataFrame,
    client: JwtApiClient,
) -> pd.DataFrame:
    if df_combats.empty:
        return df_combats

    expected_cols = ("first_pokemon", "second_pokemon", "winner")
    id_to_name: Dict[Any, Any] = {}
    if not df_pokemons.empty and {"id", "name"}.issubset(df_pokemons.columns):
        for pid, pname in zip(df_pokemons["id"], df_pokemons["name"]):
            id_to_name[pid] = pname
            id_to_name[str(pid)] = pname

    def lookup(val: Any) -> Any:
        if pd.isna(val):
            return val
        if val in id_to_name:
            return id_to_name[val]
        s = str(val)
        if s in id_to_name:
            return id_to_name[s]
        try:
            i = int(float(s))
            if i in id_to_name:
                return id_to_name[i]
        except Exception:
            pass
        return None

    for col in expected_cols:
        if col in df_combats.columns:
            df_combats[col + "_name"] = df_combats[col].apply(lookup)

    missing_ids: set = set()
    for col in expected_cols:
        if col in df_combats.columns and (col + "_name") in df_combats.columns:
            mask = df_combats[col + "_name"].isna()
            missing_vals = df_combats.loc[mask, col].dropna().unique().tolist()
            for mv in missing_vals:
                missing_ids.add(mv)

    if missing_ids:
        client.login()
        for mv in missing_ids:
            key_variants = [mv, str(mv)]
            try:
                key_variants.append(int(float(str(mv))))
            except Exception:
                pass
            if any(k in id_to_name for k in key_variants):
                continue
            try:
                details = client.get_pokemon_attributes(key_variants[-1])
                name = None
                if isinstance(details, dict):
                    name = details.get("name") or details.get("Name")
                if name:
                    for k in key_variants:
                        id_to_name[k] = name
            except Exception:
                pass
            time.sleep(0.2)

    for col in expected_cols:
        if col in df_combats.columns:
            df_combats[col] = df_combats[col].apply(lambda v: id_to_name.get(v, id_to_name.get(str(v), v)))

    aux_cols = [c for c in df_combats.columns if c.endswith("_name")]
    if aux_cols:
        df_combats.drop(columns=aux_cols, inplace=True, errors="ignore")

    return df_combats.reset_index(drop=True)


def save_csv(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Delimitador ; e BOM UTF-8 para compatibilidade com Excel PT-BR
    df.to_csv(path, index=False, sep=';', encoding='utf-8-sig')
    return path


def run(per_page: int = 50) -> None:
    config = load_config()
    client = JwtApiClient(config)

    # Autenticação e sanidade
    client.login()
    health = client.health()
    print("/health:", health)

    # Extrações
    print(f"Extraindo pokémons (per_page={per_page})...")
    df_pokemons = extract_pokemons(client, per_page=per_page)
    print("Pokémons:", len(df_pokemons))

    print("Extraindo combats (todas as páginas)...")
    df_combats = extract_combats(client, per_page=per_page)
    print("Combats:", len(df_combats))

    # Transformações
    df_pokemons = transform_pokemons(df_pokemons)
    print("Extraindo atributos dos pokémons...")
    df_attrs = extract_pokemon_attributes(client, df_pokemons["id"].tolist(), sleep=0.15)
    print("Atributos:", len(df_attrs))

    df_combats = transform_combats(df_combats, df_pokemons, client)

    # Persistência em CSV
    data_dir = config.data_dir
    _ensure_dir(data_dir)

    pokemons_csv = save_csv(df_pokemons, data_dir / "pokemons.csv")
    combats_csv = save_csv(df_combats, data_dir / "combats.csv")
    attrs_csv = save_csv(df_attrs, data_dir / "pokemon_attributes.csv")
    print("Arquivos gerados:")
    print("-", pokemons_csv)
    print("-", combats_csv)
    print("-", attrs_csv)


if __name__ == "__main__":
    # Validação inicial com per_page=50; depois você pode aumentar conforme necessário.
    run(per_page=50)
