import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models.glucose_predictor import GlucosePredictor
from utils.data_processor import DataProcessor
from utils.visualization import create_glucose_plot, create_prediction_plot
import plotly.graph_objects as go

# Page config
st.set_page_config(page_title="糖尿病管理系统", layout="wide")

# Initialize session state
if 'glucose_data' not in st.session_state:
    st.session_state.glucose_data = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(hours=i) for i in range(5)],
        'glucose_level': [120, 140, 110, 130, 125],
        'carbs': [0, 45, 0, 30, 0],
        'insulin': [0, 3, 0, 2, 0]
    })
if 'predictor' not in st.session_state:
    st.session_state.predictor = GlucosePredictor()
if 'processor' not in st.session_state:
    st.session_state.processor = DataProcessor()

# Main title
st.title("🩺 糖尿病管理系统")

# Sidebar
with st.sidebar:
    st.header("数据录入")

    # Blood glucose input
    with st.expander("记录血糖", expanded=True):
        glucose_level = st.number_input("血糖水平 (mg/dL)", 40.0, 400.0, 120.0)
        record_time = st.time_input("记录时间", datetime.now())

        if st.button("添加血糖记录"):
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
            st.success("记录已添加！")

    # Meal input
    with st.expander("记录饮食", expanded=True):
        food_db = pd.read_csv('data/food_database.csv')
        selected_food = st.selectbox("选择食物", food_db['food_name'].tolist())
        portion_size = st.number_input("份量 (克)", 0, 1000, 100)

        food_info = food_db[food_db['food_name'] == selected_food].iloc[0]
        carbs = (food_info['carbs_per_100g'] * portion_size) / 100

        st.write(f"总碳水化合物: {carbs:.1f}g")

        if st.button("添加饮食记录"):
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
            st.success("饮食记录已添加！")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("血糖趋势")
    if not st.session_state.glucose_data.empty:
        # Sort data by timestamp
        data_sorted = st.session_state.glucose_data.sort_values('timestamp')
        fig = create_glucose_plot(data_sorted)
        st.plotly_chart(fig, use_container_width=True)

        # Predictions
        st.subheader("血糖预测")
        if len(data_sorted) >= 3:
            predictions = st.session_state.predictor.predict(data_sorted)
            fig_pred = create_prediction_plot(data_sorted, predictions)
            st.plotly_chart(fig_pred, use_container_width=True)
        else:
            st.info("需要至少3个血糖记录来进行预测")

with col2:
    st.subheader("最近统计")
    if not st.session_state.glucose_data.empty:
        recent_data = st.session_state.glucose_data.sort_values('timestamp').tail(5)
        st.metric("最新血糖", f"{recent_data['glucose_level'].iloc[-1]:.1f} mg/dL")
        st.metric("平均值 (最近5次)", f"{recent_data['glucose_level'].mean():.1f} mg/dL")

        # Insulin recommendation
        if recent_data['carbs'].sum() > 0:
            insulin_recommendation = st.session_state.processor.calculate_insulin_dose(
                recent_data['glucose_level'].iloc[-1],
                recent_data['carbs'].sum()
            )
            st.metric("建议胰岛素剂量", f"{insulin_recommendation:.1f} 单位")

# Data table
st.subheader("最近记录")
if not st.session_state.glucose_data.empty:
    display_data = st.session_state.glucose_data.sort_values('timestamp', ascending=False).head(10)
    st.dataframe(display_data)