import math
from pathlib import Path

import dash
from dash import Dash, Input, Output, State, dcc, html, dash_table
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


characters = read_csv("characters.csv")
encounters = read_csv("encounters.csv")
combat_events = read_csv("combat_events.csv")
abilities = read_csv("abilities.csv")
sessions = read_csv("sessions.csv")

combat_events["round"] = combat_events["round"].astype(int)
combat_events["damage"] = combat_events["damage"].astype(float)
combat_events["roll_total"] = combat_events["roll_total"].astype(float)
combat_events["target_ac"] = combat_events["target_ac"].astype(float)
combat_events["hit"] = combat_events["hit"].astype(int)
combat_events["critical"] = combat_events["critical"].astype(int)
combat_events["session_date"] = pd.to_datetime(combat_events["session_date"])
sessions["session_date"] = pd.to_datetime(sessions["session_date"])

external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap",
        "rel": "stylesheet",
    }
]

app: Dash = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config.suppress_callback_exceptions = True
server = app.server
app.title = "НРИ-Помощник (офлайн) - аналитика"


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text="Нет данных для отображения",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=16),
            )
        ],
        template="plotly_white",
    )
    return fig


def filter_events(role: str | None, encounter_id: str | None, damage_type: str | None) -> pd.DataFrame:
    df = combat_events.copy()
    if role and role != "Все":
        heroes = set(characters.loc[characters["role"] == role, "character_name"])
        df = df[df["actor_name"].isin(heroes)]
    if encounter_id and encounter_id != "Все":
        df = df[df["encounter_id"] == encounter_id]
    if damage_type and damage_type != "Все":
        df = df[df["damage_type"] == damage_type]
    return df


app.layout = html.Div([
    html.Div([
        html.Div([
            html.Div("🎲", className="header-badge"),
            html.H1("НРИ-Помощник (офлайн)", className="header-title"),
            html.P(
                "Аналитический дашборд по боевым сценам, персонажам, игровым сессиям и игровым механикам",
                className="header-subtitle",
            ),
        ], className="header-content")
    ], className="header"),
    html.Div([
        dcc.Tabs(id="tabs", value="tab-dashboard", children=[
            dcc.Tab(label="📊 Дашборд", value="tab-dashboard"),
            dcc.Tab(label="🧙 Персонажи", value="tab-characters"),
            dcc.Tab(label="⚔️ Боевые события", value="tab-combat"),
            dcc.Tab(label="✨ Способности", value="tab-abilities"),
            dcc.Tab(label="🗂 Сессии", value="tab-sessions"),
            dcc.Tab(label="📈 Аналитика", value="tab-analytics"),
        ])
    ], className="tabs-container"),
    html.Div(id="tab-content", className="content"),
    html.Div([
        html.P("© 2026 НРИ-Помощник (офлайн). Локальное веб-приложение для анализа игровых данных."),
        html.P("Версия 1.0.0 | Анализ боев, персонажей и игровых сессий"),
    ], className="footer"),
])


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab: str):
    if tab == "tab-dashboard":
        return render_dashboard_tab()
    if tab == "tab-characters":
        return render_characters_tab()
    if tab == "tab-combat":
        return render_combat_tab()
    if tab == "tab-abilities":
        return render_abilities_tab()
    if tab == "tab-sessions":
        return render_sessions_tab()
    if tab == "tab-analytics":
        return render_analytics_tab()
    return html.Div()



def render_dashboard_tab():
    roles = ["Все"] + sorted(characters["role"].unique().tolist())
    encounter_opts = ["Все"] + sorted(encounters["encounter_id"].unique().tolist())
    damage_types = ["Все"] + sorted(combat_events["damage_type"].unique().tolist())

    return html.Div([
        html.H2("Панель управления боевой аналитикой"),
        html.Div([
            html.Div([
                html.Label("Роль персонажа:"),
                dcc.Dropdown(id="dashboard-role", options=[{"label": x, "value": x} for x in roles], value="Все"),
            ], className="filter-item"),
            html.Div([
                html.Label("Столкновение:"),
                dcc.Dropdown(id="dashboard-encounter", options=[{"label": x, "value": x} for x in encounter_opts], value="Все"),
            ], className="filter-item"),
            html.Div([
                html.Label("Тип урона:"),
                dcc.Dropdown(id="dashboard-damage-type", options=[{"label": x, "value": x} for x in damage_types], value="Все"),
            ], className="filter-item"),
        ], className="filters-row"),
        html.Div([
            html.Div([html.H3("Всего событий"), html.P(id="metric-events", className="metric-value"), html.P("боевых записей", className="metric-label")], className="metric-card"),
            html.Div([html.H3("Попадания"), html.P(id="metric-hit-rate", className="metric-value"), html.P("доля успешных атак", className="metric-label")], className="metric-card"),
            html.Div([html.H3("Средний урон"), html.P(id="metric-avg-damage", className="metric-value"), html.P("за событие", className="metric-label")], className="metric-card"),
            html.Div([html.H3("Критические успехи"), html.P(id="metric-crits", className="metric-value"), html.P("критов в выборке", className="metric-label")], className="metric-card"),
        ], className="metrics-row"),
        html.Div([
            html.Div([dcc.Graph(id="dashboard-damage-by-character")], className="chart-card"),
            html.Div([dcc.Graph(id="dashboard-round-dynamics")], className="chart-card"),
        ], className="charts-row"),
        html.Div([
            html.Div([dcc.Graph(id="dashboard-damage-pie")], className="chart-card"),
            html.Div([dcc.Graph(id="dashboard-hit-heatmap")], className="chart-card"),
        ], className="charts-row"),
    ])



