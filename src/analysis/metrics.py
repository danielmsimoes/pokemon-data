from __future__ import annotations

from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


def load_data(data_dir: Path | str = "data") -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
    data_dir = Path(data_dir)
    pokemons = pd.read_csv(data_dir / "pokemons.csv", sep=";", encoding="utf-8-sig")
    combats = pd.read_csv(data_dir / "combats.csv", sep=";", encoding="utf-8-sig")
    attrs_path = data_dir / "pokemon_attributes.csv"
    attrs = pd.read_csv(attrs_path, sep=";", encoding="utf-8-sig") if attrs_path.exists() else None
    return pokemons, combats, attrs


# ---------------------
# Métricas básicas
# ---------------------

def compute_participations(combats: pd.DataFrame) -> pd.DataFrame:
    first_counts = combats["first_pokemon"].value_counts(dropna=False)
    second_counts = combats["second_pokemon"].value_counts(dropna=False)
    total = (first_counts.add(second_counts, fill_value=0)).rename("participations").reset_index()
    total = total.rename(columns={"index": "name"})
    total = total.sort_values("participations", ascending=False, ignore_index=True)
    return total


def compute_winrate(combats: pd.DataFrame, min_battles: int = 1) -> pd.DataFrame:
    winners = combats["winner"].value_counts().rename("wins")

    losers = (
        pd.concat([
            combats[["first_pokemon", "winner"]].rename(columns={"first_pokemon": "p"}),
            combats[["second_pokemon", "winner"]].rename(columns={"second_pokemon": "p"}),
        ])
        .query("p != winner")
        ["p"].value_counts()
        .rename("losses")
    )

    perf = pd.DataFrame({"wins": winners}).join(losers, how="outer").fillna(0)
    perf.index.name = "name"
    perf = perf.reset_index()
    perf["wins"] = perf["wins"].astype(int)
    perf["losses"] = perf["losses"].astype(int)
    perf["total"] = perf["wins"] + perf["losses"]
    perf = perf.query("total >= @min_battles").copy()
    perf["win_rate"] = (perf["wins"] / perf["total"]).round(4)
    perf = perf.sort_values(["win_rate", "total", "wins"], ascending=[False, False, False], ignore_index=True)
    return perf


# ---------------------
# Integração com atributos
# ---------------------

def _extract_types_column(attrs: pd.DataFrame) -> pd.DataFrame:
    """Cria linhas por tipo (explode) e padroniza a coluna 'type'.
    Tenta suportar formatos comuns: 'types' como lista de strings, string com vírgulas,
    lista de dicts com chave 'name', ou campos 'type'/'primary_type'/'secondary_type'.
    """
    if attrs is None or attrs.empty:
        return pd.DataFrame(columns=["id", "type"])  # vazio

    df = attrs.copy()

    # Preferência: coluna 'types'
    if "types" in df.columns:
        series = df["types"].copy()

        def normalize_cell(v):
            if isinstance(v, list):
                if not v:
                    return []
                if all(isinstance(x, str) for x in v):
                    return v
                if all(isinstance(x, dict) for x in v):
                    out = []
                    for d in v:
                        name = d.get("name") or d.get("type") or d.get("Type")
                        if name:
                            out.append(str(name))
                    return out
                return [str(x) for x in v]
            if isinstance(v, str):
                # separa por vírgula
                return [s.strip() for s in v.split(",") if s.strip()]
            return []

        types_norm = series.apply(normalize_cell)
        exploded = df[["id"]].join(types_norm.rename("type")).explode("type")
        exploded = exploded.dropna(subset=["type"])  # remove vazios
        return exploded[["id", "type"]].reset_index(drop=True)

    # Alternativas por colunas separadas
    for col in ("type", "Type", "primary_type", "secondary_type"):
        if col in df.columns:
            tmp = df[["id", col]].rename(columns={col: "type"}).copy()
            tmp = tmp.dropna(subset=["type"])  # remove vazios
            return tmp.reset_index(drop=True)

    # Sem colunas de tipo
    return pd.DataFrame(columns=["id", "type"])  # vazio


def compute_type_winrate(
    winrate: pd.DataFrame, pokemons: pd.DataFrame, attrs: Optional[pd.DataFrame]
) -> pd.DataFrame:
    """Calcula taxa média de vitória por tipo.

    - Explode pokémons com dois tipos: cada tipo recebe o registro (sem categoria combinada).
    - Retorna apenas média simples e contagem de pokémons, para visual mais claro.
    """
    if attrs is None or attrs.empty:
        return pd.DataFrame(columns=["type", "taxa_media_vitoria", "qtd_pokemons"])

    types_df = _extract_types_column(attrs)
    wr = winrate.merge(pokemons, on="name", how="left")
    wr_types = wr.merge(types_df, on="id", how="left").dropna(subset=["type"])

    if wr_types.empty:
        return pd.DataFrame(columns=["type", "taxa_media_vitoria", "qtd_pokemons"])

    grouped = wr_types.groupby("type", as_index=False).agg(
        taxa_media_vitoria=("win_rate", "mean"),
        qtd_pokemons=("name", "nunique"),
    )
    return grouped.sort_values("taxa_media_vitoria", ascending=False, ignore_index=True)


