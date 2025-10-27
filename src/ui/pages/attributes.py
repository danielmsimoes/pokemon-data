"""Página: Atributos e Desempenho.

Inclui: Mapa de calor (médias por tipo), Radar (comparar tipos) e
dispersão Atributo x Taxa de Vitória.
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
from src.analysis.metrics import build_winrate_with_attrs


def render() -> None:
    st.header("Atributos e Desempenho")
    pokemons, combats, attrs = load_all()
    if attrs is None or getattr(attrs, "empty", True):
        st.info("Arquivo de atributos não encontrado. Rode o ETL para gerar 'data/pokemon_attributes.csv'.")
        return
    attrs = _ensure_overall(attrs)

    wr_attrs = build_winrate_with_attrs(combats, pokemons, attrs, min_battles=5)
    if wr_attrs.empty:
        st.warning("Não foi possível unir atributos com taxa de vitória.")
        return

    # Garantir nome e tipo principal
    if "name" not in wr_attrs.columns:
        wr_attrs["name"] = wr_attrs.get("name_x", wr_attrs.get("name_y"))
    stats = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
    if "types" in wr_attrs.columns:
        wr_attrs["primary_type_en"] = wr_attrs["types"].apply(lambda s: next((x for x in _parse_types(s) if x in OFFICIAL_TYPES_EN), None))
    else:
        wr_attrs["primary_type_en"] = None

    tabs = st.tabs(["Mapa de Calor (médias)", "Radar (comparar tipos)", "Atributo x Taxa de Vitória"])

    # 1) Mapa de calor
    with tabs[0]:
        tmp = wr_attrs.dropna(subset=["primary_type_en"]).copy()
        if tmp.empty:
            st.info("Sem dados de tipos para montar o mapa de calor.")
        else:
            means = tmp.groupby("primary_type_en")[stats].mean().reindex(OFFICIAL_TYPES_EN)
            fig_hm = px.imshow(
                means,
                labels=dict(x="Atributo", y="Tipo", color="Média"),
                x=stats,
                y=OFFICIAL_TYPES_EN,
                color_continuous_scale="YlGnBu",
                aspect="auto",
            )
            fig_hm.update_layout(height=500, transition_duration=500)
            st.plotly_chart(fig_hm, use_container_width=True)

    # 2) Radar
    with tabs[1]:
        tmp = wr_attrs.dropna(subset=["primary_type_en"]).copy()
        if tmp.empty:
            st.info("Sem dados de tipos para montar o radar.")
        else:
            options = OFFICIAL_TYPES_EN
            chosen = st.multiselect("Selecione até 3 tipos", options=options, default=options[:2], max_selections=3)
            if not chosen:
                st.info("Selecione ao menos um tipo.")
            else:
                means = tmp.groupby("primary_type_en")[stats].mean()
                tidy = (
                    means.loc[means.index.intersection(chosen)]
                    .reset_index()
                    .melt(id_vars="primary_type_en", var_name="Atributo", value_name="Valor")
                    .rename(columns={"primary_type_en": "Tipo"})
                )
                fig_radar = px.line_polar(
                    tidy,
                    r="Valor",
                    theta="Atributo",
                    color="Tipo",
                    line_close=True,
                    color_discrete_map=TYPE_COLORS_EN,
                )
                fig_radar.update_traces(fill="toself", opacity=0.6)
                fig_radar.update_layout(transition_duration=500, showlegend=True, polar=dict(radialaxis=dict(visible=True)))
                st.plotly_chart(fig_radar, use_container_width=True)

    # 3) Dispersão atributo x taxa de vitória
    with tabs[2]:
        attr_options = stats + (["overall"] if "overall" in wr_attrs.columns else [])
        chosen_attr = st.selectbox("Escolha o atributo", options=attr_options, index=min(6, len(attr_options) - 1))
        df = wr_attrs.dropna(subset=[chosen_attr]).copy()
        if df.empty:
            st.info("Sem valores para o atributo selecionado.")
        else:
            df["win_rate_pct"] = df["win_rate"] * 100
            fig_scatter = px.scatter(
                df,
                x=chosen_attr,
                y="win_rate_pct",
                color="primary_type_en",
                color_discrete_map=TYPE_COLORS_EN,
                hover_data=["name", chosen_attr, "win_rate_pct"],
                title=f"{chosen_attr.capitalize()} x Taxa de Vitória (%)",
            )
            fig_scatter.update_layout(xaxis_title=chosen_attr.capitalize(), yaxis_title="Taxa de Vitória (%)", transition_duration=500)
            st.plotly_chart(fig_scatter, use_container_width=True)
