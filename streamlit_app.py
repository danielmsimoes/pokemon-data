import streamlit as st
import pandas as pd
import plotly.express as px

from src.analysis.metrics import (
    load_data,
    compute_participations,
    compute_winrate,
    build_winrate_with_attrs,
)


@st.cache_data(show_spinner=False)
def load_all(data_dir: str = "data"):
    return load_data(data_dir)


def _parse_types(val):
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()]
    if isinstance(val, list):
        return [str(x) for x in val]
    return []


def _ensure_overall(attrs: pd.DataFrame) -> pd.DataFrame:
    df = attrs.copy()
    stats = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
    for col in stats:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "overall" not in df.columns and all(c in df.columns for c in stats):
        df["overall"] = df["hp"] + df["attack"] + df["defense"] + df["sp_attack"] + df["sp_defense"] + df["speed"]
    return df


def show_overview():
    st.title("Visão Geral")
    pokemons, combats, attrs = load_all()
    st.write(f"Pokémons: {len(pokemons)} | Combates: {len(combats)}")

    st.subheader("Amostra de Pokémons")
    if not pokemons.empty:
        cols = [c for c in pokemons.columns if c in ("id", "name", "types", "generation")]
        sample_p = pokemons[cols].head(20).copy()
        column_order = ["id"] + [c for c in sample_p.columns if c != "id"]
        st.dataframe(sample_p, use_container_width=True, hide_index=True, column_order=column_order)
        csv_p = pokemons.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button("Baixar Pokémons (CSV)", data=csv_p, file_name="pokemons.csv", mime="text/csv")

    st.subheader("Amostra de Combates")
    if not combats.empty:
        disp_cols = [c for c in combats.columns if c in ("first_pokemon", "second_pokemon", "winner")]
        sample_c = combats[disp_cols].head(20).copy()

        def highlight_winner(row):
            s = [""] * len(row)
            try:
                cols = list(sample_c.columns)
                fp, sp, w = row["first_pokemon"], row["second_pokemon"], row["winner"]
                if fp == w:
                    s[cols.index("first_pokemon")] = "background-color: #d4edda; color: #155724; font-weight: 700;"
                if sp == w:
                    s[cols.index("second_pokemon")] = "background-color: #d4edda; color: #155724; font-weight: 700;"
                s[cols.index("winner")] = "color: #155724; font-weight: 700;"
            except Exception:
                pass
            return s

        styled_c = sample_c.style.apply(highlight_winner, axis=1)
        st.dataframe(styled_c, use_container_width=True, hide_index=True)
        csv_c = combats.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button("Baixar Combates (CSV)", data=csv_c, file_name="combats.csv", mime="text/csv")


def show_participations():
    st.header("Nº de Participações em Combates")
    _, combats, _ = load_all()
    part = compute_participations(combats)
    modo = st.selectbox("Visualizar", ["Mais participações", "Menos participações"], index=0)
    qtd = st.sidebar.number_input("Quantidade exibida", min_value=5, max_value=100, value=20, step=5)
    df_show = part.sort_values("participations", ascending=(modo == "Menos participações")).head(qtd)
    fig = px.bar(df_show, x="name", y="participations", title="Nº de Participações em Combates", color="participations",
                 color_continuous_scale="Blues")
    fig.update_layout(xaxis_title="Pokémon", yaxis_title="Participações", xaxis_tickangle=-45, transition_duration=500)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_show, use_container_width=True, hide_index=True)


def show_winrate():
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

    fig = px.bar(data_view, x="name", y=y_col, hover_data=["wins", "losses", "total"], title=chart_title)
    fig.update_layout(xaxis_title="Pokémon", yaxis_title=("Derrotas" if y_col == "losses" else "Taxa de Vitória"), xaxis_tickangle=-45, transition_duration=500)
    st.plotly_chart(fig, use_container_width=True)

    tbl = data_view.rename(columns={
        "name": "Nome",
        "wins": "Vitórias",
        "losses": "Derrotas",
        "total": "Total",
        "win_rate": "Taxa de Vitória (%)",
    }).copy()
    if "Taxa de Vitória (%)" in tbl.columns:
        tbl["Taxa de Vitória (%)"] = (tbl["Taxa de Vitória (%)"] * 100).map(lambda v: f"{v:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."))
    st.dataframe(tbl, use_container_width=True, hide_index=True)


