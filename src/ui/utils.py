"""
Modulo utilitario da interface: carrega dados e fornece helpers
compartilhados (tipos, paleta de cores, parse de tipos e normalizacao
de atributos) para as paginas do Streamlit.
"""

from __future__ import annotations

from typing import List

import pandas as pd

from src.analysis.metrics import load_data


def load_all():
    """Carrega pokemons, combats e attrs a partir da pasta data/ (CSV)."""
    return load_data("data")


# 18 tipos oficiais (EN) para consistencia
OFFICIAL_TYPES_EN: List[str] = [
    "Normal",
    "Fire",
    "Water",
    "Grass",
    "Flying",
    "Fighting",
    "Poison",
    "Electric",
    "Ground",
    "Rock",
    "Psychic",
    "Ice",
    "Bug",
    "Ghost",
    "Steel",
    "Dragon",
    "Dark",
    "Fairy",
]


# Paleta fixa por tipo para todos os graficos
TYPE_COLORS_EN = {
    "Water": "#1E90FF",
    "Fire": "#FF4500",
    "Grass": "#2E8B57",
    "Electric": "#FFD700",
    "Psychic": "#EE82EE",
    "Ice": "#00CED1",
    "Fighting": "#CD5C5C",
    "Poison": "#8A2BE2",
    "Ground": "#DEB887",
    "Flying": "#87CEEB",
    "Bug": "#9ACD32",
    "Rock": "#A0522D",
    "Ghost": "#6A5ACD",
    "Dragon": "#FF8C00",
    "Dark": "#2F4F4F",
    "Steel": "#708090",
    "Fairy": "#FF69B4",
    "Normal": "#A8A77A",
}


def parse_types(val) -> list[str]:
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()]
    if isinstance(val, list):
        return [str(x) for x in val]
    return []


def ensure_overall(attrs: pd.DataFrame) -> pd.DataFrame:
    """Garante colunas numericas e calcula overall (inteiro)."""
    df = attrs.copy()
    stats = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
    for col in stats:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "overall" not in df.columns and all(c in df.columns for c in stats):
        df["overall"] = (
            df["hp"]
            + df["attack"]
            + df["defense"]
            + df["sp_attack"]
            + df["sp_defense"]
            + df["speed"]
        )
    if "overall" in df.columns:
        df["overall"] = pd.to_numeric(df["overall"], errors="coerce").round(0).astype("Int64")
    if "types" not in df.columns:
        df["types"] = None
    return df

