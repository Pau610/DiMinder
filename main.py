import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models.glucose_predictor import GlucosePredictor
from utils.data_processor import DataProcessor
from utils.visualization import create_glucose_plot, create_prediction_plot
import plotly.graph_objects as go

# Page config
st.set_page_config(page_title="Diabetes Management System", layout="wide")

# Initialize session state
if 'glucose_data' not in st.session_state:
    st.session_state.glucose_data = pd.DataFrame(columns=['timestamp', 'glucose_level', 'carbs', 'insulin'])
if 'predictor' not in st.session_state:
    st.session_state.predictor = GlucosePredictor()
if 'processor' not in st.session_state:
    st.session_state.processor = DataProcessor()

# Main title
st.title("🩺 Diabetes Management System")

# Sidebar
st.sidebar.header("Data Input")

# Blood glucose input
with st.sidebar.expander("Record Blood Glucose", expanded=True):
    glucose_level = st.number_input("Blood Glucose Level (mg/dL)", 40.0, 400.0, 120.0)
    record_time = st.time_input("Time of Reading", datetime.now())
    if st.button("Add Glucose Reading"):
        new_data = {
            'timestamp': datetime.combine(datetime.today(), record_time),
            'glucose_level': glucose_level,
            'carbs': 0,
            'insulin': 0
        }
        st.session_state.glucose_data = pd.concat([
            st.session_state.glucose_data,
            pd.DataFrame([new_data])
        ], ignore_index=True)
        st.success("Reading recorded!")

# Meal input
with st.sidebar.expander("Record Meal", expanded=True):
    food_db = pd.read_csv('data/food_database.csv')
    selected_food = st.selectbox("Select Food", food_db['food_name'].tolist())
    portion_size = st.number_input("Portion Size (grams)", 0, 1000, 100)
    
    food_info = food_db[food_db['food_name'] == selected_food].iloc[0]
    carbs = (food_info['carbs_per_100g'] * portion_size) / 100
    
    st.write(f"Total Carbohydrates: {carbs:.1f}g")
    
    if st.button("Add Meal"):
        new_meal = {
            'timestamp': datetime.now(),
            'glucose_level': 0,
            'carbs': carbs,
            'insulin': 0
        }
        st.session_state.glucose_data = pd.concat([
            st.session_state.glucose_data,
            pd.DataFrame([new_meal])
        ], ignore_index=True)
        st.success("Meal recorded!")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Blood Glucose Trends")
    if not st.session_state.glucose_data.empty:
        fig = create_glucose_plot(st.session_state.glucose_data)
        st.plotly_chart(fig, use_container_width=True)
        
        # Predictions
        st.subheader("Glucose Predictions")
        if len(st.session_state.glucose_data) >= 3:
            predictions = st.session_state.predictor.predict(st.session_state.glucose_data)
            fig_pred = create_prediction_plot(st.session_state.glucose_data, predictions)
            st.plotly_chart(fig_pred, use_container_width=True)
        else:
            st.info("Need at least 3 readings for predictions")

with col2:
    st.subheader("Recent Statistics")
    if not st.session_state.glucose_data.empty:
        recent_data = st.session_state.glucose_data.tail(5)
        st.metric("Latest Glucose", f"{recent_data['glucose_level'].iloc[-1]:.1f} mg/dL")
        st.metric("Average (Last 5)", f"{recent_data['glucose_level'].mean():.1f} mg/dL")
        
        # Insulin recommendation
        if recent_data['carbs'].sum() > 0:
            insulin_recommendation = st.session_state.processor.calculate_insulin_dose(
                recent_data['glucose_level'].iloc[-1],
                recent_data['carbs'].sum()
            )
            st.metric("Suggested Insulin Dose", f"{insulin_recommendation:.1f} units")

# Data table
st.subheader("Recent Records")
st.dataframe(st.session_state.glucose_data.tail(10))
