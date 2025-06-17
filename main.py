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
    """Load data with robust recovery mechanisms and data integrity checks"""
    def create_empty_dataframe():
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
    
    try:
        # Priority order for data recovery
        data_sources = [
            'user_data.csv',
            'user_data_safe.csv', 
            'user_data_backup.csv'
        ]
        
        # Try to load from each source in priority order
        for source_file in data_sources:
            if os.path.exists(source_file):
                try:
                    data = pd.read_csv(source_file)
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                    
                    # Verify data integrity
                    required_columns = ['timestamp', 'glucose_level', 'carbs', 'insulin']
                    if all(col in data.columns for col in required_columns):
                        # If this is not the primary file but has data, restore it
                        if source_file != 'user_data.csv' and not data.empty:
                            import shutil
                            shutil.copy(source_file, 'user_data.csv')
                            st.success(f"已从备份文件{source_file}恢复数据")
                        return data
                except Exception as e:
                    st.warning(f"尝试从{source_file}加载数据失败: {e}")
                    continue
        
        # If no user data files exist, create initial data from imported sample
        if not any(os.path.exists(f) for f in data_sources):
            if os.path.exists('processed_dm_data.csv'):
                try:
                    imported_data = pd.read_csv('processed_dm_data.csv')
                    imported_data['timestamp'] = pd.to_datetime(imported_data['timestamp'])
                    # Save as user data with multiple backups
                    imported_data.to_csv('user_data.csv', index=False)
                    imported_data.to_csv('user_data_safe.csv', index=False)
                    imported_data.to_csv('user_data_backup.csv', index=False)
                    return imported_data
                except Exception as e:
                    st.warning(f"导入初始数据失败: {e}")
        
        # Last resort: return empty dataframe
        empty_df = create_empty_dataframe()
        # Save empty dataframe to prevent repeated initialization attempts
        empty_df.to_csv('user_data.csv', index=False)
        return empty_df
        
    except Exception as e:
        st.error(f"数据加载严重失败: {e}")
        return create_empty_dataframe()

def save_persistent_data():
    """Save current data to persistent storage with multiple backup layers"""
    try:
        import shutil
        from datetime import datetime
        
        # Create timestamped backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create multiple backup copies
        if os.path.exists('user_data.csv'):
            shutil.copy('user_data.csv', 'user_data_backup.csv')
            shutil.copy('user_data.csv', f'user_data_backup_{timestamp}.csv')
        
        # Save current data with verification
        temp_file = 'user_data_temp.csv'
        st.session_state.glucose_data.to_csv(temp_file, index=False)
        
        # Verify temp file before replacing main file
        if os.path.exists(temp_file):
            test_read = pd.read_csv(temp_file)
            if len(test_read) == len(st.session_state.glucose_data):
                # Verification passed, replace main file
                shutil.move(temp_file, 'user_data.csv')
                
                # Create additional safety backup
                shutil.copy('user_data.csv', 'user_data_safe.csv')
                
                # Clean up old timestamped backups (keep only last 3)
                import glob
                backup_files = glob.glob('user_data_backup_*.csv')
                if len(backup_files) > 3:
                    backup_files.sort()
                    for old_backup in backup_files[:-3]:
                        try:
                            os.remove(old_backup)
                        except:
                            pass
            else:
                # Verification failed, remove temp file and restore backup
                os.remove(temp_file)
                if os.path.exists('user_data_backup.csv'):
                    st.error("数据保存验证失败，已保持原有数据")
            
    except Exception as e:
        st.error(f"数据保存失败: {e}")
        # Try multiple recovery options
        recovery_files = ['user_data_backup.csv', 'user_data_safe.csv']
        for recovery_file in recovery_files:
            if os.path.exists(recovery_file):
                try:
                    import shutil
                    shutil.copy(recovery_file, 'user_data.csv')
                    st.warning(f"已从{recovery_file}恢复数据")
                    break
                except:
                    continue

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
    # Verify data hasn't been accidentally reset
    if hasattr(st.session_state, 'last_record_count'):
        current_count = len(st.session_state.glucose_data)
        if current_count < st.session_state.last_record_count:
            # Data loss detected - attempt recovery
            recovered_data = load_persistent_data()
            if len(recovered_data) > current_count:
                st.session_state.glucose_data = recovered_data
                st.warning(f"检测到数据丢失，已恢复 {len(recovered_data)} 条记录")

# Track record count for loss detection
st.session_state.last_record_count = len(st.session_state.glucose_data)

# Enhanced periodic backup system
if 'last_backup_time' not in st.session_state:
    st.session_state.last_backup_time = datetime.now()
    st.session_state.backup_interval = 180  # 3 minutes for more frequent saves
