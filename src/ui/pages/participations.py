"""Página: Nº de Participações em Combates.

Mostra ranking de Pokémons com mais/menos participações e tabela.
"""

import streamlit as st
import plotly.express as px

from src.ui.utils import load_all
from src.analysis.metrics import compute_participations


def render() -> None:
    st.header("Nº de Participações em Combates")
    _, combats, _ = load_all()
    part = compute_participations(combats)
    modo = st.selectbox("Visualizar", ["Mais participações", "Menos participações"], index=0)
    qtd = st.sidebar.number_input("Quantidade exibida", min_value=5, max_value=100, value=20, step=5)
    df_show = part.sort_values("participations", ascending=(modo == "Menos participações")).head(qtd)

    fig = px.bar(
        df_show,
        x="name",
        y="participations",
        title="Nº de Participações em Combates",
        color="participations",
        color_continuous_scale="Blues",
        text='participations',
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(xaxis_title="Pokémon", yaxis_title="Participações", xaxis_tickangle=-45, transition_duration=500)
    st.plotly_chart(fig, use_container_width=True)

    tbl = df_show.rename(columns={"name": "Nome", "participations": "Participações"})
    st.dataframe(tbl, use_container_width=True, hide_index=True)

