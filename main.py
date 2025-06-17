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
    page_title="我的日記",
    layout="wide",
    initial_sidebar_state="expanded"  # 保持侧边栏展开
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

# Helper function to parse time input
def parse_time_input(time_str):
    """Parse time input in various formats and return a time object"""
    if not time_str:
        return None
    
    # Remove any non-digit characters
    digits_only = ''.join(filter(str.isdigit, str(time_str)))
    
    if len(digits_only) == 4:
        # Format: HHMM (e.g., "1442" -> "14:42")
        try:
            hour = int(digits_only[:2])
            minute = int(digits_only[2:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        except ValueError:
            pass
    elif len(digits_only) == 3:
        # Format: HMM (e.g., "942" -> "09:42")
        try:
            hour = int(digits_only[0])
            minute = int(digits_only[1:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        except ValueError:
            pass
    
    return None

# Functions for persistent data storage
def load_persistent_data():
    """Load data with robust recovery mechanisms and data integrity checks"""
    def create_empty_dataframe():
        return pd.DataFrame(columns=['timestamp', 'glucose_level', 'carbs', 'insulin', 'insulin_type', 'injection_site', 'food_details'])
    
    try:
        if os.path.exists('user_data.csv') and os.path.getsize('user_data.csv') > 0:
            try:
                data = pd.read_csv('user_data.csv')
                # Validate data structure
                required_columns = ['timestamp', 'glucose_level', 'carbs', 'insulin']
                if not all(col in data.columns for col in required_columns):
                    st.warning("数据文件格式不正确，正在创建新的数据文件")
                    return create_empty_dataframe()
                
                # Convert timestamp to datetime
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                
                # Handle missing columns
                for col in ['insulin_type', 'injection_site', 'food_details']:
                    if col not in data.columns:
                        data[col] = ''
                
                # Validate data types and ranges
                if len(data) > 0:
                    # Check for reasonable glucose values (30-600 mg/dL)
                    if data['glucose_level'].notna().any():
                        invalid_glucose = (data['glucose_level'] < 30) | (data['glucose_level'] > 600)
                        if invalid_glucose.any():
                            st.warning(f"发现 {invalid_glucose.sum()} 条异常血糖数据")
                
                return data
            except Exception as e:
                st.error(f"读取数据文件失败: {str(e)}，正在尝试恢复...")
                # Try to recover from backup
                for i in range(1, 4):
                    recovery_file = f'user_data_backup_{i}.csv'
                    if os.path.exists(recovery_file):
                        try:
                            import shutil
                            shutil.copy(recovery_file, 'user_data.csv')
                            st.warning(f"已从{recovery_file}恢复数据")
                            break
                        except:
                            continue
                return create_empty_dataframe()
        else:
            return create_empty_dataframe()
    except Exception as e:
        st.error(f"数据加载过程发生错误: {str(e)}")
        return create_empty_dataframe()

def save_persistent_data():
    """Save current data to persistent storage with multiple backup layers"""
    try:
        if 'glucose_data' in st.session_state and not st.session_state.glucose_data.empty:
            # Create backup before saving
            for i in range(3, 0, -1):
                current_backup = f'user_data_backup_{i}.csv'
                next_backup = f'user_data_backup_{i+1}.csv'
                if os.path.exists(current_backup):
                    try:
                        import shutil
                        if i == 3:
                            # Remove oldest backup
                            if os.path.exists('user_data_backup_4.csv'):
                                os.remove('user_data_backup_4.csv')
                        else:
                            shutil.copy(current_backup, next_backup)
                    except:
                        pass
            
            # Backup current file
            if os.path.exists('user_data.csv'):
                try:
                    import shutil
                    shutil.copy('user_data.csv', 'user_data_backup_1.csv')
                except:
                    pass
            
            # Save current data
            st.session_state.glucose_data.to_csv('user_data.csv', index=False)
    except Exception as e:
        st.error(f"数据保存失败: {str(e)}")

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
            insulin_dose = int(row['insulin']) if float(row['insulin']).is_integer() else row['insulin']
            summary_lines.append(f" {time_str} => {insulin_dose}U {row['insulin_type']}")
        
        # Meal record
        if row['carbs'] > 0 and row['food_details']:
            carbs_total = int(row['carbs']) if float(row['carbs']).is_integer() else row['carbs']
            summary_lines.append(f" {time_str} => {row['food_details']} [{carbs_total}g]")
    
    summary_lines.append(" )")
    return "\n".join(summary_lines)

# Enhanced session state initialization with data corruption protection
def validate_session_data():
    """Validate and recover session data if corrupted"""
    if 'glucose_data' not in st.session_state or st.session_state.glucose_data is None:
        return False
    
    try:
        # Check if data structure is valid
        required_columns = ['timestamp', 'glucose_level', 'carbs', 'insulin']
        if not isinstance(st.session_state.glucose_data, pd.DataFrame):
            return False
        if not all(col in st.session_state.glucose_data.columns for col in required_columns):
            return False
        return True
    except:
        return False

# Initialize or recover session state data
if not validate_session_data():
    st.session_state.glucose_data = load_persistent_data()
    st.session_state.data_initialized = True
    st.session_state.data_recovery_count = 0
else:
    # Periodic data validation and auto-save
    if st.session_state.get('data_recovery_count', 0) % 10 == 0:
        save_persistent_data()
    st.session_state.data_recovery_count = st.session_state.get('data_recovery_count', 0) + 1

# Initialize AI models with error handling
try:
    if 'predictor' not in st.session_state:
        st.session_state.predictor = GlucosePredictor()
    if 'processor' not in st.session_state:
        st.session_state.processor = DataProcessor()
except Exception as e:
    st.error(f"初始化预测模型时发生错误: {str(e)}")

# Main title
st.title("📔 我的日記")

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

# Data Entry Section - moved to main page
st.markdown("### 📝 数据录入")

# Initialize input type if not set
if 'input_type' not in st.session_state:
    st.session_state.input_type = 'glucose'

# Data type selection buttons
st.subheader("选择记录类型")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("血糖记录", use_container_width=True, type="primary" if st.session_state.input_type == 'glucose' else "secondary"):
        st.session_state.input_type = 'glucose'

with col2:
    if st.button("饮食记录", use_container_width=True, type="primary" if st.session_state.input_type == 'meal' else "secondary"):
        st.session_state.input_type = 'meal'

with col3:
    if st.button("胰岛素注射", use_container_width=True, type="primary" if st.session_state.input_type == 'insulin' else "secondary"):
        st.session_state.input_type = 'insulin'

st.markdown("---")

# Show selected input form
if st.session_state.input_type == 'glucose':
    # Blood glucose input
    with st.expander("记录血糖", expanded=True):
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
            if 'glucose_time_state' not in st.session_state:
                hk_now = datetime.now(HK_TZ)
                st.session_state.glucose_time_state = hk_now.time()
            
            # Quick time input option
            time_input_method = st.radio(
                "时间输入方式",
                ["快速输入 (如: 1442)", "时间选择器"],
                key="glucose_time_method",
                horizontal=True
            )
            
            if time_input_method == "快速输入 (如: 1442)":
                time_str = st.text_input(
                    "输入时间 (HHMM格式)",
                    placeholder="例如: 1442 表示 14:42",
                    key="glucose_time_text"
                )
                if time_str:
                    parsed_time = parse_time_input(time_str)
                    if parsed_time:
                        st.session_state.glucose_time_state = parsed_time
                        st.success(f"时间设置为: {parsed_time.strftime('%H:%M')}")
                    else:
                        st.error("请输入有效的时间格式 (如: 1442)")
                record_time = st.session_state.glucose_time_state
            else:
                record_time = st.time_input(
                    "记录时间 (GMT+8)",
                    value=st.session_state.glucose_time_state,
                    key="glucose_time"
                )
                st.session_state.glucose_time_state = record_time

        glucose_mmol = st.number_input("血糖水平 (mmol/L)", min_value=2.0, max_value=22.0, value=None, step=0.1, key="glucose_level", placeholder="请输入血糖值")

        if st.button("添加血糖记录", use_container_width=True):
            if glucose_mmol is not None:
                record_datetime = datetime.combine(record_date, record_time)
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
                save_persistent_data()
                if os.path.exists('user_data.csv'):
                    st.success(f"血糖记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
                else:
                    st.error("数据保存失败，请重试")
            else:
                st.error("请输入血糖值")

elif st.session_state.input_type == 'meal':
    # Meal input
    with st.expander("记录饮食", expanded=True):
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
            if 'meal_time_state' not in st.session_state:
                hk_now = datetime.now(HK_TZ)
                st.session_state.meal_time_state = hk_now.time()
            
            # Quick time input option
            meal_time_method = st.radio(
                "时间输入方式",
                ["快速输入 (如: 1442)", "时间选择器"],
                key="meal_time_method",
                horizontal=True
            )
            
            if meal_time_method == "快速输入 (如: 1442)":
                meal_time_str = st.text_input(
                    "输入时间 (HHMM格式)",
                    placeholder="例如: 1442 表示 14:42",
                    key="meal_time_text"
                )
                if meal_time_str:
                    parsed_meal_time = parse_time_input(meal_time_str)
                    if parsed_meal_time:
                        st.session_state.meal_time_state = parsed_meal_time
                        st.success(f"时间设置为: {parsed_meal_time.strftime('%H:%M')}")
                    else:
                        st.error("请输入有效的时间格式 (如: 1442)")
                meal_time = st.session_state.meal_time_state
            else:
                meal_time = st.time_input(
                    "用餐时间 (GMT+8)",
                    value=st.session_state.meal_time_state,
                    key="meal_time_input"
                )
                st.session_state.meal_time_state = meal_time

        if 'meal_foods' not in st.session_state:
            st.session_state.meal_foods = []

        st.write("添加食物:")
        col_food, col_carbs, col_add = st.columns([3, 2, 1])
        
        with col_food:
            food_name = st.text_input("食物名称", key="food_name_input", placeholder="例如：米饭、面条、苹果...")
        
        with col_carbs:
            carbs_amount = st.number_input("碳水化合物 (克)", min_value=0.0, max_value=500.0, value=None, step=0.1, key="carbs_input", placeholder="请输入克数")
        
        with col_add:
            st.write("")
            if st.button("➕", key="add_food_btn", help="添加食物"):
                if food_name and carbs_amount is not None and carbs_amount > 0:
                    st.session_state.meal_foods.append({
                        'food': food_name,
                        'carbs': carbs_amount
                    })
                    st.rerun()

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
                save_persistent_data()
                if os.path.exists('user_data.csv'):
                    st.session_state.meal_foods = []
                    st.success(f"饮食记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
                    st.rerun()
                else:
                    st.error("数据保存失败，请重试")
        else:
            st.info("请添加食物和碳水化合物含量")

elif st.session_state.input_type == 'insulin':
    # Insulin injection input
    with st.expander("记录胰岛素注射", expanded=True):
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
            if 'injection_time_state' not in st.session_state:
                hk_now = datetime.now(HK_TZ)
                st.session_state.injection_time_state = hk_now.time()
            
            # Quick time input option
            injection_time_method = st.radio(
                "时间输入方式",
                ["快速输入 (如: 1442)", "时间选择器"],
                key="injection_time_method",
                horizontal=True
            )
            
            if injection_time_method == "快速输入 (如: 1442)":
                injection_time_str = st.text_input(
                    "输入时间 (HHMM格式)",
                    placeholder="例如: 1442 表示 14:42",
                    key="injection_time_text"
                )
                if injection_time_str:
                    parsed_injection_time = parse_time_input(injection_time_str)
                    if parsed_injection_time:
                        st.session_state.injection_time_state = parsed_injection_time
                        st.success(f"时间设置为: {parsed_injection_time.strftime('%H:%M')}")
                    else:
                        st.error("请输入有效的时间格式 (如: 1442)")
                injection_time = st.session_state.injection_time_state
            else:
                injection_time = st.time_input(
                    "注射时间 (GMT+8)",
                    value=st.session_state.injection_time_state,
                    key="injection_time_input"
                )
                st.session_state.injection_time_state = injection_time

        injection_site = st.selectbox(
            "注射部位",
            ["腹部", "大腿", "手臂", "臀部"],
            key="injection_site_select"
        )

        insulin_type = st.selectbox(
            "胰岛素类型",
            ["短效胰岛素", "中效胰岛素", "长效胰岛素"],
            key="insulin_type_select"
        )
        insulin_dose = st.number_input(
            "胰岛素剂量 (单位)",
            min_value=0.0, 
            max_value=100.0, 
            value=None,
            step=0.5,
            key="insulin_dose_input",
            placeholder="请输入胰岛素剂量"
        )

        if st.button("添加胰岛素记录", use_container_width=True):
            if insulin_dose is not None and insulin_dose > 0:
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
                save_persistent_data()
                if os.path.exists('user_data.csv'):
                    st.success(f"注射记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
                else:
                    st.error("数据保存失败，请重试")
            else:
                st.error("请输入胰岛素剂量")

st.markdown("---")

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
            
            # Create and display glucose trend plot
            fig = create_glucose_plot(st.session_state.glucose_data, (start_date, end_date))
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="mobile_glucose_trend")
            else:
                st.info("选择的日期范围内没有血糖数据")
                
        except Exception as e:
            st.error(f"血糖趋势图显示错误: {str(e)}")

        # 血糖预测
        st.subheader("智能预测")
        try:
            # Filter glucose data for prediction
            glucose_only_data = st.session_state.glucose_data[st.session_state.glucose_data['glucose_level'] > 0].copy()
            
            if len(glucose_only_data) >= 3:
                predictions = st.session_state.predictor.predict(glucose_only_data)
                
                if predictions is not None and len(predictions) > 0:
                    # Real-time prediction
                    st.write("**未来30分钟血糖预测:**")
                    realtime_predictions = st.session_state.predictor.predict_real_time(glucose_only_data)
                    
                    if realtime_predictions:
                        pred_times = []
                        pred_values = []
                        current_time = datetime.now(HK_TZ)
                        
                        for i, pred in enumerate(realtime_predictions):
                            pred_time = current_time + timedelta(minutes=(i+1)*5)
                            pred_times.append(pred_time.strftime('%H:%M'))
                            pred_values.append(round(pred / 18.0182, 1))  # Convert to mmol/L
                        
                        # Display predictions in a more readable format
                        for time, value in zip(pred_times, pred_values):
                            if value < 3.9:
                                st.error(f"{time}: {value} mmol/L ⚠️ 低血糖风险")
                            elif value > 10.0:
                                st.warning(f"{time}: {value} mmol/L ⚠️ 高血糖")
                            else:
                                st.success(f"{time}: {value} mmol/L ✅ 正常范围")
                    
                    # Create prediction plot
                    pred_fig = create_prediction_plot(glucose_only_data, predictions)
                    if pred_fig:
                        st.plotly_chart(pred_fig, use_container_width=True, key="mobile_prediction")
                else:
                    st.info("预测功能暂时不可用，请确保有足够的血糖数据")
            else:
                st.info("需要至少3条血糖记录才能进行预测")
        except Exception as e:
            st.error(f"预测功能错误: {str(e)}")

        # 数据统计
        st.subheader("数据统计")
        try:
            # Calculate statistics
            glucose_data = st.session_state.glucose_data[st.session_state.glucose_data['glucose_level'] > 0]
            
            if not glucose_data.empty:
                # Convert to mmol/L for display
                glucose_mmol = glucose_data['glucose_level'] / 18.0182
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("平均血糖", f"{glucose_mmol.mean():.1f} mmol/L")
                    st.metric("最高血糖", f"{glucose_mmol.max():.1f} mmol/L")
                with col2:
                    st.metric("最低血糖", f"{glucose_mmol.min():.1f} mmol/L")
                    # Time in range (3.9-10.0 mmol/L)
                    in_range = ((glucose_mmol >= 3.9) & (glucose_mmol <= 10.0)).sum()
                    time_in_range = (in_range / len(glucose_mmol)) * 100
                    st.metric("目标范围内时间", f"{time_in_range:.1f}%")
            else:
                st.info("暂无血糖数据进行统计")
        except Exception as e:
            st.error(f"统计计算错误: {str(e)}")

        # 胰岛素使用情况
        st.subheader("胰岛素使用")
        try:
            insulin_data = st.session_state.glucose_data[st.session_state.glucose_data['insulin'] > 0]
            
            if not insulin_data.empty:
                # Show recent insulin injections
                st.write("**最近注射记录:**")
                recent_insulin = insulin_data.sort_values('timestamp', ascending=False).head(5)
                
                for _, row in recent_insulin.iterrows():
                    injection_time = pd.to_datetime(row['timestamp']).strftime('%m-%d %H:%M')
                    st.write(f"• {injection_time}: {row['insulin']}单位 {row['insulin_type']} ({row['injection_site']})")
                
                # Insulin statistics
                col1, col2 = st.columns(2)
                with col1:
                    total_insulin = insulin_data['insulin'].sum()
                    st.metric("总胰岛素用量", f"{total_insulin:.1f}单位")
                with col2:
                    daily_avg = insulin_data.groupby(insulin_data['timestamp'].dt.date)['insulin'].sum().mean()
                    st.metric("日均用量", f"{daily_avg:.1f}单位")
            else:
                st.info("暂无胰岛素注射记录")
        except Exception as e:
            st.error(f"胰岛素数据显示错误: {str(e)}")

    else:
        # 桌面端双列布局
        col1, col2 = st.columns(2)
        
        with col1:
            # 血糖趋势
            st.subheader("血糖趋势")
            try:
                # Date range selector
                date_col1, date_col2 = st.columns(2)
                with date_col1:
                    start_date = st.date_input(
                        "开始日期",
                        datetime.now() - timedelta(days=7),
                        key="desktop_start_date"
                    )
                with date_col2:
                    end_date = st.date_input(
                        "结束日期",
                        datetime.now(),
                        key="desktop_end_date"
                    )
                
                # Create and display glucose trend plot
                fig = create_glucose_plot(st.session_state.glucose_data, (start_date, end_date))
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="desktop_glucose_trend")
                else:
                    st.info("选择的日期范围内没有血糖数据")
                    
            except Exception as e:
                st.error(f"血糖趋势图显示错误: {str(e)}")

            # 数据统计
            st.subheader("数据统计")
            try:
                glucose_data = st.session_state.glucose_data[st.session_state.glucose_data['glucose_level'] > 0]
                
                if not glucose_data.empty:
                    glucose_mmol = glucose_data['glucose_level'] / 18.0182
                    
                    col_stat1, col_stat2 = st.columns(2)
                    with col_stat1:
                        st.metric("平均血糖", f"{glucose_mmol.mean():.1f} mmol/L")
                        st.metric("最低血糖", f"{glucose_mmol.min():.1f} mmol/L")
                    with col_stat2:
                        st.metric("最高血糖", f"{glucose_mmol.max():.1f} mmol/L")
                        in_range = ((glucose_mmol >= 3.9) & (glucose_mmol <= 10.0)).sum()
                        time_in_range = (in_range / len(glucose_mmol)) * 100
                        st.metric("目标范围内时间", f"{time_in_range:.1f}%")
                else:
                    st.info("暂无血糖数据进行统计")
            except Exception as e:
                st.error(f"统计计算错误: {str(e)}")

        with col2:
            # 智能预测
            st.subheader("智能预测")
            try:
                glucose_only_data = st.session_state.glucose_data[st.session_state.glucose_data['glucose_level'] > 0].copy()
                
                if len(glucose_only_data) >= 3:
                    predictions = st.session_state.predictor.predict(glucose_only_data)
                    
                    if predictions is not None and len(predictions) > 0:
                        # Real-time prediction
                        st.write("**未来30分钟血糖预测:**")
                        realtime_predictions = st.session_state.predictor.predict_real_time(glucose_only_data)
                        
                        if realtime_predictions:
                            pred_times = []
                            pred_values = []
                            current_time = datetime.now(HK_TZ)
                            
                            for i, pred in enumerate(realtime_predictions):
                                pred_time = current_time + timedelta(minutes=(i+1)*5)
                                pred_times.append(pred_time.strftime('%H:%M'))
                                pred_values.append(round(pred / 18.0182, 1))
                            
                            for time, value in zip(pred_times, pred_values):
                                if value < 3.9:
                                    st.error(f"{time}: {value} mmol/L ⚠️ 低血糖风险")
                                elif value > 10.0:
                                    st.warning(f"{time}: {value} mmol/L ⚠️ 高血糖")
                                else:
                                    st.success(f"{time}: {value} mmol/L ✅ 正常范围")
                        
                        pred_fig = create_prediction_plot(glucose_only_data, predictions)
                        if pred_fig:
                            st.plotly_chart(pred_fig, use_container_width=True, key="desktop_prediction")
                    else:
                        st.info("预测功能暂时不可用，请确保有足够的血糖数据")
                else:
                    st.info("需要至少3条血糖记录才能进行预测")
            except Exception as e:
                st.error(f"预测功能错误: {str(e)}")

            # 胰岛素使用情况
            st.subheader("胰岛素使用")
            try:
                insulin_data = st.session_state.glucose_data[st.session_state.glucose_data['insulin'] > 0]
                
                if not insulin_data.empty:
                    st.write("**最近注射记录:**")
                    recent_insulin = insulin_data.sort_values('timestamp', ascending=False).head(5)
                    
                    for _, row in recent_insulin.iterrows():
                        injection_time = pd.to_datetime(row['timestamp']).strftime('%m-%d %H:%M')
                        st.write(f"• {injection_time}: {row['insulin']}单位 {row['insulin_type']} ({row['injection_site']})")
                    
                    col_insulin1, col_insulin2 = st.columns(2)
                    with col_insulin1:
                        total_insulin = insulin_data['insulin'].sum()
                        st.metric("总胰岛素用量", f"{total_insulin:.1f}单位")
                    with col_insulin2:
                        daily_avg = insulin_data.groupby(insulin_data['timestamp'].dt.date)['insulin'].sum().mean()
                        st.metric("日均用量", f"{daily_avg:.1f}单位")
                else:
                    st.info("暂无胰岛素注射记录")
            except Exception as e:
                st.error(f"胰岛素数据显示错误: {str(e)}")