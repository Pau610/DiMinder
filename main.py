import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models.glucose_predictor import GlucosePredictor
from utils.data_processor import DataProcessor
from utils.visualization import create_glucose_plot, create_prediction_plot
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="糖尿病管理系统",
    layout="wide",
    initial_sidebar_state="collapsed"  # 在移动端默认收起侧边栏
)

# Custom CSS for mobile-friendly design
st.markdown("""
<style>
    /* 增大按钮尺寸 */
    .stButton > button {
        width: 100%;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
    }

    /* 优化输入框样式 */
    .stNumberInput input,
    .stTextInput input,
    .stDateInput input {
        font-size: 1.1rem;
        padding: 0.5rem;
    }

    /* 优化选择框样式 */
    .stSelectbox select {
        font-size: 1.1rem;
        padding: 0.5rem;
    }

    /* 响应式布局调整 */
    @media (max-width: 768px) {
        .element-container {
            margin: 0.5rem 0;
        }

        /* 调整图表容器 */
        .plotly-graph-div {
            height: 300px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'glucose_data' not in st.session_state:
    st.session_state.glucose_data = pd.DataFrame({
        'timestamp': [datetime.now() - timedelta(hours=i) for i in range(5)],
        'glucose_level': [120, 140, 110, 130, 125],
        'carbs': [0, 45, 0, 30, 0],
        'insulin': [0, 3, 0, 2, 0],
        'insulin_type': ['', '', '', '', ''], #Added for insulin type
        'injection_site': ['', '', '', '', ''] #Added for injection site
    })

if 'selected_time' not in st.session_state:
    st.session_state.selected_time = datetime.now().time()

try:
    if 'predictor' not in st.session_state:
        st.session_state.predictor = GlucosePredictor()
    if 'processor' not in st.session_state:
        st.session_state.processor = DataProcessor()
except Exception as e:
    st.error(f"初始化预测模型时发生错误: {str(e)}")

# Main title
st.title("🩺 糖尿病管理系统")

# Sidebar with mobile-friendly layout
with st.sidebar:
    st.header("数据录入")

    # Blood glucose input
    with st.expander("记录血糖", expanded=True):
        # 添加日期选择器
        col1, col2 = st.columns(2)
        with col1:
            record_date = st.date_input(
                "记录日期",
                datetime.now(),
                max_value=datetime.now(),
                key="glucose_date"
            )
        with col2:
            # 初始化血糖记录时间状态
            if 'glucose_time_state' not in st.session_state:
                st.session_state.glucose_time_state = datetime.now().time()
            
            record_time = st.time_input(
                "记录时间",
                value=st.session_state.glucose_time_state,
                key="glucose_time"
            )
            
            # 更新状态但不重置
            st.session_state.glucose_time_state = record_time

        glucose_level = st.number_input("血糖水平 (mg/dL)", 40.0, 400.0, 120.0, key="glucose_level")

        if st.button("添加血糖记录", use_container_width=True):
            record_datetime = datetime.combine(record_date, record_time)
            new_data = {
                'timestamp': record_datetime,
                'glucose_level': glucose_level,
                'carbs': 0,
                'insulin': 0,
                'insulin_type': '',
                'injection_site': ''
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
            col1, col2 = st.columns(2)
            with col1:
                meal_date = st.date_input(
                    "用餐日期",
                    datetime.now(),
                    max_value=datetime.now(),
                    key="meal_date"
                )
            with col2:
                # 初始化用餐时间状态
                if 'meal_time_state' not in st.session_state:
                    st.session_state.meal_time_state = datetime.now().time()
                
                meal_time = st.time_input(
                    "用餐时间",
                    value=st.session_state.meal_time_state,
                    key="meal_time_input"
                )
                
                # 更新状态但不重置
                st.session_state.meal_time_state = meal_time

            food_db = pd.read_csv('data/food_database.csv')
            selected_food = st.selectbox("选择食物", food_db['food_name'].tolist(), key="food_select")
            portion_size = st.number_input("份量 (克)", 0, 1000, 100, key="portion_size")

            food_info = food_db[food_db['food_name'] == selected_food].iloc[0]
            carbs = (food_info['carbs_per_100g'] * portion_size) / 100

            st.write(f"总碳水化合物: {carbs:.1f}g")

            if st.button("添加饮食记录", use_container_width=True):
                meal_datetime = datetime.combine(meal_date, meal_time)
                new_meal = {
                    'timestamp': meal_datetime,
                    'glucose_level': 0,
                    'carbs': carbs,
                    'insulin': 0,
                    'insulin_type': '',
                    'injection_site': ''
                }
                st.session_state.glucose_data = pd.concat([
                    st.session_state.glucose_data,
                    pd.DataFrame([new_meal])
                ], ignore_index=True)
                st.success("饮食记录已添加！")
        except Exception as e:
            st.error(f"加载食物数据库时发生错误: {str(e)}")

    # Insulin injection input
    with st.expander("记录胰岛素注射", expanded=True):
        try:
            # 添加日期选择器
            col1, col2 = st.columns(2)
            with col1:
                injection_date = st.date_input(
                    "注射日期",
                    datetime.now(),
                    max_value=datetime.now(),
                    key="injection_date"
                )
            with col2:
                # 初始化注射时间状态
                if 'injection_time_state' not in st.session_state:
                    st.session_state.injection_time_state = datetime.now().time()
                
                injection_time = st.time_input(
                    "注射时间",
                    value=st.session_state.injection_time_state,
                    key="injection_time_input"
                )
                
                # 更新状态但不重置
                st.session_state.injection_time_state = injection_time

            # 注射部位选择
            injection_site = st.selectbox(
                "注射部位",
                ["腹部", "大腿", "手臂", "臀部"],
                key="injection_site_select"
            )

            # 胰岛素类型和剂量
            insulin_type = st.selectbox(
                "胰岛素类型",
                ["短效胰岛素", "中效胰岛素", "长效胰岛素"],
                key="insulin_type_select"
            )
            insulin_dose = st.number_input(
                "胰岛素剂量 (单位)",
                0.0, 100.0, 0.0,
                step=0.5,
                key="insulin_dose"
            )

            if st.button("添加注射记录", use_container_width=True):
                injection_datetime = datetime.combine(injection_date, injection_time)
                new_injection = {
                    'timestamp': injection_datetime,
                    'glucose_level': 0,
                    'carbs': 0,
                    'insulin': insulin_dose,
                    'insulin_type': insulin_type,
                    'injection_site': injection_site
                }
                st.session_state.glucose_data = pd.concat([
                    st.session_state.glucose_data,
                    pd.DataFrame([new_injection])
                ], ignore_index=True)
                st.success("注射记录已添加！")

        except Exception as e:
            st.error(f"添加注射记录时发生错误: {str(e)}")

# 血糖预警系统 (显著位置)
if not st.session_state.glucose_data.empty:
    latest_glucose = st.session_state.glucose_data['glucose_level'].iloc[-1]
    if latest_glucose <= 40:
        st.error("🚨 严重低血糖预警！当前血糖: {:.1f} mg/dL - 请立即处理！".format(latest_glucose))
        st.markdown("**紧急处理建议：**")
        st.markdown("- 立即摄入15-20克快速碳水化合物")
        st.markdown("- 15分钟后重新测量血糖")
        st.markdown("- 如无改善请寻求医疗帮助")
    elif latest_glucose < 70:
        st.warning("⚠️ 低血糖预警！当前血糖: {:.1f} mg/dL - 请及时处理".format(latest_glucose))

# Main content with responsive layout
if st.session_state.glucose_data.empty:
    st.info("还没有任何记录，请先添加数据。")
else:
    # 根据屏幕宽度决定使用单列或双列布局
    screen_width = st.empty()
    is_mobile = screen_width.checkbox("Mobile View", value=False, key="mobile_view")
    screen_width.empty()  # 清除checkbox

    if is_mobile:
        # 移动端单列布局
        # 血糖趋势
        st.subheader("血糖趋势")
        try:
            # Date range selector with responsive layout
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

            # Sort and filter data
            data_sorted = st.session_state.glucose_data.sort_values('timestamp')
            data_filtered = data_sorted[
                (data_sorted['timestamp'] >= start_datetime) &
                (data_sorted['timestamp'] <= end_datetime)
            ]

            # Create interactive plot with date range
            fig = create_glucose_plot(data_filtered, (start_datetime, end_datetime))
            st.plotly_chart(fig, use_container_width=True, height=350)

            # Recent statistics
            st.subheader("最近统计")
            recent_data = data_sorted.tail(5)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("最新血糖", f"{recent_data['glucose_level'].iloc[-1]:.1f} mg/dL")
            with col2:
                st.metric("平均值 (最近5次)", f"{recent_data['glucose_level'].mean():.1f} mg/dL")

            # 血糖预警检查
            recent_glucose = recent_data['glucose_level'].iloc[-1]
            if recent_glucose <= 40:
                st.error("⚠️ 危险！当前血糖值过低，请立即处理！")
            elif recent_glucose < 70:
                st.warning("⚠️ 注意！当前血糖值偏低，请及时补充糖分。")


            # Predictions
            st.subheader("血糖预测")
            if len(data_filtered) >= 3:
                predictions = st.session_state.predictor.predict(data_filtered)
                fig_pred = create_prediction_plot(data_filtered, predictions)
                st.plotly_chart(fig_pred, use_container_width=True, height=350)
            else:
                st.info("需要至少3个血糖记录来进行预测")


            # Real-time predictions
            st.subheader("实时血糖预测")
            if len(data_filtered) >= 12:
                real_time_predictions = st.session_state.predictor.predict_real_time(data_filtered)
                if len(real_time_predictions) > 0:
                    pred_times = [datetime.now() + timedelta(minutes=5*i) for i in range(6)]
                    real_time_df = pd.DataFrame({
                        'timestamp': pred_times,
                        'glucose_level': real_time_predictions
                    })
                    lower_bound, upper_bound = st.session_state.predictor.get_prediction_intervals(real_time_predictions)

                    fig_real_time = go.Figure()

                    # Add prediction intervals
                    fig_real_time.add_trace(go.Scatter(
                        x=pred_times + pred_times[::-1],
                        y=np.concatenate([upper_bound, lower_bound[::-1]]),
                        fill='toself',
                        fillcolor='rgba(0,176,246,0.2)',
                        line=dict(color='rgba(255,255,255,0)'),
                        name='预测区间'
                    ))

                    # Add predictions
                    fig_real_time.add_trace(go.Scatter(
                        x=pred_times,
                        y=real_time_predictions,
                        name='预测值',
                        line=dict(color='red', width=2)
                    ))

                    fig_real_time.update_layout(
                        title='未来30分钟血糖预测',
                        xaxis_title='时间',
                        yaxis_title='血糖值 (mg/dL)',
                        height=300
                    )
                    st.plotly_chart(fig_real_time, use_container_width=True)

                    # Check if any predicted values are dangerous
                    if np.any(real_time_predictions <= 40):
                        st.error("⚠️ 危险！预测未来30分钟内可能出现严重低血糖，请立即采取预防措施！")
                    elif np.any(real_time_predictions < 70):
                        st.warning("⚠️ 注意！预测未来30分钟内可能出现低血糖，请做好准备。")

                    if np.any(real_time_predictions > 180) or np.any(real_time_predictions < 70):
                        st.warning("⚠️ 预测显示血糖可能会超出目标范围，请注意监测")
                else:
                    st.info("需要至少1小时的数据来进行实时预测")

            # Insulin needs prediction
            st.subheader("胰岛素需求预测")
            if len(data_filtered) >= 24:
                insulin_predictions = st.session_state.processor.predict_insulin_needs(data_filtered)
                if len(insulin_predictions) > 0:
                    pred_hours = [datetime.now() + timedelta(hours=i) for i in range(24)]
                    insulin_df = pd.DataFrame({
                        'timestamp': pred_hours,
                        'insulin': insulin_predictions
                    })

                    fig_insulin = go.Figure()
                    fig_insulin.add_trace(go.Scatter(
                        x=pred_hours,
                        y=insulin_predictions,
                        name='预计胰岛素需求',
                        line=dict(color='purple', width=2)
                    ))

                    fig_insulin.update_layout(
                        title='24小时胰岛素需求预测',
                        xaxis_title='时间',
                        yaxis_title='胰岛素剂量 (单位)',
                        height=300
                    )
                    st.plotly_chart(fig_insulin, use_container_width=True)
            else:
                st.info("需要至少24小时的数据来预测胰岛素需求")

            # Injection site analysis
            st.subheader("注射部位分析")
            site_stats = st.session_state.processor.analyze_injection_sites(data_filtered)
            if site_stats:
                site_df = pd.DataFrame(site_stats)
                st.write("注射部位使用统计：")
                st.dataframe(site_df)
            else:
                st.info("暂无注射部位数据")

        except Exception as e:
            st.error(f"生成图表时发生错误: {str(e)}")

    else:
        # 桌面端双列布局
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("血糖趋势")
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

                # Sort and filter data
                data_sorted = st.session_state.glucose_data.sort_values('timestamp')
                data_filtered = data_sorted[
                    (data_sorted['timestamp'] >= start_datetime) &
                    (data_sorted['timestamp'] <= end_datetime)
                ]

                # Create interactive plot with date range
                fig = create_glucose_plot(data_filtered, (start_datetime, end_datetime))
                st.plotly_chart(fig, use_container_width=True, height=450)

                # Predictions
                st.subheader("血糖预测")
                if len(data_filtered) >= 3:
                    predictions = st.session_state.predictor.predict(data_filtered)
                    fig_pred = create_prediction_plot(data_filtered, predictions)
                    st.plotly_chart(fig_pred, use_container_width=True, height=450)
                else:
                    st.info("需要至少3个血糖记录来进行预测")

                # Real-time predictions
                st.subheader("实时血糖预测")
                if len(data_filtered) >= 12:
                    real_time_predictions = st.session_state.predictor.predict_real_time(data_filtered)
                    if len(real_time_predictions) > 0:
                        pred_times = [datetime.now() + timedelta(minutes=5*i) for i in range(6)]
                        real_time_df = pd.DataFrame({
                            'timestamp': pred_times,
                            'glucose_level': real_time_predictions
                        })
                        lower_bound, upper_bound = st.session_state.predictor.get_prediction_intervals(real_time_predictions)

                        fig_real_time = go.Figure()

                        # Add prediction intervals
                        fig_real_time.add_trace(go.Scatter(
                            x=pred_times + pred_times[::-1],
                            y=np.concatenate([upper_bound, lower_bound[::-1]]),
                            fill='toself',
                            fillcolor='rgba(0,176,246,0.2)',
                            line=dict(color='rgba(255,255,255,0)'),
                            name='预测区间'
                        ))

                        # Add predictions
                        fig_real_time.add_trace(go.Scatter(
                            x=pred_times,
                            y=real_time_predictions,
                            name='预测值',
                            line=dict(color='red', width=2)
                        ))

                        fig_real_time.update_layout(
                            title='未来30分钟血糖预测',
                            xaxis_title='时间',
                            yaxis_title='血糖值 (mg/dL)',
                            height=300
                        )
                        st.plotly_chart(fig_real_time, use_container_width=True)

                        # Check if any predicted values are dangerous
                        if np.any(real_time_predictions <= 40):
                            st.error("⚠️ 危险！预测未来30分钟内可能出现严重低血糖，请立即采取预防措施！")
                        elif np.any(real_time_predictions < 70):
                            st.warning("⚠️ 注意！预测未来30分钟内可能出现低血糖，请做好准备。")

                        if np.any(real_time_predictions > 180) or np.any(real_time_predictions < 70):
                            st.warning("⚠️ 预测显示血糖可能会超出目标范围，请注意监测")
                else:
                    st.info("需要至少1小时的数据来进行实时预测")

                # Insulin needs prediction
                st.subheader("胰岛素需求预测")
                if len(data_filtered) >= 24:
                    insulin_predictions = st.session_state.processor.predict_insulin_needs(data_filtered)
                    if len(insulin_predictions) > 0:
                        pred_hours = [datetime.now() + timedelta(hours=i) for i in range(24)]
                        insulin_df = pd.DataFrame({
                            'timestamp': pred_hours,
                            'insulin': insulin_predictions
                        })

                        fig_insulin = go.Figure()
                        fig_insulin.add_trace(go.Scatter(
                            x=pred_hours,
                            y=insulin_predictions,
                            name='预计胰岛素需求',
                            line=dict(color='purple', width=2)
                        ))

                        fig_insulin.update_layout(
                            title='24小时胰岛素需求预测',
                            xaxis_title='时间',
                            yaxis_title='胰岛素剂量 (单位)',
                            height=300
                        )
                        st.plotly_chart(fig_insulin, use_container_width=True)
                else:
                    st.info("需要至少24小时的数据来预测胰岛素需求")

                # Injection site analysis
                st.subheader("注射部位分析")
                site_stats = st.session_state.processor.analyze_injection_sites(data_filtered)
                if site_stats:
                    site_df = pd.DataFrame(site_stats)
                    st.write("注射部位使用统计：")
                    st.dataframe(site_df)
                else:
                    st.info("暂无注射部位数据")

            except Exception as e:
                st.error(f"生成图表时发生错误: {str(e)}")

        with col2:
            st.subheader("最近统计")
            try:
                recent_data = data_sorted.tail(5)
                st.metric("最新血糖", f"{recent_data['glucose_level'].iloc[-1]:.1f} mg/dL")
                st.metric("平均值 (最近5次)", f"{recent_data['glucose_level'].mean():.1f} mg/dL")

                # 血糖预警检查
                recent_glucose = recent_data['glucose_level'].iloc[-1]
                if recent_glucose <= 40:
                    st.error("⚠️ 危险！当前血糖值过低，请立即处理！")
                elif recent_glucose < 70:
                    st.warning("⚠️ 注意！当前血糖值偏低，请及时补充糖分。")

                # Insulin recommendation
                if recent_data['carbs'].sum() > 0:
                    insulin_recommendation = st.session_state.processor.calculate_insulin_dose(
                        recent_data['glucose_level'].iloc[-1],
                        recent_data['carbs'].sum()
                    )
                    st.metric("建议胰岛素剂量", f"{insulin_recommendation:.1f} 单位")
            except Exception as e:
                st.error(f"计算统计数据时发生错误: {str(e)}")

    # Data table with mobile-friendly scroll
    st.subheader("最近记录")
    try:
        display_data = st.session_state.glucose_data.sort_values('timestamp', ascending=False).head(10)
        st.dataframe(
            display_data,
            use_container_width=True,
            height=300 if is_mobile else 400
        )
    except Exception as e:
        st.error(f"显示数据表格时发生错误: {str(e)}")