def build_winrate_with_attrs(
    combats: pd.DataFrame, pokemons: pd.DataFrame, attrs: Optional[pd.DataFrame], min_battles: int = 5
) -> pd.DataFrame:
    wr = compute_winrate(combats, min_battles=min_battles)
    if attrs is None or attrs.empty:
        return wr
    wr_id = wr.merge(pokemons, on="name", how="left")  # adiciona id
    merged = wr_id.merge(attrs, on="id", how="left")
    return merged


def compute_numeric_correlations(wr_attrs: pd.DataFrame) -> pd.DataFrame:
    """Retorna correlações Pearson entre colunas numéricas de atributos e win_rate."""
    if wr_attrs is None or wr_attrs.empty or "win_rate" not in wr_attrs.columns:
        return pd.DataFrame(columns=["attribute", "corr"])
    numeric_cols = wr_attrs.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ("id", "wins", "losses", "total")]
    out = []
    for col in numeric_cols:
        try:
            corr = wr_attrs["win_rate"].corr(wr_attrs[col])
        except Exception:
            corr = np.nan
        if pd.notna(corr):
            out.append({"attribute": col, "corr": float(corr)})
    return pd.DataFrame(out).sort_values("corr", ascending=False, ignore_index=True)


def compute_feature_importance(wr_attrs: pd.DataFrame, max_features: int = 12) -> pd.DataFrame:
    """Treina um RandomForestRegressor simples para estimar importâncias de atributos numéricos."""
    if wr_attrs is None or wr_attrs.empty or "win_rate" not in wr_attrs.columns:
        return pd.DataFrame(columns=["attribute", "importance"])
    numeric_cols = wr_attrs.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c not in ("id", "wins", "losses", "total", "win_rate")]
    feature_cols = feature_cols[:max_features]
    if not feature_cols:
        return pd.DataFrame(columns=["attribute", "importance"])
    X = wr_attrs[feature_cols].fillna(0.0).values
    y = wr_attrs["win_rate"].values
    try:
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(X, y)
        imp = model.feature_importances_
        df = pd.DataFrame({"attribute": feature_cols, "importance": imp})
        return df.sort_values("importance", ascending=False, ignore_index=True)
    except Exception:
        return pd.DataFrame(columns=["attribute", "importance"])


def suggest_team(wr_attrs: pd.DataFrame, team_size: int = 6) -> pd.DataFrame:
    """Sugestão heurística de time: pega top por win_rate com diversidade de tipos (quando disponíveis)."""
    if wr_attrs is None or wr_attrs.empty:
        return pd.DataFrame(columns=["name", "win_rate"])  # vazio

    # Extrai tipos se existirem
    types_df = None
    if "types" in wr_attrs.columns:
        types_df = wr_attrs[["id", "types"]].copy()
    # cria cópia e ordena por win_rate/total
    df = wr_attrs.copy()
    if "total" in df.columns:
        df = df.sort_values(["win_rate", "total"], ascending=[False, False])
    else:
        df = df.sort_values(["win_rate"], ascending=[False])

    chosen = []
    seen_types = set()
    for _, row in df.iterrows():
        if len(chosen) >= team_size:
            break
        pid = row.get("id")
        name = row.get("name")
        # diversidade de tipos se possível
        add_ok = True
        if types_df is not None and pid in types_df.get("id", []):
            # tentativa simples: se todos os tipos do pokémon já estiverem no set, tenta pular
            tval = row.get("types")
            if isinstance(tval, str):
                tset = {t.strip() for t in tval.split(",") if t.strip()}
            elif isinstance(tval, list):
                tset = set(tval)
            else:
                tset = set()
            if tset and tset.issubset(seen_types):
                add_ok = False
            else:
                seen_types.update(tset)
        if add_ok:
            chosen.append({"name": name, "win_rate": row.get("win_rate")})

    return pd.DataFrame(chosen)


# ---------------------
# Head-to-Head (A x B)
# ---------------------

def compute_h2h(combats: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Matriz de vitórias do A (linhas) sobre B (colunas) para os Top N por participações."""
    # Top N por participação total
    first_counts = combats["first_pokemon"].value_counts()
    second_counts = combats["second_pokemon"].value_counts()
    total = (first_counts.add(second_counts, fill_value=0)).sort_values(ascending=False)
    top = set(total.head(top_n).index.tolist())

    # Constrói pares (winner, loser) por combate
    rows = []
    for _, row in combats.iterrows():
        w = row["winner"]
        a = row["first_pokemon"]
        b = row["second_pokemon"]
        loser = b if w == a else a
        rows.append((w, loser))

    df_pairs = pd.DataFrame(rows, columns=["winner", "loser"])
    df_pairs = df_pairs[df_pairs["winner"].isin(top) & df_pairs["loser"].isin(top)]

    # Pivot (contagem) e ordenação consistente
    pivot = pd.pivot_table(
        df_pairs, index="winner", columns="loser", values="loser", aggfunc="count", fill_value=0
    )
    ordered = sorted(top)
    pivot = pivot.reindex(index=ordered, columns=ordered, fill_value=0)
    for n in pivot.index:
        if n in pivot.columns:
            pivot.loc[n, n] = 0
    return pivot
