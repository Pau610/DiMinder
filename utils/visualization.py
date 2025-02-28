import plotly.graph_objects as go
from datetime import datetime, timedelta

def create_glucose_plot(data):
    """Create a plotly figure for glucose trends"""
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
    
    # Update layout
    fig.update_layout(
        title='Blood Glucose Readings',
        xaxis_title='Time',
        yaxis_title='Blood Glucose (mg/dL)',
        hovermode='x unified',
        showlegend=True
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
    
    # Update layout
    fig.update_layout(
        title='Glucose Predictions (Next 6 Hours)',
        xaxis_title='Time',
        yaxis_title='Blood Glucose (mg/dL)',
        hovermode='x unified',
        showlegend=True
    )
    
    return fig
