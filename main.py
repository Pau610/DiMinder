import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models.glucose_predictor import GlucosePredictor
from utils.data_processor import DataProcessor
from utils.visualization import create_glucose_plot, create_prediction_plot

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

try:
    if 'predictor' not in st.session_state:
        st.session_state.predictor = GlucosePredictor()
    if 'processor' not in st.session_state:
        st.session_state.processor = DataProcessor()
except Exception as e:
    st.error(f"初始化预测模型时发生错误: {str(e)}")

# Main title
st.title("🩺 糖尿病管理系统")

# Sidebar
with st.sidebar:
    st.header("数据录入")

    # Blood glucose input
    with st.expander("记录血糖", expanded=True):
        # 添加日期选择器
        record_date = st.date_input(
            "记录日期",
            datetime.now(),
            max_value=datetime.now()
        )
        record_time = st.time_input("记录时间", datetime.now().time())
        glucose_level = st.number_input("血糖水平 (mg/dL)", 40.0, 400.0, 120.0)

        if st.button("添加血糖记录"):
            # 组合日期和时间
            record_datetime = datetime.combine(record_date, record_time)
            new_data = {
                'timestamp': record_datetime,
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
        try:
            # 添加日期选择器
            meal_date = st.date_input(
                "用餐日期",
                datetime.now(),
                max_value=datetime.now(),
                key="meal_date"
            )
            meal_time = st.time_input("用餐时间", datetime.now().time(), key="meal_time")

            food_db = pd.read_csv('data/food_database.csv')
            selected_food = st.selectbox("选择食物", food_db['food_name'].tolist())
            portion_size = st.number_input("份量 (克)", 0, 1000, 100)

            food_info = food_db[food_db['food_name'] == selected_food].iloc[0]
            carbs = (food_info['carbs_per_100g'] * portion_size) / 100

            st.write(f"总碳水化合物: {carbs:.1f}g")

            if st.button("添加饮食记录"):
                # 组合日期和时间
                meal_datetime = datetime.combine(meal_date, meal_time)
                new_meal = {
                    'timestamp': meal_datetime,
                    'glucose_level': 0,
                    'carbs': carbs,
                    'insulin': 0
                }
                st.session_state.glucose_data = pd.concat([
                    st.session_state.glucose_data,
                    pd.DataFrame([new_meal])
                ], ignore_index=True)
                st.success("饮食记录已添加！")
        except Exception as e:
            st.error(f"加载食物数据库时发生错误: {str(e)}")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("血糖趋势")
    if not st.session_state.glucose_data.empty:
        try:
            # Date range selector
            st.write("选择日期范围：")
            col_start, col_end = st.columns(2)
            with col_start:
                start_date = st.date_input(
                    "开始日期",
                    datetime.now() - timedelta(days=7)
                )
            with col_end:
                end_date = st.date_input(
                    "结束日期",
                    datetime.now()
                )

            # Convert dates to datetime
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Sort data by timestamp
            data_sorted = st.session_state.glucose_data.sort_values('timestamp')

            # Filter data by date range
            data_filtered = data_sorted[
                (data_sorted['timestamp'] >= start_datetime) &
                (data_sorted['timestamp'] <= end_datetime)
            ]

            # Create interactive plot with date range
            fig = create_glucose_plot(data_filtered, (start_datetime, end_datetime))
            st.plotly_chart(fig, use_container_width=True)

            # Predictions
            st.subheader("血糖预测")
            if len(data_filtered) >= 3:
                predictions = st.session_state.predictor.predict(data_filtered)
                fig_pred = create_prediction_plot(data_filtered, predictions)
                st.plotly_chart(fig_pred, use_container_width=True)
            else:
                st.info("需要至少3个血糖记录来进行预测")
        except Exception as e:
            st.error(f"生成图表时发生错误: {str(e)}")

with col2:
    st.subheader("最近统计")
    if not st.session_state.glucose_data.empty:
        try:
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
        except Exception as e:
            st.error(f"计算统计数据时发生错误: {str(e)}")

# Data table
st.subheader("最近记录")
if not st.session_state.glucose_data.empty:
    try:
        display_data = st.session_state.glucose_data.sort_values('timestamp', ascending=False).head(10)
        st.dataframe(display_data)
    except Exception as e:
        st.error(f"显示数据表格时发生错误: {str(e)}")