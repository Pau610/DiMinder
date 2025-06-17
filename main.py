import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, time
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

# Enhanced mobile-friendly CSS design
st.markdown("""
<style>
    /* Mobile-first responsive design */
    .main .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* Enhanced button styling for mobile */
    .stButton > button {
        width: 100%;
        padding: 1rem 1.5rem;
        font-size: 1.2rem;
        font-weight: 600;
        border-radius: 8px;
        min-height: 3rem;
        background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
        border: none;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #2196F3 0%, #1976D2 100%);
    }
    
    /* Secondary button styling */
    .stButton > button[kind="secondary"] {
        background: linear-gradient(90deg, #9E9E9E 0%, #757575 100%);
    }

    /* Enhanced input field styling */
    .stNumberInput input,
    .stTextInput input,
    .stDateInput input,
    .stTimeInput input {
        font-size: 1.2rem;
        padding: 0.75rem;
        border-radius: 8px;
        border: 2px solid #E0E0E0;
        min-height: 3rem;
        box-sizing: border-box;
    }
    
    .stNumberInput input:focus,
    .stTextInput input:focus,
    .stDateInput input:focus,
    .stTimeInput input:focus {
        border-color: #2196F3;
        box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
    }

    /* Enhanced selectbox styling */
    .stSelectbox select {
        font-size: 1.2rem;
        padding: 0.75rem;
        border-radius: 8px;
        min-height: 3rem;
        border: 2px solid #E0E0E0;
    }

    /* Text area improvements */
    .stTextArea textarea {
        font-size: 1.1rem;
        padding: 0.75rem;
        border-radius: 8px;
        border: 2px solid #E0E0E0;
        min-height: 150px;
    }

    /* Mobile-specific improvements */
    @media (max-width: 768px) {
        /* Reduce margins and padding for mobile */
        .element-container {
            margin: 0.75rem 0;
        }
        
        /* Larger touch targets */
        .stButton > button {
            min-height: 3.5rem;
            font-size: 1.3rem;
        }
        
        /* Better input field sizing */
        .stNumberInput input,
        .stTextInput input,
        .stDateInput input,
        .stTimeInput input,
        .stSelectbox select {
            min-height: 3.5rem;
            font-size: 1.3rem;
        }

        /* Optimize charts for mobile */
        .plotly-graph-div {
            height: 350px !important;
        }
        
        /* Better column spacing */
        .row-widget.stHorizontal > div {
            padding: 0 0.25rem;
        }
        
        /* Improve metric display */
        div[data-testid="metric-container"] {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
        }
        
        /* Better tabs for mobile */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0.75rem 1rem;
            font-size: 1.1rem;
            min-height: 3rem;
        }
        
        /* Improve expander styling */
        .streamlit-expanderHeader {
            font-size: 1.2rem;
            font-weight: 600;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        /* Better dataframe display */
        .dataframe {
            font-size: 0.9rem;
        }
        
        /* Improve sidebar for mobile */
        .css-1d391kg {
            padding-top: 1rem;
        }
    }
    
    /* Extra small devices */
    @media (max-width: 480px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        
        .stButton > button {
            font-size: 1.1rem;
            padding: 0.875rem 1rem;
        }
        
        /* Stack columns on very small screens */
        .row-widget.stHorizontal {
            flex-direction: column;
        }
        
        .row-widget.stHorizontal > div {
            width: 100% !important;
            margin-bottom: 0.5rem;
        }
    }
    
    /* Toast notifications styling */
    .stToast {
        font-size: 1.1rem;
        padding: 1rem;
        border-radius: 8px;
    }
    
    /* Loading spinner improvements */
    .stSpinner {
        text-align: center;
        padding: 2rem;
    }
    
    /* Better alert styling */
    .stAlert {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-size: 1.1rem;
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

# Initialize session state page if not exists
if 'page' not in st.session_state:
    st.session_state.page = "记录数据"

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

# Navigation tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 数据录入", "🩸 血糖记录", "🍽️ 饮食记录", "💉 胰岛素记录", "📋 综合摘要"])

with tab1:
    # Mobile-friendly data input section in main area
    st.markdown("### 📝 数据录入")

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

    st.markdown("---")

    # Show selected input form
    if st.session_state.input_type == 'glucose':
        # Blood glucose input - using container instead of expander to prevent closing
        st.subheader("🩸 记录血糖")
        with st.container(border=True):
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
            
            # 快速时间输入 - 支持4位数字格式
            time_input_method = st.radio(
                "时间输入方式",
                ["快速输入 (如: 1442)", "时间选择器"],
                key="glucose_time_method",
                horizontal=True
            )
            
            if time_input_method == "快速输入 (如: 1442)":
                time_text = st.text_input(
                    "记录时间 (HHMM格式)",
                    placeholder="例如: 1442 表示 14:42",
                    key="glucose_time_text",
                    max_chars=4
                )
                
                # 验证和转换时间格式
                if time_text and len(time_text) == 4 and time_text.isdigit():
                    try:
                        hour = int(time_text[:2])
                        minute = int(time_text[2:])
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            record_time = time(hour, minute)
                            st.session_state.glucose_time_state = record_time
                            st.success(f"时间: {record_time.strftime('%H:%M')}")
                        else:
                            st.error("请输入有效时间 (小时: 00-23, 分钟: 00-59)")
                            record_time = st.session_state.glucose_time_state
                    except:
                        st.error("时间格式错误")
                        record_time = st.session_state.glucose_time_state
                elif time_text and len(time_text) > 0:
                    st.error("请输入4位数字 (例如: 1442)")
                    record_time = st.session_state.glucose_time_state
                else:
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
        # Meal input - using container instead of expander to prevent closing
        st.subheader("🍽️ 记录饮食")
        with st.container(border=True):
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
                
                # 快速时间输入 - 支持4位数字格式
                meal_time_method = st.radio(
                    "时间输入方式",
                    ["快速输入 (如: 1442)", "时间选择器"],
                    key="meal_time_method",
                    horizontal=True
                )
            
            if meal_time_method == "快速输入 (如: 1442)":
                meal_time_text = st.text_input(
                    "用餐时间 (HHMM格式)",
                    placeholder="例如: 1442 表示 14:42",
                    key="meal_time_text",
                    max_chars=4
                )
                
                # 验证和转换时间格式
                if meal_time_text and len(meal_time_text) == 4 and meal_time_text.isdigit():
                    try:
                        hour = int(meal_time_text[:2])
                        minute = int(meal_time_text[2:])
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            meal_time = time(hour, minute)
                            st.session_state.meal_time_state = meal_time
                            st.success(f"时间: {meal_time.strftime('%H:%M')}")
                        else:
                            st.error("请输入有效时间 (小时: 00-23, 分钟: 00-59)")
                            meal_time = st.session_state.meal_time_state
                    except:
                        st.error("时间格式错误")
                        meal_time = st.session_state.meal_time_state
                elif meal_time_text and len(meal_time_text) > 0:
                    st.error("请输入4位数字 (例如: 1442)")
                    meal_time = st.session_state.meal_time_state
                else:
                    meal_time = st.session_state.meal_time_state
            else:
                meal_time = st.time_input(
                    "用餐时间 (GMT+8)",
                    value=st.session_state.meal_time_state,
                    key="meal_time_input"
                )
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
        # Insulin injection input - using container instead of expander to prevent closing
        st.subheader("💉 记录胰岛素注射")
        with st.container(border=True):
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
                
                # 快速时间输入 - 支持4位数字格式
                injection_time_method = st.radio(
                    "时间输入方式",
                    ["快速输入 (如: 1442)", "时间选择器"],
                    key="injection_time_method",
                    horizontal=True
                )
                
                if injection_time_method == "快速输入 (如: 1442)":
                    injection_time_text = st.text_input(
                        "注射时间 (HHMM格式)",
                        placeholder="例如: 1442 表示 14:42",
                        key="injection_time_text",
                        max_chars=4
                    )
                    
                    # 验证和转换时间格式
                    if injection_time_text and len(injection_time_text) == 4 and injection_time_text.isdigit():
                        try:
                            hour = int(injection_time_text[:2])
                            minute = int(injection_time_text[2:])
                            if 0 <= hour <= 23 and 0 <= minute <= 59:
                                injection_time = time(hour, minute)
                                st.session_state.injection_time_state = injection_time
                                st.success(f"时间: {injection_time.strftime('%H:%M')}")
                            else:
                                st.error("请输入有效时间 (小时: 00-23, 分钟: 00-59)")
                                injection_time = st.session_state.injection_time_state
                        except:
                            st.error("时间格式错误")
                            injection_time = st.session_state.injection_time_state
                    elif injection_time_text and len(injection_time_text) > 0:
                        st.error("请输入4位数字 (例如: 1442)")
                        injection_time = st.session_state.injection_time_state
                    else:
                        injection_time = st.session_state.injection_time_state
                else:
                    injection_time = st.time_input(
                        "注射时间 (GMT+8)",
                        value=st.session_state.injection_time_state,
                        key="injection_time_input"
                    )
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
    # Responsive layout that automatically adapts
    # Use JavaScript to detect screen size and set responsive layout
    st.markdown("""
    <script>
    function setMobileView() {
        const isMobile = window.innerWidth <= 768;
        const sessionState = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (sessionState) {
            sessionState.style.display = isMobile ? 'none' : 'block';
        }
    }
    window.addEventListener('resize', setMobileView);
    setMobileView();
    </script>
    """, unsafe_allow_html=True)

    # Mobile-optimized single column layout
    st.subheader("📊 血糖趋势")
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
        st.subheader("📊 最近统计")
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
        st.subheader("🔮 血糖预测")
        if len(data_filtered) >= 3:
            predictions = st.session_state.predictor.predict(data_filtered)
            fig_pred = create_prediction_plot(data_filtered, predictions)
            st.plotly_chart(fig_pred, use_container_width=True, height=350)
        else:
            st.info("需要至少3个血糖记录来进行预测")

        # Real-time predictions
        st.subheader("⏱️ 实时血糖预测")
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

    # Mobile-first design completed - all legacy desktop code removed

# Summary sections with tabbed navigation
st.markdown("---")
st.markdown("### 📊 记录摘要")

summary_tab1, summary_tab2, summary_tab3, summary_tab4 = st.tabs(["🩸 血糖记录", "🍽️ 饮食记录", "💉 胰岛素记录", "📋 综合摘要"])

with summary_tab1:
    st.subheader("血糖记录摘要")
    if not st.session_state.glucose_data.empty:
        glucose_data = st.session_state.glucose_data[st.session_state.glucose_data['glucose_level'] > 0].sort_values('timestamp', ascending=False)
        if not glucose_data.empty:
            display_glucose = glucose_data.copy()
            display_glucose['日期'] = display_glucose['timestamp'].dt.strftime('%Y-%m-%d')
            display_glucose['时间'] = display_glucose['timestamp'].dt.strftime('%H:%M')
            display_glucose['血糖 (mmol/L)'] = display_glucose['glucose_level'].apply(lambda x: f"{x/18.0182:.1f}")
            
            summary_glucose = display_glucose[['日期', '时间', '血糖 (mmol/L)']].head(20)
            st.dataframe(summary_glucose, use_container_width=True, height=400)
            
            # Statistics
            avg_glucose = display_glucose['glucose_level'].mean() / 18.0182
            max_glucose = display_glucose['glucose_level'].max() / 18.0182
            min_glucose = display_glucose['glucose_level'].min() / 18.0182
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("平均血糖", f"{avg_glucose:.1f} mmol/L")
            with col2:
                st.metric("最高血糖", f"{max_glucose:.1f} mmol/L")
            with col3:
                st.metric("最低血糖", f"{min_glucose:.1f} mmol/L")
        else:
            st.info("暂无血糖记录")
    else:
        st.info("暂无数据")

with summary_tab2:
    st.subheader("饮食记录摘要")
    if not st.session_state.glucose_data.empty:
        meal_data = st.session_state.glucose_data[
            (st.session_state.glucose_data['carbs'] > 0) & 
            (st.session_state.glucose_data['food_details'].str.len() > 0)
        ].sort_values('timestamp', ascending=False)
        
        if not meal_data.empty:
            display_meals = meal_data.copy()
            display_meals['日期'] = display_meals['timestamp'].dt.strftime('%Y-%m-%d')
            display_meals['时间'] = display_meals['timestamp'].dt.strftime('%H:%M')
            display_meals['碳水 (g)'] = display_meals['carbs'].apply(lambda x: f"{x:.1f}")
            
            summary_meals = display_meals[['日期', '时间', 'food_details', '碳水 (g)']].head(20)
            summary_meals.columns = ['日期', '时间', '食物详情', '碳水 (g)']
            st.dataframe(summary_meals, use_container_width=True, height=400)
            
            # Statistics
            total_carbs = display_meals['carbs'].sum()
            avg_carbs = display_meals['carbs'].mean()
            meal_count = len(display_meals)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总碳水摄入", f"{total_carbs:.1f} g")
            with col2:
                st.metric("平均每餐", f"{avg_carbs:.1f} g")
            with col3:
                st.metric("餐次统计", f"{meal_count} 次")
        else:
            st.info("暂无饮食记录")
    else:
        st.info("暂无数据")

with summary_tab3:
    st.subheader("胰岛素记录摘要")
    if not st.session_state.glucose_data.empty:
        insulin_data = st.session_state.glucose_data[st.session_state.glucose_data['insulin'] > 0].sort_values('timestamp', ascending=False)
        
        if not insulin_data.empty:
            display_insulin = insulin_data.copy()
            display_insulin['日期'] = display_insulin['timestamp'].dt.strftime('%Y-%m-%d')
            display_insulin['时间'] = display_insulin['timestamp'].dt.strftime('%H:%M')
            display_insulin['剂量 (单位)'] = display_insulin['insulin'].apply(lambda x: f"{x:.1f}")
            
            summary_insulin = display_insulin[['日期', '时间', '剂量 (单位)', 'insulin_type', 'injection_site']].head(20)
            summary_insulin.columns = ['日期', '时间', '剂量 (单位)', '胰岛素类型', '注射部位']
            st.dataframe(summary_insulin, use_container_width=True, height=400)
            
            # Statistics
            total_insulin = display_insulin['insulin'].sum()
            avg_insulin = display_insulin['insulin'].mean()
            injection_count = len(display_insulin)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总胰岛素用量", f"{total_insulin:.1f} 单位")
            with col2:
                st.metric("平均每次", f"{avg_insulin:.1f} 单位")
            with col3:
                st.metric("注射次数", f"{injection_count} 次")
                
            # Injection site analysis
            if 'injection_site' in display_insulin.columns:
                site_counts = display_insulin['injection_site'].value_counts()
                if not site_counts.empty:
                    st.write("注射部位分布:")
                    st.bar_chart(site_counts)
        else:
            st.info("暂无胰岛素记录")
    else:
        st.info("暂无数据")

with summary_tab4:
    st.subheader("每日综合摘要")
    if not st.session_state.glucose_data.empty:
        data_dates = pd.to_datetime(st.session_state.glucose_data['timestamp']).dt.date.unique()
        data_dates = sorted(data_dates, reverse=True)
        
        if data_dates:
            selected_date = st.selectbox(
                "选择日期查看摘要",
                options=data_dates,
                format_func=lambda x: x.strftime('%Y-%m-%d'),
                key="comprehensive_summary_date"
            )
            
            # Generate and display daily summary
            daily_summary = generate_daily_summary(selected_date)
            
            if daily_summary:
                st.text_area(
                    "每日摘要 (可复制)",
                    value=daily_summary,
                    height=300,
                    key="comprehensive_daily_summary"
                )
                
                # Show daily statistics
                daily_data = st.session_state.glucose_data[
                    pd.to_datetime(st.session_state.glucose_data['timestamp']).dt.date == selected_date
                ]
                
                if not daily_data.empty:
                    st.write("当日统计:")
                    col1, col2, col3 = st.columns(3)
                    
                    glucose_records = daily_data[daily_data['glucose_level'] > 0]
                    meal_records = daily_data[daily_data['carbs'] > 0]
                    insulin_records = daily_data[daily_data['insulin'] > 0]
                    
                    with col1:
                        st.metric("血糖记录", f"{len(glucose_records)} 次")
                    with col2:
                        st.metric("饮食记录", f"{len(meal_records)} 次")
                    with col3:
                        st.metric("胰岛素注射", f"{len(insulin_records)} 次")
            else:
                st.info("选择的日期没有记录")
        else:
            st.info("暂无数据可显示摘要")
    else:
        st.info("暂无数据可显示摘要")