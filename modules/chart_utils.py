"""Shared chart utilities — TradingView-style zoom/pan config for all Plotly charts."""

# Shared st.plotly_chart config — TradingView-style
TV_CHART_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": True,
    "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawcircle", "drawrect", "eraseshape"],
    "displaylogo": False}

# Shared update_layout kwargs — TradingView-style
TV_LAYOUT_KWARGS = dict(
    dragmode="zoom",
    hovermode="x unified",
    xaxis_rangeslider_visible=False,
)

# Shared spike settings for update_xaxes / update_yaxes
TV_SPIKE_XAXES = dict(
    showspikes=True,
    spikemode="across",
    spikesnap="cursor",
    spikecolor="grey",
    spikethickness=1,
)

TV_SPIKE_YAXES = dict(
    fixedrange=False,
    showspikes=True,
    spikemode="across",
    spikesnap="cursor",
    spikecolor="grey",
    spikethickness=1,
)


def apply_tv_style(fig, tight_margins=True):
    """Apply TradingView-style settings to a Plotly figure (in-place)."""
    fig.update_layout(
        dragmode="zoom",
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
    )
    if tight_margins:
        fig.update_layout(margin=dict(l=10, r=60, t=10, b=10))
    fig.update_xaxes(
        rangeslider_visible=False,
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="grey",
        spikethickness=1,
    )
    fig.update_yaxes(
        fixedrange=False,
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="grey",
        spikethickness=1,
    )
    return fig