else:
    current_time = datetime.now()
    time_diff = current_time - st.session_state.last_backup_time
    # More aggressive auto-save schedule
    if time_diff.total_seconds() > st.session_state.backup_interval and not st.session_state.glucose_data.empty:
        save_persistent_data()
        st.session_state.last_backup_time = current_time
        # Show subtle save confirmation
        if len(st.session_state.glucose_data) > 0:
            st.toast(f"已自动保存 {len(st.session_state.glucose_data)} 条记录", icon="💾")



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

# Sidebar with mobile-friendly layout
with st.sidebar:
    st.header("数据录入")

    # Data type selection buttons
    st.subheader("选择记录类型")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        glucose_selected = st.button("血糖记录", use_container_width=True, type="primary" if st.session_state.get('input_type') == 'glucose' else "secondary")
        if glucose_selected:
            st.session_state.input_type = 'glucose'
    
    with col2:
        meal_selected = st.button("饮食记录", use_container_width=True, type="primary" if st.session_state.get('input_type') == 'meal' else "secondary")
        if meal_selected:
            st.session_state.input_type = 'meal'
    
    with col3:
        insulin_selected = st.button("胰岛素注射", use_container_width=True, type="primary" if st.session_state.get('input_type') == 'insulin' else "secondary")
        if insulin_selected:
            st.session_state.input_type = 'insulin'

    # Initialize input type if not set
    if 'input_type' not in st.session_state:
        st.session_state.input_type = 'glucose'
    
    # Initialize expander states
    if 'glucose_expander_open' not in st.session_state:
        st.session_state.glucose_expander_open = True
    if 'meal_expander_open' not in st.session_state:
        st.session_state.meal_expander_open = True
    if 'insulin_expander_open' not in st.session_state:
        st.session_state.insulin_expander_open = True

    st.markdown("---")

    # Show selected input form
    if st.session_state.input_type == 'glucose':
        # Blood glucose input
        with st.expander("记录血糖", expanded=st.session_state.glucose_expander_open):
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

            glucose_mmol = st.number_input("血糖水平 (mmol/L)", min_value=2.0, max_value=22.0, value=None, step=0.1, key="glucose_level", placeholder="请输入血糖值")

            if st.button("添加血糖记录", use_container_width=True):
                if glucose_mmol is not None:
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
                    # Immediate save with validation
                    save_persistent_data()
                    # Verify save was successful
                    if os.path.exists('user_data.csv'):
                        st.success(f"血糖记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
                    else:
                        st.error("数据保存失败，请重试")
                else:
                    st.error("请输入血糖值")

    elif st.session_state.input_type == 'meal':
        # Meal input
        with st.expander("记录饮食", expanded=st.session_state.meal_expander_open):
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
                carbs_amount = st.number_input("碳水化合物 (克)", min_value=0.0, max_value=500.0, value=None, step=0.1, key="carbs_input", placeholder="请输入克数")
            
            with col_add:
                st.write("")  # 空行对齐
                if st.button("➕", key="add_food_btn", help="添加食物"):
                    if food_name and carbs_amount is not None and carbs_amount > 0:
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
                    # Immediate save with validation
                    save_persistent_data()
                    # Verify save was successful
                    if os.path.exists('user_data.csv'):
                        # 清空食物列表
                        st.session_state.meal_foods = []
                        st.success(f"饮食记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
                        st.rerun()
                    else:
                        st.error("数据保存失败，请重试")
            else:
                st.info("请添加食物和碳水化合物含量")

    elif st.session_state.input_type == 'insulin':
        # Insulin injection input
        with st.expander("记录胰岛素注射", expanded=st.session_state.insulin_expander_open):
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
                min_value=0.0, 
                max_value=100.0, 
                value=None,
                step=0.5,
                placeholder="请输入剂量",
                key="insulin_dose"
            )

            if st.button("添加注射记录", use_container_width=True):
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
                    # Immediate save with validation
                    save_persistent_data()
                    # Verify save was successful
                    if os.path.exists('user_data.csv'):
                        st.success(f"注射记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
                    else:
                        st.error("数据保存失败，请重试")
                else:
                    st.error("请输入胰岛素剂量")

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
                latest_mmol = round(recent_data['glucose_level'].iloc[-1] / 18.0182, 1)
                st.metric("最新血糖", f"{latest_mmol} mmol/L")
            with col2:
                avg_mmol = round(recent_data['glucose_level'].mean() / 18.0182, 1)
                st.metric("平均值 (最近5次)", f"{avg_mmol} mmol/L")

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

                    # Convert to mmol/L for display
                    real_time_predictions_mmol = [p / 18.0182 for p in real_time_predictions]
                    upper_bound_mmol = [p / 18.0182 for p in upper_bound]
                    lower_bound_mmol = [p / 18.0182 for p in lower_bound]

                    # Add prediction intervals
                    fig_real_time.add_trace(go.Scatter(
                        x=pred_times + pred_times[::-1],
                        y=np.concatenate([upper_bound_mmol, lower_bound_mmol[::-1]]),
                        fill='toself',
                        fillcolor='rgba(0,176,246,0.2)',
                        line=dict(color='rgba(255,255,255,0)'),
                        name='预测区间'
                    ))

                    # Add predictions
                    fig_real_time.add_trace(go.Scatter(
                        x=pred_times,
                        y=real_time_predictions_mmol,
                        name='预测值',
                        line=dict(color='red', width=2)
                    ))

                    fig_real_time.update_layout(
                        title='未来30分钟血糖预测',
                        xaxis_title='时间',
                        yaxis_title='血糖值 (mmol/L)',
                        height=300
                    )
                    st.plotly_chart(fig_real_time, use_container_width=True)

                    # Check if any predicted values are dangerous (convert to mmol/L thresholds)
                    # 40 mg/dL = 2.2 mmol/L, 70 mg/dL = 3.9 mmol/L, 180 mg/dL = 10.0 mmol/L
                    predictions_mmol = [p / 18.0182 for p in real_time_predictions]
                    if np.any(np.array(predictions_mmol) <= 2.2):
                        st.error("⚠️ 危险！预测未来30分钟内可能出现严重低血糖，请立即采取预防措施！")
                    elif np.any(np.array(predictions_mmol) < 3.9):
                        st.warning("⚠️ 注意！预测未来30分钟内可能出现低血糖，请做好准备。")

                    if np.any(np.array(predictions_mmol) > 10.0) or np.any(np.array(predictions_mmol) < 3.9):
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

                        # Convert to mmol/L for display
                        real_time_predictions_mmol = [p / 18.0182 for p in real_time_predictions]
                        upper_bound_mmol = [p / 18.0182 for p in upper_bound]
                        lower_bound_mmol = [p / 18.0182 for p in lower_bound]

                        # Add prediction intervals
                        fig_real_time.add_trace(go.Scatter(
                            x=pred_times + pred_times[::-1],
                            y=np.concatenate([upper_bound_mmol, lower_bound_mmol[::-1]]),
                            fill='toself',
                            fillcolor='rgba(0,176,246,0.2)',
                            line=dict(color='rgba(255,255,255,0)'),
                            name='预测区间'
                        ))

                        # Add predictions
                        fig_real_time.add_trace(go.Scatter(
                            x=pred_times,
                            y=real_time_predictions_mmol,
                            name='预测值',
                            line=dict(color='red', width=2)
                        ))

                        fig_real_time.update_layout(
                            title='未来30分钟血糖预测',
                            xaxis_title='时间',
                            yaxis_title='血糖值 (mmol/L)',
                            height=300
                        )
                        st.plotly_chart(fig_real_time, use_container_width=True)

                        # Check if any predicted values are dangerous (convert to mmol/L thresholds)
                        # 40 mg/dL = 2.2 mmol/L, 70 mg/dL = 3.9 mmol/L, 180 mg/dL = 10.0 mmol/L
                        predictions_mmol = [p / 18.0182 for p in real_time_predictions]
                        if np.any(np.array(predictions_mmol) <= 2.2):
                            st.error("⚠️ 危险！预测未来30分钟内可能出现严重低血糖，请立即采取预防措施！")
                        elif np.any(np.array(predictions_mmol) < 3.9):
                            st.warning("⚠️ 注意！预测未来30分钟内可能出现低血糖，请做好准备。")

                        if np.any(np.array(predictions_mmol) > 10.0) or np.any(np.array(predictions_mmol) < 3.9):
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
                latest_glucose_mmol = recent_data['glucose_level'].iloc[-1] / 18.0182
                avg_glucose_mmol = recent_data['glucose_level'].mean() / 18.0182
                st.metric("最新血糖", f"{latest_glucose_mmol:.1f} mmol/L")
                st.metric("平均值 (最近5次)", f"{avg_glucose_mmol:.1f} mmol/L")

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
                
                # Display records with delete functionality
                st.write("**最近30条血糖记录:**")
                glucose_records = glucose_data.head(30)
                
                for idx, row in glucose_records.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 1])
                    
                    with col1:
                        st.write(f"{row['timestamp'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.write(f"{row['timestamp'].strftime('%H:%M')}")
                    with col3:
                        glucose_mmol = round(row['glucose_level'] / 18.0182, 1)
                        st.write(f"{glucose_mmol} mmol/L")
                    with col4:
                        status = '严重低血糖' if row['glucose_level'] <= 40 else ('低血糖' if row['glucose_level'] < 70 else ('正常' if row['glucose_level'] <= 180 else '高血糖'))
                        st.write(status)
                    with col5:
                        if st.button("🗑️", key=f"delete_glucose_{idx}", help="删除记录"):
                            if f"confirm_delete_glucose_{idx}" not in st.session_state:
                                st.session_state[f"confirm_delete_glucose_{idx}"] = True
                                st.rerun()
                            
                    # Confirmation dialog
                    if f"confirm_delete_glucose_{idx}" in st.session_state:
                        st.warning(f"确认删除 {row['timestamp'].strftime('%Y-%m-%d %H:%M')} 的血糖记录？")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("确认删除", key=f"confirm_yes_{idx}"):
                                st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                save_persistent_data()
                                del st.session_state[f"confirm_delete_glucose_{idx}"]
                                st.success("记录已删除")
                                st.rerun()
                        with col_no:
                            if st.button("取消", key=f"confirm_no_{idx}"):
                                del st.session_state[f"confirm_delete_glucose_{idx}"]
                                st.rerun()
                
                # Glucose statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    avg_glucose_mmol = glucose_data['glucose_level'].mean() / 18.0182
                    st.metric("平均血糖", f"{avg_glucose_mmol:.1f} mmol/L")
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
                
                # Display records with delete functionality
                st.write("**最近30条胰岛素注射记录:**")
                insulin_records = insulin_data.head(30)
                
                for idx, row in insulin_records.iterrows():
                    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1.5, 1.5, 1.5, 1])
                    
                    with col1:
                        st.write(f"{row['timestamp'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.write(f"{row['timestamp'].strftime('%H:%M')}")
                    with col3:
                        st.write(f"{row['insulin']:.1f} 单位")
                    with col4:
                        st.write(f"{row['insulin_type'] if pd.notna(row['insulin_type']) else '未指定'}")
                    with col5:
                        st.write(f"{row['injection_site'] if pd.notna(row['injection_site']) else '未指定'}")
                    with col6:
                        if st.button("🗑️", key=f"delete_insulin_{idx}", help="删除记录"):
                            if f"confirm_delete_insulin_{idx}" not in st.session_state:
                                st.session_state[f"confirm_delete_insulin_{idx}"] = True
                                st.rerun()
                            
                    # Confirmation dialog
                    if f"confirm_delete_insulin_{idx}" in st.session_state:
                        st.warning(f"确认删除 {row['timestamp'].strftime('%Y-%m-%d %H:%M')} 的胰岛素注射记录？")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("确认删除", key=f"confirm_insulin_yes_{idx}"):
                                st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                save_persistent_data()
                                del st.session_state[f"confirm_delete_insulin_{idx}"]
                                st.success("记录已删除")
                                st.rerun()
                        with col_no:
                            if st.button("取消", key=f"confirm_insulin_no_{idx}"):
                                del st.session_state[f"confirm_delete_insulin_{idx}"]
                                st.rerun()
                
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
                
                # Display records with delete functionality
                st.write("**最近30条饮食记录:**")
                meal_records = meal_data.head(30)
                
                for idx, row in meal_records.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 4, 1.5, 1])
                    
                    with col1:
                        st.write(f"{row['timestamp'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.write(f"{row['timestamp'].strftime('%H:%M')}")
                    with col3:
                        food_details = row['food_details'] if pd.notna(row['food_details']) and row['food_details'] else '未记录详情'
                        st.write(food_details)
                    with col4:
                        st.write(f"{row['carbs']:.1f}g")
                    with col5:
                        if st.button("🗑️", key=f"delete_meal_{idx}", help="删除记录"):
                            if f"confirm_delete_meal_{idx}" not in st.session_state:
                                st.session_state[f"confirm_delete_meal_{idx}"] = True
                                st.rerun()
                            
                    # Confirmation dialog
                    if f"confirm_delete_meal_{idx}" in st.session_state:
                        st.warning(f"确认删除 {row['timestamp'].strftime('%Y-%m-%d %H:%M')} 的饮食记录？")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("确认删除", key=f"confirm_meal_yes_{idx}"):
                                st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                save_persistent_data()
                                del st.session_state[f"confirm_delete_meal_{idx}"]
                                st.success("记录已删除")
                                st.rerun()
                        with col_no:
                            if st.button("取消", key=f"confirm_meal_no_{idx}"):
                                del st.session_state[f"confirm_delete_meal_{idx}"]
                                st.rerun()
                
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