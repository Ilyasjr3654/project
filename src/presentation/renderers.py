from typing import Callable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.models.result_presentation import ResultPresentation


def _next_chart_key() -> str:
    counter = st.session_state.get("_chart_render_count", 0) + 1
    st.session_state["_chart_render_count"] = counter
    return f"report_chart_{counter}"


def _format_integer(value) -> str:
    return f"{float(value):,.0f}".replace(",", " ")


def _format_decimal(value) -> str:
    return f"{float(value):,.2f}".replace(",", " ")


def _format_currency(value) -> str:
    return f"{_format_decimal(value)} MAD"


def _format_percentage(value) -> str:
    return f"{float(value):.2f} %"


NUMBER_FORMATTERS: dict[str, Callable] = {
    "integer": _format_integer,
    "decimal": _format_decimal,
    "currency": _format_currency,
    "percentage": _format_percentage,
    "none": str,
}


CHART_COLORS = [
    "#0B6B4F",
    "#3157A4",
    "#B66A15",
    "#7B4F9D",
    "#2F7D85",
    "#B23A48",
]


def _style_figure(figure: go.Figure) -> go.Figure:
    """Apply the same restrained visual language to every reporting chart."""

    figure.update_layout(
        colorway=CHART_COLORS,
        font={
            "family": "Segoe UI, Inter, Arial, sans-serif",
            "size": 13,
            "color": "#334139",
        },
        title={
            "x": 0,
            "xanchor": "left",
            "font": {"size": 17, "color": "#16211B"},
        },
        margin={"l": 20, "r": 20, "t": 62, "b": 24},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={
            "bgcolor": "#18211D",
            "font": {"color": "#FFFFFF", "size": 12},
            "bordercolor": "#18211D",
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "title": None,
        },
    )
    figure.update_xaxes(
        showgrid=False,
        showline=True,
        linecolor="#DCE5DF",
        tickfont={"color": "#66726C"},
        title_font={"color": "#4C5B53", "size": 12},
    )
    figure.update_yaxes(
        gridcolor="#E7EDE9",
        gridwidth=1,
        zeroline=False,
        tickfont={"color": "#66726C"},
        title_font={"color": "#4C5B53", "size": 12},
    )
    return figure


def render_text(dataframe: pd.DataFrame, specification: ResultPresentation) -> None:
    st.write(specification.answer)


def render_kpi(dataframe: pd.DataFrame, specification: ResultPresentation) -> None:
    value_column = specification.y_columns[0]
    formatter = NUMBER_FORMATTERS[specification.number_format]
    st.write(specification.answer)
    st.metric(specification.title, formatter(dataframe.iloc[0][value_column]))


def render_table(dataframe: pd.DataFrame, specification: ResultPresentation) -> None:
    st.write(specification.answer)
    st.dataframe(dataframe, use_container_width=True, hide_index=True)


def render_bar(dataframe: pd.DataFrame, specification: ResultPresentation) -> None:
    st.write(specification.answer)
    figure = px.bar(
        dataframe,
        x=specification.x_column,
        y=specification.y_columns,
        color=specification.series_column,
        title=specification.title,
        labels={
            specification.x_column: specification.x_label or specification.x_column,
            **{
                column: specification.y_label or column
                for column in specification.y_columns
            },
        },
    )
    figure.update_traces(marker_line_width=0)
    st.plotly_chart(
        _style_figure(figure),
        use_container_width=True,
        key=_next_chart_key(),
    )


def render_line(dataframe: pd.DataFrame, specification: ResultPresentation) -> None:
    st.write(specification.answer)
    figure = px.line(
        dataframe,
        x=specification.x_column,
        y=specification.y_columns,
        color=specification.series_column,
        markers=True,
        title=specification.title,
        labels={
            specification.x_column: specification.x_label or specification.x_column,
            **{
                column: specification.y_label or column
                for column in specification.y_columns
            },
        },
    )
    figure.update_traces(line={"width": 3}, marker={"size": 7})
    st.plotly_chart(
        _style_figure(figure),
        use_container_width=True,
        key=_next_chart_key(),
    )


def render_pie(dataframe: pd.DataFrame, specification: ResultPresentation) -> None:
    st.write(specification.answer)
    figure = px.pie(
        dataframe,
        names=specification.x_column,
        values=specification.y_columns[0],
        title=specification.title,
    )
    figure.update_traces(
        hole=0.48,
        marker={"line": {"color": "#FFFFFF", "width": 2}},
        textposition="inside",
    )
    st.plotly_chart(
        _style_figure(figure),
        use_container_width=True,
        key=_next_chart_key(),
    )


PRESENTATION_RENDERERS: dict[
    str,
    Callable[[pd.DataFrame, ResultPresentation], None],
] = {
    "text": render_text,
    "kpi": render_kpi,
    "table": render_table,
    "bar": render_bar,
    "line": render_line,
    "pie": render_pie,
}


def render_presentation(
    dataframe: pd.DataFrame,
    specification: ResultPresentation,
) -> None:
    renderer = PRESENTATION_RENDERERS.get(specification.presentation, render_table)
    renderer(dataframe, specification)