def show_types():
    st.header("Informações por Tipo")
    pokemons, combats, attrs = load_all()
    if attrs is None or attrs.empty:
        st.info("Arquivo de atributos não encontrado. Rode o ETL para gerar 'data/pokemon_attributes.csv'.")
        return

    wr = compute_winrate(combats, min_battles=1)
    attrs = _ensure_overall(attrs)

    # Explode tipos para os 18 oficiais (cada Pokémon contribui uma vez por tipo que possui)
    wr_id = wr.merge(pokemons, on="name", how="left")
    types_df = attrs[["id", "types"]].copy()
    types_df["types_list"] = types_df["types"].apply(_parse_types)
    types_exploded = types_df.explode("types_list").dropna(subset=["types_list"]).rename(columns={"types_list": "type_en"})
    official_en = [
        "Normal","Fire","Water","Grass","Flying","Fighting","Poison","Electric","Ground",
        "Rock","Psychic","Ice","Bug","Ghost","Steel","Dragon","Dark","Fairy"
    ]
    types_exploded = types_exploded[types_exploded["type_en"].isin(official_en)].copy()

    type_pt = {
        "Water": "Água", "Fire": "Fogo", "Grass": "Planta", "Electric": "Elétrico",
        "Psychic": "Psíquico", "Ice": "Gelo", "Fighting": "Lutador", "Poison": "Venenoso",
        "Ground": "Terrestre", "Flying": "Voador", "Bug": "Inseto", "Rock": "Rocha",
        "Ghost": "Fantasma", "Dragon": "Dragão", "Dark": "Sombrio", "Steel": "Aço",
        "Fairy": "Fada", "Normal": "Normal",
    }
    color_map = {
        "Água": "#1E90FF", "Fogo": "#FF4500", "Planta": "#2E8B57", "Elétrico": "#FFD700",
        "Psíquico": "#EE82EE", "Gelo": "#00CED1", "Lutador": "#CD5C5C", "Venenoso": "#8A2BE2",
        "Terrestre": "#DEB887", "Voador": "#87CEEB", "Inseto": "#9ACD32", "Rocha": "#A0522D",
        "Fantasma": "#6A5ACD", "Dragão": "#FF8C00", "Sombrio": "#2F4F4F", "Aço": "#708090",
        "Fada": "#FF69B4", "Normal": "#A8A77A",
    }

    types_exploded["Tipo"] = types_exploded["type_en"].map(type_pt)
    wr_types = wr_id.merge(types_exploded[["id", "Tipo"]], on="id", how="inner")
    if wr_types.empty:
        st.warning("Não foi possível calcular taxa por tipo.")
    else:
        agg = (
            wr_types.groupby("Tipo", as_index=False)
            .agg(taxa_vitoria=("win_rate", "mean"))
            .sort_values("taxa_vitoria", ascending=False)
        )
        agg["Taxa de Vitória (%)"] = (agg["taxa_vitoria"] * 100).round(2)
        fig1 = px.bar(
            agg,
            y="Tipo",
            x="Taxa de Vitória (%)",
            color="Tipo",
            color_discrete_map=color_map,
            orientation="h",
            title="Taxa de Vitória por Tipo (18 tipos oficiais)",
            text="Taxa de Vitória (%)",
            height=500,
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(xaxis_title="Taxa de Vitória (%)", yaxis_title="Tipo", transition_duration=500)
        st.plotly_chart(fig1, use_container_width=True)

    # Detalhe: seleção de tipo (em inglês) e métrica
    official_en = [
        "Normal","Fire","Water","Grass","Flying","Fighting","Poison","Electric","Ground",
        "Rock","Psychic","Ice","Bug","Ghost","Steel","Dragon","Dark","Fairy"
    ]
    sel_type_en = st.selectbox("Select a type", options=official_en)
    metric = st.selectbox("Metric", options=["wins", "losses", "overall"], index=0)

    # Monta base com atributos (inclui 'overall') e filtra por tipo selecionado (em inglês)
    attrs_sel = _ensure_overall(attrs)
    wr_attrs = wr_id.merge(attrs_sel[["id", "types", "overall"]], on="id", how="left")
    mask = wr_attrs["types"].fillna("").apply(lambda s: sel_type_en in _parse_types(s))
    det = wr_attrs[mask].copy()
    if det.empty or metric not in det.columns:
        st.info("Sem dados para este tipo/métrica.")
    else:
        det = det[["name", metric]].sort_values(metric, ascending=False)
        fig2 = px.bar(det.head(30), y="name", x=metric, orientation="h", title=f"{sel_type_en} — by {metric}")
        fig2.update_layout(yaxis_title="Pokémon", xaxis_title=metric.capitalize(), transition_duration=500)
        st.plotly_chart(fig2, use_container_width=True)


def show_attributes_influence():
    st.header("Atributos x Taxa de Vitória")
    pokemons, combats, attrs = load_all()
    if attrs is None or attrs.empty:
        st.info("Arquivo de atributos não encontrado. Rode o ETL para gerar 'data/pokemon_attributes.csv'.")
        return
    attrs = _ensure_overall(attrs)
    wr_attrs = build_winrate_with_attrs(combats, pokemons, attrs, min_battles=5)
    if wr_attrs.empty:
        st.warning("Não foi possível unir atributos com taxa de vitória.")
        return
    if 'name' not in wr_attrs.columns:
        if 'name_x' in wr_attrs.columns:
            wr_attrs['name'] = wr_attrs['name_x']
        elif 'name_y' in wr_attrs.columns:
            wr_attrs['name'] = wr_attrs['name_y']

    stats = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
    official_en = [
        "Normal","Fire","Water","Grass","Flying","Fighting","Poison","Electric","Ground",
        "Rock","Psychic","Ice","Bug","Ghost","Steel","Dragon","Dark","Fairy"
    ]
    color_map_en = {
        "Water": "#1E90FF", "Fire": "#FF4500", "Grass": "#2E8B57", "Electric": "#FFD700",
        "Psychic": "#EE82EE", "Ice": "#00CED1", "Fighting": "#CD5C5C", "Poison": "#8A2BE2",
        "Ground": "#DEB887", "Flying": "#87CEEB", "Bug": "#9ACD32", "Rock": "#A0522D",
        "Ghost": "#6A5ACD", "Dragon": "#FF8C00", "Dark": "#2F4F4F", "Steel": "#708090",
        "Fairy": "#FF69B4", "Normal": "#A8A77A",
    }
    tabs = st.tabs(["Distribuição por Tipo (Radar)", "Atributo x Taxa de Vitória", "Ranking de Atributos (Tipos)"])

    # Radar por tipo
    with tabs[0]:
        if 'types' not in wr_attrs.columns:
            st.info("Coluna 'types' não disponível nos atributos.")
        else:
            tipos_all = sorted({t for lst in wr_attrs['types'].dropna().apply(_parse_types) for t in lst})
            tipos_unicos = [t for t in tipos_all if t in official_en]
            sel_tipo = st.selectbox("Select a type", options=tipos_unicos)
            subset = wr_attrs[wr_attrs['types'].fillna("").apply(lambda s: sel_tipo in _parse_types(s))]
            if subset.empty:
                st.info("Sem dados para este tipo.")
            else:
                mean_vals = subset[stats].mean().reset_index()
                mean_vals.columns = ['atributo', 'valor']
                fig_radar = px.line_polar(mean_vals, r='valor', theta='atributo', line_close=True, title=f"Perfil médio de atributos — {sel_tipo}")
                fig_radar.update_traces(fill='toself')
                st.plotly_chart(fig_radar, use_container_width=True)

    # Scatter atributo x taxa de vitória
    with tabs[1]:
        attr_options = stats + (["overall"] if "overall" in wr_attrs.columns else [])
        chosen_attr = st.selectbox("Escolha o atributo", options=attr_options, index=min(6, len(attr_options)-1))
        wr_attrs['win_rate_pct'] = wr_attrs['win_rate'] * 100
        # Define primary_type_en para cores (18 tipos)
        def first_official(t):
            lst = _parse_types(t)
            for x in lst:
                if x in official_en:
                    return x
            return None
        wr_attrs['primary_type_en'] = wr_attrs['types'].apply(first_official) if 'types' in wr_attrs.columns else None
        fig_scatter = px.scatter(
            wr_attrs,
            x=chosen_attr,
            y='win_rate_pct',
            color='primary_type_en',
            color_discrete_map=color_map_en,
            hover_data=['name', chosen_attr, 'win_rate_pct'],
            title=f"{chosen_attr.capitalize()} x Taxa de Vitória (%)",
        )
        fig_scatter.update_layout(xaxis_title=chosen_attr.capitalize(), yaxis_title="Taxa de Vitória (%)", transition_duration=500)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Ranking de atributos por tipo (média)
    with tabs[2]:
        attr_rank = st.selectbox("Atributo para ranking", options=stats + (["overall"] if "overall" in wr_attrs.columns else []), index=min(6, len(stats)))
        if 'types' not in wr_attrs.columns:
            st.info("Coluna 'types' não disponível nos atributos.")
        else:
            tmp = wr_attrs[['types', attr_rank]].dropna()
            tmp['types_list'] = tmp['types'].apply(_parse_types)
            tmp = tmp.explode('types_list')
            tmp = tmp[tmp['types_list'].isin(official_en)].rename(columns={'types_list': 'type'})
            rank_df = tmp.groupby('type', as_index=False)[attr_rank].mean().sort_values(attr_rank, ascending=False)
            fig_rank = px.bar(rank_df, y='type', x=attr_rank, orientation='h', title=f"Média de {attr_rank} por tipo", color='type', color_discrete_map=color_map_en)
            fig_rank.update_layout(yaxis_title="Tipo", xaxis_title=attr_rank.capitalize())
            st.plotly_chart(fig_rank, use_container_width=True)


def show_attribute_analytics():
    st.header("Análises Interativas de Atributos")
    pokemons, combats, attrs = load_all()
    if attrs is None or attrs.empty:
        st.info("Arquivo de atributos não encontrado. Rode o ETL para gerar 'data/pokemon_attributes.csv'.")
        return

    attrs_df = _ensure_overall(attrs)
    attrs_df = attrs_df.copy()
    attrs_df['primary_type'] = attrs_df['types'].apply(_parse_types).apply(lambda lst: lst[0] if lst else None)
    attr_options = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed", "overall"] if 'overall' in attrs_df.columns else ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]

    tab1, tab2 = st.tabs(["Top 10 Atributos", "Análise por Geração"])

    with tab1:
        st.subheader("Top 10 por Atributo")
        chosen_attr = st.selectbox("Escolha o atributo", options=attr_options, index=min(6, len(attr_options)-1))
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
            st.dataframe(top10, use_container_width=True, hide_index=True)
            title_map = {
                "hp": "Top 10 HP",
                "attack": "Top 10 Ataque",
                "defense": "Top 10 Defesa",
                "sp_attack": "Top 10 Ataque Especial",
                "sp_defense": "Top 10 Defesa Especial",
                "speed": "Top 10 Velocidade",
                "overall": "Top 10 Overall",
            }
            fig = px.bar(
                top10,
                y="name",
                x=chosen_attr,
                color="primary_type",
                orientation="h",
                title=title_map.get(chosen_attr, f"Top 10 {chosen_attr}"),
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
            chosen_attr2 = st.selectbox("Escolha o atributo", options=attr_options, index=min(6, len(attr_options)-1), key="attr_gen")
            cols_needed2 = ["id", "name", "primary_type", "generation", chosen_attr2]
            if all(c in attrs_df.columns for c in cols_needed2):
                subset = attrs_df[attrs_df["generation"] == gen]
                top10g = (
                    subset[["id", "name", "primary_type", chosen_attr2]]
                    .dropna(subset=[chosen_attr2])
                    .sort_values(by=chosen_attr2, ascending=False)
                    .head(10)
                )
                st.dataframe(top10g, use_container_width=True, hide_index=True)
                fig2 = px.bar(
                    top10g,
                    y="name",
                    x=chosen_attr2,
                    color="primary_type",
                    orientation="h",
                    title=f"Top 10 {chosen_attr2.capitalize()} — Geração {gen}",
                )
                fig2.update_layout(yaxis_title="Pokémon", xaxis_title=chosen_attr2.capitalize())
                st.plotly_chart(fig2, use_container_width=True)
            else:
                missing2 = [c for c in cols_needed2 if c not in attrs_df.columns]
                st.warning(f"Colunas ausentes nos atributos: {missing2}")


def main():
    st.set_page_config(page_title="Pokémon Battles", layout="wide")
    st.sidebar.title("Navegação")
    page = st.sidebar.selectbox(
        "Ir para",
        [
            "Visão Geral",
            "Participações",
            "Taxa de Vitória",
            "Informações por Tipo",
            "Atributos vs Win Rate",
            "Análises Interativas de Atributos",
        ],
    )
    if page == "Visão Geral":
        show_overview()
    elif page == "Participações":
        show_participations()
    elif page == "Taxa de Vitória":
        show_winrate()
    elif page == "Informações por Tipo":
        show_types()
    elif page == "Atributos vs Win Rate":
        show_attributes_influence()
    else:
        show_attribute_analytics()


if __name__ == "__main__":
    main()
