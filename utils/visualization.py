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
        name='Blood Glucose',
        line=dict(color='blue'),
        mode='lines+markers'
    ))

    # Add target range
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5)
    fig.add_hline(y=180, line_dash="dash", line_color="red", opacity=0.5)

    # Update layout with interactive features
    fig.update_layout(
        title='Blood Glucose Readings',
        xaxis_title='Time',
        yaxis_title='Blood Glucose (mg/dL)',
        hovermode='x unified',
        showlegend=True,
        # Add range slider
        xaxis=dict(
            rangeslider=dict(visible=True),
            type='date'
        ),
        # Add zoom and pan buttons
        updatemenus=[
            dict(
                type='buttons',
                showactive=False,
                buttons=[
                    dict(label='1D',
                         method='relayout',
                         args=[{'xaxis.range': [datetime.now() - timedelta(days=1), datetime.now()]}]),
                    dict(label='1W',
                         method='relayout',
                         args=[{'xaxis.range': [datetime.now() - timedelta(weeks=1), datetime.now()]}]),
                    dict(label='1M',
                         method='relayout',
                         args=[{'xaxis.range': [datetime.now() - timedelta(days=30), datetime.now()]}]),
                    dict(label='ALL',
                         method='relayout',
                         args=[{'xaxis.range': [data['timestamp'].min(), data['timestamp'].max()]}])
                ]
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
        name='Historical',
        line=dict(color='blue'),
        mode='lines+markers'
    ))

    # Predictions
    fig.add_trace(go.Scatter(
        x=future_timestamps,
        y=predictions,
        name='Predicted',
        line=dict(color='red', dash='dash'),
        mode='lines'
    ))

    # Update layout with interactive features
    fig.update_layout(
        title='Glucose Predictions (Next 6 Hours)',
        xaxis_title='Time',
        yaxis_title='Blood Glucose (mg/dL)',
        hovermode='x unified',
        showlegend=True,
        # Add range slider
        xaxis=dict(
            rangeslider=dict(visible=True),
            type='date'
        )
    )

    return fig