def render_characters_tab():
    return html.Div([
        html.H2("Справочник персонажей и NPC"),
        html.Div([
            html.Div([
                html.H3("Ключевые показатели"),
                html.Div([
                    html.Div([html.H4("Персонажей"), html.P(str(len(characters)), className="metric-value")], className="metric-card-small"),
                    html.Div([html.H4("Игроков"), html.P(str((characters["alignment"] == "Player").sum()), className="metric-value")], className="metric-card-small"),
                    html.Div([html.H4("NPC"), html.P(str((characters["alignment"] == "NPC").sum()), className="metric-value")], className="metric-card-small"),
                    html.Div([html.H4("Средний AC"), html.P(f"{characters['armor_class'].mean():.1f}", className="metric-value")], className="metric-card-small"),
                ], className="metrics-row-small"),
                dcc.Graph(
                    figure=px.scatter(
                        characters,
                        x="armor_class",
                        y="max_hp",
                        size="initiative_mod",
                        color="role",
                        hover_name="character_name",
                        title="Соотношение защиты и здоровья персонажей",
                        labels={"armor_class": "Класс защиты", "max_hp": "Максимальное здоровье", "initiative_mod": "Инициатива"},
                    ).update_layout(template="plotly_white")
                ),
            ], className="chart-card"),
            html.Div([
                html.H3("Таблица персонажей"),
                dash_table.DataTable(
                    data=characters.to_dict("records"),
                    columns=[{"name": col, "id": col} for col in characters.columns],
                    page_size=10,
                    sort_action="native",
                    filter_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "left", "padding": "10px"},
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                ),
            ], className="chart-card"),
        ], className="charts-row"),
    ])



def render_combat_tab():
    encounter_opts = sorted(encounters["encounter_id"].unique().tolist())
    return html.Div([
        html.H2("Журнал боевых событий"),
        html.Div([
            html.Div([
                html.Label("Столкновение:"),
                dcc.Dropdown(id="combat-encounter", options=[{"label": x, "value": x} for x in encounter_opts], value=encounter_opts[0]),
            ], className="filter-item"),
            html.Div([
                html.Label("Минимальный раунд:"),
                dcc.Slider(id="combat-min-round", min=1, max=int(combat_events["round"].max()), step=1, value=1,
                           marks={i: str(i) for i in sorted(combat_events["round"].unique())}),
            ], className="filter-item"),
        ], className="filters-row"),
        html.Div([
            html.Div([dcc.Graph(id="combat-timeline")], className="chart-card"),
            html.Div([
                html.H3("Детализация журнала"),
                dash_table.DataTable(
                    id="combat-table",
                    page_size=12,
                    sort_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "left", "padding": "10px"},
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                ),
            ], className="chart-card"),
        ], className="charts-row"),
    ])



