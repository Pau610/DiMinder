import plotly.graph_objects as go
from datetime import datetime, timedelta

def create_glucose_plot(data, date_range=None):
    """Create an interactive plotly figure for glucose trends with date range selection"""
    if date_range:
        start_date, end_date = date_range
        data = data[(data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)]

    # Data is already in mmol/L, no conversion needed
    data_display = data.copy()

    fig = go.Figure()

    # Add glucose readings in mmol/L
    fig.add_trace(go.Scatter(
        x=data_display['timestamp'],
        y=data_display['glucose_level'],
        name='血糖值',
        line=dict(color='blue', width=2),
        mode='lines+markers',
        marker=dict(size=10)  # 增大标记点以便触控
    ))

    # Add danger zone for hypoglycemia (below 2.2 mmol/L = 40 mg/dL)
    fig.add_hrect(
        y0=0, y1=2.2,
        fillcolor="red", opacity=0.1,
        layer="below", line_width=0,
        name="低血糖危险区域"
    )

    # Add target range lines in mmol/L
    fig.add_hline(y=2.2, line_dash="dash", line_color="red", opacity=0.8,
                  annotation_text="低血糖警戒线", annotation_position="top right")
    fig.add_hline(y=3.9, line_dash="dash", line_color="orange", opacity=0.5)
    fig.add_hline(y=10.0, line_dash="dash", line_color="orange", opacity=0.5)

    # Update layout with mobile-friendly features
    fig.update_layout(
        title='血糖读数',
        xaxis_title='时间',
        yaxis_title='血糖值 (mmol/L)',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.1),
            type='date',
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            tickfont=dict(size=10),
            range=[0, max(11.1, data_display['glucose_mmol'].max() * 1.1)]  # 确保危险区域可见
        ),
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                y=1.1,
                x=0,
                xanchor='left',
                yanchor='bottom',
                buttons=[
                    dict(
                        label='1天',
                        method='relayout',
                        args=[{'xaxis.range': [datetime.now() - timedelta(days=1), datetime.now()]}]
                    ),
                    dict(
                        label='1周',
                        method='relayout',
                        args=[{'xaxis.range': [datetime.now() - timedelta(weeks=1), datetime.now()]}]
                    ),
                    dict(
                        label='1月',
                        method='relayout',
                        args=[{'xaxis.range': [datetime.now() - timedelta(days=30), datetime.now()]}]
                    ),
                    dict(
                        label='全部',
                        method='relayout',
                        args=[{'xaxis.range': [data['timestamp'].min(), data['timestamp'].max()]}]
                    )
                ],
                pad={"r": 10, "t": 10},
                font=dict(size=12)
            )
        ]
    )

    return fig

def create_prediction_plot(data, predictions):
    """Create a plotly figure for glucose predictions"""
    last_timestamp = data['timestamp'].max()
    future_timestamps = [last_timestamp + timedelta(hours=i) for i in range(1, 7)]

    # Convert mg/dL to mmol/L for display
    data_display = data.copy()
    data_display['glucose_mmol'] = data_display['glucose_level'] / 18.0182
    predictions_mmol = [p / 18.0182 for p in predictions]

    fig = go.Figure()

    # Add danger zone for hypoglycemia (below 2.2 mmol/L)
    fig.add_hrect(
        y0=0, y1=2.2,
        fillcolor="red", opacity=0.1,
        layer="below", line_width=0,
        name="低血糖危险区域"
    )

    # Historical data in mmol/L
    fig.add_trace(go.Scatter(
        x=data_display['timestamp'],
        y=data_display['glucose_mmol'],
        name='历史数据',
        line=dict(color='blue', width=2),
        mode='lines+markers',
        marker=dict(size=10)
    ))

    # Predictions in mmol/L
    fig.add_trace(go.Scatter(
        x=future_timestamps,
        y=predictions_mmol,
        name='预测值',
        line=dict(color='red', width=2, dash='dash'),
        mode='lines'
    ))

    # Add warning lines in mmol/L
    fig.add_hline(y=2.2, line_dash="dash", line_color="red", opacity=0.8,
                  annotation_text="低血糖警戒线", annotation_position="top right")
    fig.add_hline(y=3.9, line_dash="dash", line_color="orange", opacity=0.5)
    fig.add_hline(y=10.0, line_dash="dash", line_color="orange", opacity=0.5)

    # Update layout with mobile-friendly features
    fig.update_layout(
        title='血糖预测（未来6小时）',
        xaxis_title='时间',
        yaxis_title='血糖值 (mmol/L)',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.1),
            type='date',
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            tickfont=dict(size=10),
            range=[0, max(200, max(data['glucose_level'].max(), max(predictions)) * 1.1)]
        )
    )

    return fig