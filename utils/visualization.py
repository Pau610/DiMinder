import plotly.graph_objects as go
from datetime import datetime, timedelta

def create_glucose_plot(data, date_range=None):
    """Create an interactive plotly figure for glucose trends with date range selection"""
    if date_range:
        start_date, end_date = date_range
        data = data[(data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)]

    fig = go.Figure()

    # Add glucose readings
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['glucose_level'],
        name='血糖值',
        line=dict(color='blue', width=2),
        mode='lines+markers',
        marker=dict(size=10)  # 增大标记点以便触控
    ))

    # Add target range
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5)
    fig.add_hline(y=180, line_dash="dash", line_color="red", opacity=0.5)

    # Update layout with mobile-friendly features
    fig.update_layout(
        title='血糖读数',
        xaxis_title='时间',
        yaxis_title='血糖值 (mg/dL)',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",  # 水平放置图例
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 移动端优化的边距
        margin=dict(l=10, r=10, t=60, b=10),
        # Add range slider
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.1),  # 减小滑块高度
            type='date',
            tickfont=dict(size=10)  # 减小刻度字体
        ),
        yaxis=dict(
            tickfont=dict(size=10)  # 减小刻度字体
        ),
        # Add zoom and pan buttons with larger touch targets
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
                # 增大按钮尺寸
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

    fig = go.Figure()

    # Historical data
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=data['glucose_level'],
        name='历史数据',
        line=dict(color='blue', width=2),
        mode='lines+markers',
        marker=dict(size=10)  # 增大标记点以便触控
    ))

    # Predictions
    fig.add_trace(go.Scatter(
        x=future_timestamps,
        y=predictions,
        name='预测值',
        line=dict(color='red', width=2, dash='dash'),
        mode='lines'
    ))

    # Update layout with mobile-friendly features
    fig.update_layout(
        title='血糖预测（未来6小时）',
        xaxis_title='时间',
        yaxis_title='血糖值 (mg/dL)',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",  # 水平放置图例
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 移动端优化的边距
        margin=dict(l=10, r=10, t=60, b=10),
        # Add range slider
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.1),  # 减小滑块高度
            type='date',
            tickfont=dict(size=10)  # 减小刻度字体
        ),
        yaxis=dict(
            tickfont=dict(size=10)  # 减小刻度字体
        )
    )

    return fig