def render_abilities_tab():
    merged = abilities.merge(characters[["character_name", "role"]], on="character_name", how="left")
    return html.Div([
        html.H2("Каталог способностей и игровых механик"),
        html.Div([
            html.Div([
                dcc.Graph(
                    figure=px.bar(
                        merged.groupby(["role", "resource_type"], as_index=False)["uses_per_session"].sum(),
                        x="role",
                        y="uses_per_session",
                        color="resource_type",
                        barmode="group",
                        title="Использование ресурсов по ролям персонажей",
                        labels={"role": "Роль", "uses_per_session": "Использований за сессию", "resource_type": "Ресурс"},
                    ).update_layout(template="plotly_white")
                )
            ], className="chart-card"),
            html.Div([
                dcc.Graph(
                    figure=px.sunburst(
                        merged,
                        path=["role", "resource_type", "ability_name"],
                        values="base_power",
                        title="Иерархия способностей и их базовой силы",
                    ).update_layout(template="plotly_white")
                )
            ], className="chart-card"),
        ], className="charts-row"),
        html.Div([
            html.H3("Таблица способностей"),
            dash_table.DataTable(
                data=abilities.to_dict("records"),
                columns=[{"name": col, "id": col} for col in abilities.columns],
                page_size=10,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "10px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            ),
        ], className="chart-card"),
    ])



def render_sessions_tab():
    return html.Div([
        html.H2("Игровые сессии и кампании"),
        html.Div([
            html.Div([
                dcc.Graph(
                    figure=px.line(
                        sessions.sort_values("session_date"),
                        x="session_date",
                        y="session_duration_hours",
                        color="campaign_name",
                        markers=True,
                        title="Длительность игровых сессий по датам",
                        labels={"session_date": "Дата", "session_duration_hours": "Длительность, ч", "campaign_name": "Кампания"},
                    ).update_layout(template="plotly_white")
                )
            ], className="chart-card"),
            html.Div([
                dcc.Graph(
                    figure=px.bar(
                        sessions,
                        x="session_code",
                        y="notes_count",
                        color="encounters_count",
                        title="Объём заметок и число столкновений по сессиям",
                        labels={"session_code": "Сессия", "notes_count": "Количество заметок", "encounters_count": "Столкновений"},
                    ).update_layout(template="plotly_white")
                )
            ], className="chart-card"),
        ], className="charts-row"),
        html.Div([
            html.H3("Таблица сессий"),
            dash_table.DataTable(
                data=sessions.assign(session_date=sessions["session_date"].dt.strftime("%Y-%m-%d")).to_dict("records"),
                columns=[{"name": col, "id": col} for col in sessions.columns],
                page_size=10,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "10px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            ),
        ], className="chart-card"),
    ])



def render_analytics_tab():
    return html.Div([
        html.H2("Сводная аналитика игровых данных"),
        html.Div([
            html.Div([
                html.Label("Показатель:"),
                dcc.Dropdown(
                    id="analytics-mode",
                    options=[
                        {"label": "Эффективность попаданий", "value": "accuracy"},
                        {"label": "Интенсивность урона", "value": "damage"},
                        {"label": "Критические успехи", "value": "critical"},
                    ],
                    value="accuracy",
                )
            ], className="filter-item", style={"maxWidth": "320px"}),
        ], className="filters-row"),
        html.Div([
            html.Div([dcc.Graph(id="analytics-main")], className="chart-card"),
            html.Div([dcc.Graph(id="analytics-secondary")], className="chart-card"),
        ], className="charts-row"),
        html.Div([
            html.H3("Справка"),
            html.Div(id="analytics-text", className="results-box"),
        ], className="chart-card"),
    ])


@app.callback(
    Output("metric-events", "children"),
    Output("metric-hit-rate", "children"),
    Output("metric-avg-damage", "children"),
    Output("metric-crits", "children"),
    Output("dashboard-damage-by-character", "figure"),
    Output("dashboard-round-dynamics", "figure"),
    Output("dashboard-damage-pie", "figure"),
    Output("dashboard-hit-heatmap", "figure"),
    Input("dashboard-role", "value"),
    Input("dashboard-encounter", "value"),
    Input("dashboard-damage-type", "value"),
)
def update_dashboard(role: str, encounter_id: str, damage_type: str):
    df = filter_events(role, encounter_id, damage_type)
    if df.empty:
        return "0", "0%", "0", "0", empty_figure("Урон по персонажам"), empty_figure("Динамика по раундам"), empty_figure("Типы урона"), empty_figure("Тепловая карта попаданий")

    total_events = len(df)
    hit_rate = f"{(df['hit'].mean() * 100):.1f}%"
    avg_damage = f"{df['damage'].mean():.1f}"
    crits = str(int(df['critical'].sum()))

    by_character = df.groupby("actor_name", as_index=False)["damage"].sum().sort_values("damage", ascending=False)
    fig_character = px.bar(by_character, x="actor_name", y="damage", color="damage", title="Суммарный урон по активным персонажам", labels={"actor_name": "Персонаж", "damage": "Урон"})
    fig_character.update_layout(template="plotly_white", coloraxis_showscale=False)

    by_round = df.groupby("round", as_index=False)["damage"].sum()
    fig_round = px.line(by_round, x="round", y="damage", markers=True, title="Динамика нанесённого урона по раундам", labels={"round": "Раунд", "damage": "Урон"})
    fig_round.update_layout(template="plotly_white")

    by_type = df.groupby("damage_type", as_index=False)["damage"].sum()
    fig_type = px.pie(by_type, values="damage", names="damage_type", title="Структура урона по типам")
    fig_type.update_layout(template="plotly_white")

    heatmap = df.pivot_table(index="actor_name", columns="round", values="hit", aggfunc="mean", fill_value=0)
    fig_heatmap = px.imshow(heatmap, aspect="auto", title="Вероятность попаданий по раундам", labels={"x": "Раунд", "y": "Персонаж", "color": "Доля попаданий"})
    fig_heatmap.update_layout(template="plotly_white")

    return total_events, hit_rate, avg_damage, crits, fig_character, fig_round, fig_type, fig_heatmap


@app.callback(
    Output("combat-table", "data"),
    Output("combat-table", "columns"),
    Output("combat-timeline", "figure"),
    Input("combat-encounter", "value"),
    Input("combat-min-round", "value"),
)
def update_combat(encounter_id: str, min_round: int):
    df = combat_events[(combat_events["encounter_id"] == encounter_id) & (combat_events["round"] >= min_round)].copy()
    if df.empty:
        return [], [], empty_figure("Хронология столкновения")

    df["event_label"] = df.apply(lambda row: f"{row['actor_name']} → {row['target_name']}", axis=1)
    fig = px.scatter(
        df,
        x="round",
        y="damage",
        size="roll_total",
        color="damage_type",
        symbol="hit",
        hover_name="event_label",
        title=f"Хронология столкновения {encounter_id}",
        labels={"round": "Раунд", "damage": "Урон", "roll_total": "Итог броска", "damage_type": "Тип урона", "hit": "Попадание"},
    )
    fig.update_layout(template="plotly_white")

    view = df[["session_code", "round", "actor_name", "target_name", "ability_name", "damage_type", "damage", "roll_total", "target_ac", "hit", "critical"]].copy()
    view["hit"] = view["hit"].map({1: "Да", 0: "Нет"})
    view["critical"] = view["critical"].map({1: "Да", 0: "Нет"})
    columns = [{"name": c, "id": c} for c in view.columns]
    return view.to_dict("records"), columns, fig


@app.callback(
    Output("analytics-main", "figure"),
    Output("analytics-secondary", "figure"),
    Output("analytics-text", "children"),
    Input("analytics-mode", "value"),
)
def update_analytics(mode: str):
    merged = combat_events.merge(characters[["character_name", "role"]], left_on="actor_name", right_on="character_name", how="left")
    if merged.empty:
        return empty_figure("Сводный график"), empty_figure("Дополнительный график"), "Недостаточно данных для отображения."

    if mode == "accuracy":
        accuracy = merged.groupby("actor_name", as_index=False)["hit"].mean().sort_values("hit", ascending=False)
        fig_main = px.bar(accuracy, x="actor_name", y="hit", color="hit", title="Точность атак по персонажам", labels={"actor_name": "Персонаж", "hit": "Доля попаданий"})
        fig_secondary = px.box(merged, x="role", y="roll_total", color="role", title="Распределение итоговых бросков по ролям", labels={"role": "Роль", "roll_total": "Итог броска"})
        best = accuracy.iloc[0]
        text = f"Наиболее высокая точность наблюдается у персонажа {best['actor_name']}: средняя доля успешных атак составляет {best['hit'] * 100:.1f}%. Показатель отражает устойчивую частоту успешных атак в текущем наборе данных."
    elif mode == "damage":
        damage = merged.groupby(["session_code", "actor_name"], as_index=False)["damage"].sum()
        fig_main = px.line(damage, x="session_code", y="damage", color="actor_name", markers=True, title="Интенсивность урона по сессиям", labels={"session_code": "Сессия", "damage": "Урон", "actor_name": "Персонаж"})
        role_damage = merged.groupby("role", as_index=False)["damage"].mean()
        fig_secondary = px.bar(role_damage, x="role", y="damage", color="role", title="Средний урон по ролям", labels={"role": "Роль", "damage": "Средний урон"})
        peak = damage.sort_values("damage", ascending=False).iloc[0]
        text = f"Максимальная интенсивность урона зафиксирована в сессии {peak['session_code']} у персонажа {peak['actor_name']}: {peak['damage']:.1f} ед. Показатель отражает наиболее насыщенный по урону эпизод в текущем наборе данных."
    else:
        crits = merged.groupby("actor_name", as_index=False)["critical"].sum().sort_values("critical", ascending=False)
        fig_main = px.bar(crits, x="actor_name", y="critical", color="critical", title="Количество критических успехов", labels={"actor_name": "Персонаж", "critical": "Критические успехи"})
        crit_by_type = merged.groupby("damage_type", as_index=False)["critical"].sum()
        fig_secondary = px.pie(crit_by_type, values="critical", names="damage_type", title="Критические успехи по типам урона")
        leader = crits.iloc[0]
        text = f"Наибольшее число критических успехов зафиксировано у персонажа {leader['actor_name']}: {int(leader['critical'])} случаев. Показатель отражает распределение критических результатов в текущем наборе данных."

    fig_main.update_layout(template="plotly_white")
    fig_secondary.update_layout(template="plotly_white")
    return fig_main, fig_secondary, text


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
