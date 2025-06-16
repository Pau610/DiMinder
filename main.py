import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import pytz
from models.glucose_predictor import GlucosePredictor
from utils.data_processor import DataProcessor
from utils.visualization import create_glucose_plot, create_prediction_plot
import plotly.graph_objects as go

# Set Hong Kong timezone
HK_TZ = pytz.timezone('Asia/Hong_Kong')

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

# Functions for persistent data storage
def load_persistent_data():
    """Load data with persistent manual records"""
    try:
        # Try to load persistent data first (includes manual records)
        if os.path.exists('user_data.csv'):
            data = pd.read_csv('user_data.csv')
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            return data
        else:
            # If no persistent data exists, load imported data
            imported_data = pd.read_csv('processed_dm_data.csv')
            imported_data['timestamp'] = pd.to_datetime(imported_data['timestamp'])
            return imported_data
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        # Fallback to empty data if everything fails
        return pd.DataFrame({
            'timestamp': [],
            'glucose_level': [],
            'carbs': [],
            'insulin': [],
            'insulin_type': [],
            'injection_site': [],
            'food_details': []
        }).astype({
            'timestamp': 'datetime64[ns]',
            'glucose_level': 'float64',
            'carbs': 'float64', 
            'insulin': 'float64',
            'insulin_type': 'object',
            'injection_site': 'object',
            'food_details': 'object'
        })

def save_persistent_data():
    """Save current data to persistent storage"""
    try:
        st.session_state.glucose_data.to_csv('user_data.csv', index=False)
    except Exception as e:
        st.error(f"数据保存失败: {e}")

def generate_daily_summary(selected_date):
    """Generate daily summary in the requested format"""
    if st.session_state.glucose_data.empty:
        return ""
    
    # Filter data for the selected date
    data = st.session_state.glucose_data.copy()
    data['date'] = pd.to_datetime(data['timestamp']).dt.date
    daily_data = data[data['date'] == selected_date].sort_values('timestamp')
    
    if daily_data.empty:
        return f"({selected_date}\n 无记录\n)"
    
    summary_lines = [f"({selected_date}"]
    
    for _, row in daily_data.iterrows():
        time_str = pd.to_datetime(row['timestamp']).strftime('%H:%M')
        
        # Blood glucose record
        if row['glucose_level'] > 0:
            glucose_mmol = round(row['glucose_level'] / 18.0182, 1)
            summary_lines.append(f" {time_str} => {glucose_mmol}mmol")
        
        # Insulin injection record
        if row['insulin'] > 0:
            insulin_dose = int(row['insulin']) if row['insulin'].is_integer() else row['insulin']
            summary_lines.append(f" {time_str} => {insulin_dose}U {row['insulin_type']}")
        
        # Meal record
        if row['carbs'] > 0 and row['food_details']:
            carbs_total = int(row['carbs']) if row['carbs'].is_integer() else row['carbs']
            summary_lines.append(f" {time_str} => {row['food_details']} [{carbs_total}g]")
    
    summary_lines.append(" )")
    return "\n".join(summary_lines)

# Initialize session state with persistent data
if 'glucose_data' not in st.session_state:
    st.session_state.glucose_data = load_persistent_data()

# Optional reload button (restores original imported data)
if st.button("重新加载原始数据", key="reload_data"):
    try:
        imported_data = pd.read_csv('processed_dm_data.csv')
        imported_data['timestamp'] = pd.to_datetime(imported_data['timestamp'])
        st.session_state.glucose_data = imported_data
        save_persistent_data()  # Save as new persistent data
        st.success("原始数据已重新加载")
    except Exception as e:
        st.error(f"数据重新加载失败: {e}")

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

# Daily Summary Section
st.markdown("### 📋 每日记录摘要")
col1, col2 = st.columns([3, 1])

