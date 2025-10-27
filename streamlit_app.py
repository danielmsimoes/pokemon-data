"""Aplicativo Streamlit principal: roteador de páginas.

Este arquivo apenas configura a navegação e delega a renderização para
os módulos em `src/ui/pages/*`.
"""

import streamlit as st

from src.ui.pages import overview, participations, winrate, types, attributes, interactive


def main() -> None:
    st.set_page_config(page_title="Pokemon Battles", layout="wide")
    st.sidebar.title("Navegação")
    page = st.sidebar.selectbox(
        "Ir para",
        [
            "Visão Geral",
            "Participações",
            "Taxa de Vitória",
            "Informações por Tipo",
            "Atributos e Desempenho",
            "Análises Interativas de Atributos",
        ],
    )
    if page == "Visão Geral":
        overview.render()
    elif page == "Participações":
        participations.render()
    elif page == "Taxa de Vitória":
        winrate.render()
    elif page == "Informações por Tipo":
        types.render()
    elif page == "Atributos e Desempenho":
        attributes.render()
    else:
        interactive.render()


if __name__ == "__main__":
    main()

