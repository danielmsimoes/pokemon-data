"""Página: Visão Geral.

Mostra amostras de Pokémons e Combates, com destaque ao vencedor e
botões para baixar CSVs completos.
"""

import pandas as pd
import streamlit as st

from src.ui.utils import load_all


def render() -> None:
    st.title("Visão Geral")
    pokemons, combats, _ = load_all()
    st.write(f"Pokémons: {len(pokemons)} | Combates: {len(combats)}")

    st.subheader("Amostra de Pokémons")
    if not pokemons.empty:
        base_cols = [c for c in pokemons.columns if c in ("id", "name", "generation")]
        sample_p = pokemons[base_cols].head(20).copy()
        # Estilo: coluna id menor
        styler = sample_p.style.set_properties(subset=["id"], **{"width": "60px", "font-size": "0.9rem"})
        st.dataframe(styler, use_container_width=True, hide_index=True)
        csv_p = pokemons.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button("Baixar Pokémons (CSV)", data=csv_p, file_name="pokemons.csv", mime="text/csv")

    st.subheader("Amostra de Combates")
    if not combats.empty:
        disp_cols = [c for c in combats.columns if c in ("first_pokemon", "second_pokemon", "winner")]
        sample_c = combats[disp_cols].head(20).copy()

        def highlight_winner(row: pd.Series) -> list[str]:
            s = [""] * len(row)
            cols = list(sample_c.columns)
            fp, sp, w = row.get("first_pokemon"), row.get("second_pokemon"), row.get("winner")
            if fp == w:
                s[cols.index("first_pokemon")] = "background-color: #d4edda; color: #0f5132; font-weight: 700;"
            if sp == w:
                s[cols.index("second_pokemon")] = "background-color: #d4edda; color: #0f5132; font-weight: 700;"
            s[cols.index("winner")] = "color: #0f5132; font-weight: 700;"
            return s

        styled_c = sample_c.style.apply(highlight_winner, axis=1)
        st.dataframe(styled_c, use_container_width=True, hide_index=True)
        csv_c = combats.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button("Baixar Combates (CSV)", data=csv_c, file_name="combats.csv", mime="text/csv")

