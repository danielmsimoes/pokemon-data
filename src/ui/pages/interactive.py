"""Página: Análises Interativas de Atributos.

Top 10 por atributo e por geração, com botão para baixar CSV da geração.
"""

import plotly.express as px
import streamlit as st

from src.ui.utils import (
    load_all,
    TYPE_COLORS_EN,
    parse_types as _parse_types,
    ensure_overall as _ensure_overall,
)


def render() -> None:
    st.header("Análises Interativas de Atributos")
    _, _, attrs = load_all()
    if attrs is None or attrs.empty:
        st.info("Arquivo de atributos não encontrado. Rode o ETL para gerar 'data/pokemon_attributes.csv'.")
        return

    attrs_df = _ensure_overall(attrs).copy()
    attrs_df["primary_type"] = attrs_df["types"].apply(_parse_types).apply(lambda lst: lst[0] if lst else None)
    attr_options = [
        "hp",
        "attack",
        "defense",
        "sp_attack",
        "sp_defense",
        "speed",
        "overall",
    ] if "overall" in attrs_df.columns else [
        "hp",
        "attack",
        "defense",
        "sp_attack",
        "sp_defense",
        "speed",
    ]

    tab1, tab2 = st.tabs(["Top 10 Atributos", "Análise por Geração"])

    with tab1:
        st.subheader("Top 10 por Atributo")
        chosen_attr = st.selectbox("Escolha o atributo", options=attr_options, index=min(6, len(attr_options) - 1))
        cols_needed = ["id", "name", "primary_type", chosen_attr]
        if all(c in attrs_df.columns for c in cols_needed):
            top10 = (
                attrs_df[cols_needed]
                .dropna(subset=[chosen_attr])
                .sort_values(by=chosen_attr, ascending=False)
                .head(10)
            )
            if "overall" in attrs_df.columns and chosen_attr != "overall":
                extra = attrs_df[["id", "overall"]]
                top10 = top10.merge(extra, on="id", how="left")
            styler_top = top10.style.set_properties(subset=["id"], **{"width": "60px", "font-size": "0.9rem"})
            st.dataframe(styler_top, use_container_width=True, hide_index=True)
            fig = px.bar(
                top10,
                y="name",
                x=chosen_attr,
                color="primary_type",
                orientation="h",
                title=f"Top 10 {chosen_attr}",
                color_discrete_map=TYPE_COLORS_EN,
            )
            fig.update_layout(yaxis_title="Pokémon", xaxis_title=chosen_attr.capitalize())
            st.plotly_chart(fig, use_container_width=True)
        else:
            missing = [c for c in cols_needed if c not in attrs_df.columns]
            st.warning(f"Colunas ausentes nos atributos: {missing}")

    with tab2:
        st.subheader("Top 10 por Geração e Atributo")
        if "generation" not in attrs_df.columns:
            st.warning("Coluna 'generation' ausente nos atributos.")
        else:
            gens = sorted([g for g in attrs_df["generation"].dropna().unique().tolist()])
            gen = st.selectbox("Escolha a geração", options=gens)
            chosen_attr2 = st.selectbox("Escolha o atributo", options=attr_options, index=min(6, len(attr_options) - 1), key="attr_gen")
            cols_needed2 = ["id", "name", "primary_type", "generation", chosen_attr2]
            if all(c in attrs_df.columns for c in cols_needed2):
                subset = attrs_df[attrs_df["generation"] == gen]
                csv_gen = subset.to_csv(index=False, sep=';', encoding='utf-8-sig')
                st.download_button(
                    label=f"Baixar CSV da Geração {gen}",
                    data=csv_gen,
                    file_name=f"geracao_{gen}.csv",
                    mime="text/csv",
                )
                top10g = (
                    subset[["id", "name", "primary_type", chosen_attr2]]
                    .dropna(subset=[chosen_attr2])
                    .sort_values(by=chosen_attr2, ascending=False)
                    .head(10)
                )
                styler_topg = top10g.style.set_properties(subset=["id"], **{"width": "60px", "font-size": "0.9rem"})
                st.dataframe(styler_topg, use_container_width=True, hide_index=True)
                fig2 = px.bar(
                    top10g,
                    y="name",
                    x=chosen_attr2,
                    color="primary_type",
                    orientation="h",
                    title=f"Top 10 {chosen_attr2} - Geração {gen}",
                    color_discrete_map=TYPE_COLORS_EN,
                )
                fig2.update_layout(yaxis_title="Pokémon", xaxis_title=chosen_attr2.capitalize())
                st.plotly_chart(fig2, use_container_width=True)
            else:
                missing2 = [c for c in cols_needed2 if c not in attrs_df.columns]
                st.warning(f"Colunas ausentes nos atributos: {missing2}")