with col1:
    # Date selector for daily summary
    if not st.session_state.glucose_data.empty:
        data_dates = pd.to_datetime(st.session_state.glucose_data['timestamp']).dt.date.unique()
        data_dates = sorted(data_dates, reverse=True)
        
        if data_dates:
            selected_date = st.selectbox(
                "选择日期查看摘要",
                options=data_dates,
                format_func=lambda x: x.strftime('%Y-%m-%d'),
                key="summary_date_select"
            )
            
            # Generate and display daily summary
            daily_summary = generate_daily_summary(selected_date)
            
            if daily_summary:
                st.text_area(
                    "每日摘要 (可复制)",
                    value=daily_summary,
                    height=200,
                    key="daily_summary_text"
                )
            else:
                st.info("选择的日期没有记录")
        else:
            st.info("暂无数据可显示摘要")
    else:
        st.info("暂无数据可显示摘要")

with col2:
    st.markdown("**使用说明:**")
    st.markdown("- 选择日期查看当日所有记录")
    st.markdown("- 可直接复制摘要文本")
    st.markdown("- 格式: 时间 => 记录内容")

st.markdown("---")

# Sidebar with mobile-friendly layout
with st.sidebar:
    st.header("数据录入")

    # Blood glucose input
    with st.expander("记录血糖", expanded=True):
        # 添加日期选择器
        col1, col2 = st.columns(2)
        with col1:
            hk_today = datetime.now(HK_TZ).date()
            record_date = st.date_input(
                "记录日期 (GMT+8)",
                hk_today,
                max_value=hk_today,
                key="glucose_date"
            )
        with col2:
            # 初始化血糖记录时间状态 (HK时区)
            if 'glucose_time_state' not in st.session_state:
                hk_now = datetime.now(HK_TZ)
                st.session_state.glucose_time_state = hk_now.time()
            
            record_time = st.time_input(
                "记录时间 (GMT+8)",
                value=st.session_state.glucose_time_state,
                key="glucose_time"
            )
            
            # 更新状态但不重置
            st.session_state.glucose_time_state = record_time

        glucose_mmol = st.number_input("血糖水平 (mmol/L)", 2.0, 22.0, 6.7, step=0.1, key="glucose_level")

        if st.button("添加血糖记录", use_container_width=True):
            record_datetime = datetime.combine(record_date, record_time)
            # Convert mmol/L to mg/dL for internal storage
            glucose_level_mgdl = glucose_mmol * 18.0182
            new_data = {
                'timestamp': record_datetime,
                'glucose_level': glucose_level_mgdl,
                'carbs': 0,
                'insulin': 0,
                'insulin_type': '',
                'injection_site': '',
                'food_details': ''
            }
            st.session_state.glucose_data = pd.concat([
                st.session_state.glucose_data,
                pd.DataFrame([new_data])
            ], ignore_index=True)
            save_persistent_data()  # Save to persistent storage
            st.success("记录已添加！")

    # Meal input
    with st.expander("记录饮食", expanded=True):
        try:
            # 添加日期选择器
            col1, col2 = st.columns(2)
            with col1:
                hk_today = datetime.now(HK_TZ).date()
                meal_date = st.date_input(
                    "用餐日期 (GMT+8)",
                    hk_today,
                    max_value=hk_today,
                    key="meal_date"
                )
            with col2:
                # 初始化用餐时间状态 (HK时区)
                if 'meal_time_state' not in st.session_state:
                    hk_now = datetime.now(HK_TZ)
                    st.session_state.meal_time_state = hk_now.time()
                
                meal_time = st.time_input(
                    "用餐时间 (GMT+8)",
                    value=st.session_state.meal_time_state,
                    key="meal_time_input"
                )
                
                # 更新状态但不重置
                st.session_state.meal_time_state = meal_time

            # 初始化食物列表
            if 'meal_foods' not in st.session_state:
                st.session_state.meal_foods = []

            # 添加食物输入
            st.write("添加食物:")
            col_food, col_carbs, col_add = st.columns([3, 2, 1])
            
            with col_food:
                food_name = st.text_input("食物名称", key="food_name_input", placeholder="例如：米饭、面条、苹果...")
            
            with col_carbs:
                carbs_amount = st.number_input("碳水化合物 (克)", 0.0, 500.0, 0.0, step=0.1, key="carbs_input")
            
            with col_add:
                st.write("")  # 空行对齐
                if st.button("➕", key="add_food_btn", help="添加食物"):
                    if food_name and carbs_amount > 0:
                        st.session_state.meal_foods.append({
                            'food': food_name,
                            'carbs': carbs_amount
                        })
                        st.rerun()

            # 显示已添加的食物
            if st.session_state.meal_foods:
                st.write("本餐食物:")
                total_carbs = 0
                for i, food_item in enumerate(st.session_state.meal_foods):
                    col_display, col_remove = st.columns([4, 1])
                    with col_display:
                        st.write(f"• {food_item['food']}: {food_item['carbs']}g 碳水化合物")
                        total_carbs += food_item['carbs']
                    with col_remove:
                        if st.button("🗑️", key=f"remove_food_{i}", help="删除"):
                            st.session_state.meal_foods.pop(i)
                            st.rerun()
                
                st.write(f"**总碳水化合物: {total_carbs:.1f}g**")

                if st.button("添加饮食记录", use_container_width=True):
                    meal_datetime = datetime.combine(meal_date, meal_time)
                    # Create detailed food description
                    food_list = [f"{item['food']} ({item['carbs']}g碳水)" for item in st.session_state.meal_foods]
                    food_details = "; ".join(food_list)
                    
                    new_meal = {
                        'timestamp': meal_datetime,
                        'glucose_level': 0,
                        'carbs': total_carbs,
                        'insulin': 0,
                        'insulin_type': '',
                        'injection_site': '',
                        'food_details': food_details
                    }
                    st.session_state.glucose_data = pd.concat([
                        st.session_state.glucose_data,
                        pd.DataFrame([new_meal])
                    ], ignore_index=True)
                    save_persistent_data()  # Save to persistent storage
                    # 清空食物列表
                    st.session_state.meal_foods = []
                    st.success("饮食记录已添加！")
                    st.rerun()
            else:
                st.info("请添加食物和碳水化合物含量")

        except Exception as e:
            st.error(f"添加饮食记录时发生错误: {str(e)}")

    # Insulin injection input
    with st.expander("记录胰岛素注射", expanded=True):
        try:
            # 添加日期选择器
            col1, col2 = st.columns(2)
            with col1:
                hk_today = datetime.now(HK_TZ).date()
                injection_date = st.date_input(
                    "注射日期 (GMT+8)",
                    hk_today,
                    max_value=hk_today,
                    key="injection_date"
                )
            with col2:
                # 初始化注射时间状态 (HK时区)
                if 'injection_time_state' not in st.session_state:
                    hk_now = datetime.now(HK_TZ)
                    st.session_state.injection_time_state = hk_now.time()
                
                injection_time = st.time_input(
                    "注射时间 (GMT+8)",
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
                    'injection_site': injection_site,
                    'food_details': ''
                }
                st.session_state.glucose_data = pd.concat([
                    st.session_state.glucose_data,
                    pd.DataFrame([new_injection])
                ], ignore_index=True)
                save_persistent_data()  # Save to persistent storage
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

    # Review Tables Section
    st.header("数据回顾分析")
    
    # Tab selection for different review tables
    tab1, tab2, tab3, tab4 = st.tabs(["血糖记录", "胰岛素注射记录", "饮食记录", "综合记录"])
    
    with tab1:
        st.subheader("血糖记录汇总")
        try:
            # Filter data to show only glucose records (glucose_level > 0)
            glucose_data = st.session_state.glucose_data[st.session_state.glucose_data['glucose_level'] > 0].copy()
            if not glucose_data.empty:
                glucose_data = glucose_data.sort_values('timestamp', ascending=False)
                
                # Create display dataframe
                display_glucose = glucose_data[['timestamp', 'glucose_level']].copy()
                display_glucose['日期'] = display_glucose['timestamp'].dt.strftime('%Y-%m-%d')
                display_glucose['时间'] = display_glucose['timestamp'].dt.strftime('%H:%M')
                display_glucose['血糖值 (mmol/L)'] = (display_glucose['glucose_level'] / 18.0182).round(1)
                display_glucose['血糖状态'] = display_glucose['glucose_level'].apply(
                    lambda x: '严重低血糖' if x <= 40 else ('低血糖' if x < 70 else ('正常' if x <= 180 else '高血糖'))
                )
                
                summary_glucose = display_glucose[['日期', '时间', '血糖值 (mmol/L)', '血糖状态']].head(30)
                st.dataframe(summary_glucose, use_container_width=True, height=400)
                
                # Glucose statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    avg_glucose = glucose_data['glucose_level'].mean()
                    st.metric("平均血糖", f"{avg_glucose:.1f} mg/dL")
                with col2:
                    low_count = len(glucose_data[glucose_data['glucose_level'] < 70])
                    st.metric("低血糖次数", f"{low_count}次")
                with col3:
                    high_count = len(glucose_data[glucose_data['glucose_level'] > 180])
                    st.metric("高血糖次数", f"{high_count}次")
                with col4:
                    danger_count = len(glucose_data[glucose_data['glucose_level'] <= 40])
                    st.metric("严重低血糖", f"{danger_count}次", delta_color="inverse")
            else:
                st.info("暂无血糖记录")
        except Exception as e:
            st.error(f"显示血糖汇总时发生错误: {str(e)}")
    
    with tab2:
        st.subheader("胰岛素注射记录汇总")
        try:
            # Filter data to show only insulin records (insulin > 0)
            insulin_data = st.session_state.glucose_data[st.session_state.glucose_data['insulin'] > 0].copy()
            if not insulin_data.empty:
                insulin_data = insulin_data.sort_values('timestamp', ascending=False)
                
                # Create display dataframe
                display_insulin = insulin_data[['timestamp', 'insulin', 'insulin_type', 'injection_site']].copy()
                display_insulin['日期'] = display_insulin['timestamp'].dt.strftime('%Y-%m-%d')
                display_insulin['时间'] = display_insulin['timestamp'].dt.strftime('%H:%M')
                display_insulin['剂量 (单位)'] = display_insulin['insulin'].round(1)
                display_insulin['胰岛素类型'] = display_insulin['insulin_type'].fillna('未指定')
                display_insulin['注射部位'] = display_insulin['injection_site'].fillna('未指定')
                
                summary_insulin = display_insulin[['日期', '时间', '剂量 (单位)', '胰岛素类型', '注射部位']].head(30)
                st.dataframe(summary_insulin, use_container_width=True, height=400)
                
                # Insulin statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_insulin = insulin_data['insulin'].sum()
                    st.metric("总胰岛素用量", f"{total_insulin:.1f}单位")
                with col2:
                    daily_avg = insulin_data.groupby(insulin_data['timestamp'].dt.date)['insulin'].sum().mean()
                    st.metric("日均用量", f"{daily_avg:.1f}单位")
                with col3:
                    long_acting = insulin_data[insulin_data['insulin_type'] == '长效胰岛素']['insulin'].sum()
                    st.metric("长效胰岛素", f"{long_acting:.1f}单位")
                with col4:
                    short_acting = insulin_data[insulin_data['insulin_type'] == '短效胰岛素']['insulin'].sum()
                    st.metric("短效胰岛素", f"{short_acting:.1f}单位")
            else:
                st.info("暂无胰岛素注射记录")
        except Exception as e:
            st.error(f"显示胰岛素汇总时发生错误: {str(e)}")
    
    with tab3:
        st.subheader("饮食记录汇总")
        try:
            # Filter data to show only meal records (carbs > 0)
            meal_data = st.session_state.glucose_data[st.session_state.glucose_data['carbs'] > 0].copy()
            if not meal_data.empty:
                meal_data = meal_data.sort_values('timestamp', ascending=False)
                
                # Create display dataframe with formatted data
                display_meals = meal_data[['timestamp', 'food_details', 'carbs']].copy()
                display_meals['日期'] = display_meals['timestamp'].dt.strftime('%Y-%m-%d')
                display_meals['时间'] = display_meals['timestamp'].dt.strftime('%H:%M')
                display_meals['食物详情'] = display_meals['food_details'].fillna('').apply(lambda x: x if x else '未记录详情')
                display_meals['碳水化合物 (g)'] = display_meals['carbs'].round(1)
                
                # Show summary table with food details
                summary_display = display_meals[['日期', '时间', '食物详情', '碳水化合物 (g)']].head(30)
                st.dataframe(
                    summary_display,
                    use_container_width=True,
                    height=400,
                    column_config={
                        "食物详情": st.column_config.TextColumn("食物详情", width="large")
                    }
                )
                
                # Add daily summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_carbs = meal_data['carbs'].sum()
                    st.metric("总碳水摄入", f"{total_carbs:.1f}g")
                
                with col2:
                    avg_daily_carbs = meal_data.groupby(meal_data['timestamp'].dt.date)['carbs'].sum().mean()
                    st.metric("日均碳水", f"{avg_daily_carbs:.1f}g")
                
                with col3:
                    total_meals = len(meal_data)
                    st.metric("总餐次", f"{total_meals}次")
                    
            else:
                st.info("暂无饮食记录")
        except Exception as e:
            st.error(f"显示饮食汇总时发生错误: {str(e)}")
    
    with tab4:
        st.subheader("综合记录总览")
        try:
            all_data = st.session_state.glucose_data.sort_values('timestamp', ascending=False)
            if not all_data.empty:
                # Create comprehensive display
                display_all = all_data.copy()
                display_all['日期'] = display_all['timestamp'].dt.strftime('%Y-%m-%d')
                display_all['时间'] = display_all['timestamp'].dt.strftime('%H:%M')
                display_all['血糖 (mg/dL)'] = display_all['glucose_level'].apply(lambda x: f"{x:.1f}" if x > 0 else "-")
                display_all['胰岛素 (单位)'] = display_all['insulin'].apply(lambda x: f"{x:.1f}" if x > 0 else "-")
                display_all['碳水 (g)'] = display_all['carbs'].apply(lambda x: f"{x:.1f}" if x > 0 else "-")
                display_all['记录类型'] = display_all.apply(lambda row: 
                    '血糖' if row['glucose_level'] > 0 else 
                    ('胰岛素' if row['insulin'] > 0 else 
                     ('饮食' if row['carbs'] > 0 else '其他')), axis=1)
                
                summary_all = display_all[['日期', '时间', '记录类型', '血糖 (mg/dL)', '胰岛素 (单位)', '碳水 (g)']].head(50)
                st.dataframe(summary_all, use_container_width=True, height=500)
                
                # Overall statistics
                st.subheader("总体统计")
                col1, col2, col3, col4 = st.columns(4)
                
                glucose_records = len(all_data[all_data['glucose_level'] > 0])
                insulin_records = len(all_data[all_data['insulin'] > 0])
                meal_records = len(all_data[all_data['carbs'] > 0])
                total_records = len(all_data)
                
                with col1:
                    st.metric("总记录数", f"{total_records}条")
                with col2:
                    st.metric("血糖记录", f"{glucose_records}条")
                with col3:
                    st.metric("胰岛素记录", f"{insulin_records}条")
                with col4:
                    st.metric("饮食记录", f"{meal_records}条")
                    
                # Date range
                date_range = f"{all_data['timestamp'].min().strftime('%Y-%m-%d')} 至 {all_data['timestamp'].max().strftime('%Y-%m-%d')}"
                st.info(f"数据时间范围: {date_range}")
                
            else:
                st.info("暂无任何记录")
        except Exception as e:
            st.error(f"显示综合记录时发生错误: {str(e)}")