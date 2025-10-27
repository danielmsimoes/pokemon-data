"""Página: Taxa de Vitória.

Ranking por taxa de vitória ou por derrotas, com tabela traduzida.
"""

import streamlit as st
import plotly.express as px

from src.ui.utils import load_all
from src.analysis.metrics import compute_winrate


def render() -> None:
    st.header("Taxa de Vitória")
    _, combats, _ = load_all()

    st.markdown("<div style='font-size:1.15rem; font-weight:700; margin-bottom:4px;'>Mostrar quem mais perdeu</div>", unsafe_allow_html=True)
    mostrar_derrotas = st.checkbox("Ativar", value=False)
    qtd = st.sidebar.number_input("Quantidade exibida", min_value=5, max_value=100, value=20, step=5)

    wr = compute_winrate(combats, min_battles=1)
    if mostrar_derrotas:
        data_view = wr.sort_values(["losses", "total"], ascending=[False, False]).head(qtd)
        chart_title = "Mais Derrotas"
        y_col = "losses"
    else:
        data_view = wr.sort_values(["win_rate", "total"], ascending=[False, False]).head(qtd)
        chart_title = "Maior Taxa de Vitória"
        y_col = "win_rate"

    fig = px.bar(
        data_view,
        x="name",
        y=y_col,
        hover_data=["wins", "losses", "total"],
        title=chart_title,
    )
    fig.update_layout(
        xaxis_title="Pokémon",
        yaxis_title=("Derrotas" if y_col == "losses" else "Taxa de Vitória"),
        xaxis_tickangle=-45,
        transition_duration=500,
    )
    st.plotly_chart(fig, use_container_width=True)

