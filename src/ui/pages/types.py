"""Página: Informações por Tipo.

Gráfico consolidado com os 18 tipos e detalhamento por tipo e métrica.
"""

import plotly.express as px
import streamlit as st

from src.ui.utils import (
    load_all,
    OFFICIAL_TYPES_EN,
    TYPE_COLORS_EN,
    parse_types as _parse_types,
    ensure_overall as _ensure_overall,
)
from src.analysis.metrics import compute_winrate


def render() -> None:
    st.header("Informações por Tipo")
    pokemons, combats, attrs = load_all()
    if attrs is None or attrs.empty:
        st.info("Arquivo de atributos não encontrado. Rode o ETL para gerar 'data/pokemon_attributes.csv'.")
        return
    attrs = _ensure_overall(attrs)

    wr = compute_winrate(combats, min_battles=1)
    wr_id = wr.merge(pokemons, on="name", how="left")

    types_df = attrs[["id", "types"]].copy()
    types_df["types_list"] = types_df["types"].apply(_parse_types)
    types_exploded = (
        types_df.explode("types_list")
        .dropna(subset=["types_list"])  # type: ignore[arg-type]
        .rename(columns={"types_list": "type_en"})
    )
    types_exploded = types_exploded[types_exploded["type_en"].isin(OFFICIAL_TYPES_EN)].copy()

    wr_types = wr_id.merge(types_exploded[["id", "type_en"]], on="id", how="inner")
    if wr_types.empty:
        st.warning("Não foi possível calcular taxa por tipo.")
    else:
        agg = (
            wr_types.groupby("type_en", as_index=False)
            .agg(taxa_vitoria=("win_rate", "mean"))
            .sort_values("taxa_vitoria", ascending=False)
        )
        agg["Taxa de Vitória (%)"] = (agg["taxa_vitoria"] * 100).round(2)
        fig1 = px.bar(
            agg,
            y="type_en",
            x="Taxa de Vitória (%)",
            color="type_en",
            orientation="h",
            title="Taxa de Vitória por Tipo (18 tipos oficiais)",
            color_discrete_map=TYPE_COLORS_EN,
            text="Taxa de Vitória (%)",
        )
        fig1.update_traces(textposition="outside", textfont_size=16)
        fig1.update_layout(xaxis_title="Taxa de Vitória (%)", yaxis_title="Tipo", transition_duration=500)
        st.plotly_chart(fig1, use_container_width=True)

    # Detalhe por tipo
    sel_type_en = st.selectbox("Selecione um tipo", options=OFFICIAL_TYPES_EN)
    metric_label = st.selectbox("Métrica", options=["Vitórias", "Derrotas", "Overall"], index=0)
    metric_map = {"Vitórias": "wins", "Derrotas": "losses", "Overall": "overall"}
    metric = metric_map[metric_label]

    wr_attrs = wr_id.merge(attrs[["id", "types", "overall"]], on="id", how="left")
    mask = wr_attrs["types"].fillna("").apply(lambda s: sel_type_en in _parse_types(s))
    det = wr_attrs[mask].copy()
    if det.empty or metric not in det.columns:
        st.info("Sem dados para este tipo/métrica.")
    else:
        det = det[["name", metric]].sort_values(metric, ascending=False)
        fig2 = px.bar(det.head(30), y="name", x=metric, orientation="h", title=f"{metric_label} do tipo {sel_type_en}")
        fig2.update_layout(yaxis_title="Pokémon", xaxis_title=metric_label, transition_duration=500)
        st.plotly_chart(fig2, use_container_width=True)
