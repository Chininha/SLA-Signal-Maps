import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from . import update_figs_layout

def sla_last_30days(data: pd.DataFrame):
    fig = go.Figure()
    color_list = px.colors.qualitative.G10
    for idx, business_unit in enumerate(data['name'].unique()):
        filtered_BU = data[data['name'] == business_unit]

        fig.add_trace(go.Scatter(x=filtered_BU['date(dsl.created_at)'], y=filtered_BU['sla_mean'], mode='lines+markers', line=dict(width=3, color=color_list[idx], shape='spline'),
                                name=filtered_BU['name'].unique()[0]))

    fig.update_layout(title=dict(text='Average SLA over the last 30 days', font=dict(size=26, family='roboto'), x=0.5, y=0.93, xanchor='center', yanchor='top'),
                      font=dict(family='roboto'), colorscale_sequential=px.colors.qualitative.G10,
                      legend=dict(y=-0.2, orientation='h', font=dict(family='roboto', size=14)), height=500)
    
    fig.update_xaxes(showgrid=True, griddash='solid', gridcolor='rgba(211, 211, 211, 0.2)', title=None, tickfont=dict(size=16, family='roboto'))
    fig.update_yaxes(title=dict(text=None, font=dict(family='roboto', size=18)), tickfont=dict(family='roboto', size=14), ticksuffix='%')

    update_figs_layout.alter_hover(fig=fig, mode='x unified')

    return fig