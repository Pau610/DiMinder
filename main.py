import streamlit as st
import streamlit.components.v1 as components
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
    initial_sidebar_state="collapsed"
)

# PWA Meta tags and manifest for iOS app conversion
st.markdown("""
<!-- Basic PWA Meta Tags -->
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#1f77b4">
<meta name="description" content="专业的糖尿病健康数据管理和预测应用">

<!-- iOS Specific Meta Tags -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="我的日記">
<meta name="apple-touch-fullscreen" content="yes">
<meta name="format-detection" content="telephone=no">

<!-- Manifest -->
<link rel="manifest" href="/static/manifest.json">

<!-- iOS Icons -->
<link rel="apple-touch-icon" sizes="57x57" href="/generated-icon.png">
<link rel="apple-touch-icon" sizes="60x60" href="/generated-icon.png">
<link rel="apple-touch-icon" sizes="72x72" href="/generated-icon.png">
<link rel="apple-touch-icon" sizes="76x76" href="/generated-icon.png">
<link rel="apple-touch-icon" sizes="114x114" href="/generated-icon.png">
<link rel="apple-touch-icon" sizes="120x120" href="/generated-icon.png">
<link rel="apple-touch-icon" sizes="144x144" href="/generated-icon.png">
<link rel="apple-touch-icon" sizes="152x152" href="/generated-icon.png">
<link rel="apple-touch-icon" sizes="180x180" href="/generated-icon.png">

<!-- Splash screen meta tags for iOS -->
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-startup-image" href="/generated-icon.png">

<!-- Windows/Android -->
<meta name="msapplication-TileColor" content="#1f77b4">
<meta name="msapplication-TileImage" content="/generated-icon.png">
""", unsafe_allow_html=True)

# Initialize predictor and processor
try:
    if 'predictor' not in st.session_state:
        st.session_state.predictor = GlucosePredictor()
    if 'processor' not in st.session_state:
        st.session_state.processor = DataProcessor()
except Exception as e:
    st.error(f"初始化预测模型时发生错误: {str(e)}")

# Helper function for time input parsing
def parse_time_input(time_input, default_time=None):
    """Parse time input from various formats including 4-digit format"""
    if not time_input:
        return default_time or datetime.now(HK_TZ).time()
    
    # Remove any spaces and colons
    time_str = str(time_input).replace(" ", "").replace(":", "")
    
    try:
        # Handle 4-digit format (e.g., 1430 -> 14:30)
        if len(time_str) == 4 and time_str.isdigit():
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        
        # Handle 3-digit format (e.g., 930 -> 09:30)
        elif len(time_str) == 3 and time_str.isdigit():
            hour = int(time_str[0])
            minute = int(time_str[1:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        
        # Handle standard HH:MM format
        elif ":" in time_str:
            return datetime.strptime(time_str, "%H:%M").time()
    except:
        pass
    
    return default_time or datetime.now(HK_TZ).time()

def load_persistent_data():
    """Load data with offline protection and conflict resolution"""
    def create_empty_dataframe():
        return pd.DataFrame(columns=[
            'timestamp', 'glucose_level', 'carbs', 'insulin', 
            'insulin_type', 'injection_site', 'food_details'
        ])
    
    try:
        if os.path.exists('user_data.csv'):
            data = pd.read_csv('user_data.csv')
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            # Validate required columns exist
            required_columns = ['timestamp', 'glucose_level', 'carbs', 'insulin']
            if all(col in data.columns for col in required_columns):
                # Fill missing optional columns
                if 'insulin_type' not in data.columns:
                    data['insulin_type'] = ''
                if 'injection_site' not in data.columns:
                    data['injection_site'] = ''
                if 'food_details' not in data.columns:
                    data['food_details'] = ''
                return data
        
        # Recovery attempt from backup files
        backup_files = [f for f in os.listdir('.') if f.startswith('user_data_backup_') and f.endswith('.csv')]
        for backup_file in sorted(backup_files, reverse=True)[:3]:  # Try latest 3 backups
            try:
                data = pd.read_csv(backup_file)
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                st.warning(f"已从备份文件恢复数据: {backup_file}")
                return data
            except:
                continue
                
        return create_empty_dataframe()
    except Exception as e:
        st.error(f"数据加载错误: {str(e)}")
        return create_empty_dataframe()

def save_persistent_data():
    """Save current data to persistent storage with multiple backup layers"""
    try:
        if 'glucose_data' in st.session_state and not st.session_state.glucose_data.empty:
            # Create timestamped backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"user_data_backup_{timestamp}.csv"
            
            # Save main file
            st.session_state.glucose_data.to_csv('user_data.csv', index=False)
            
            # Save backup
            st.session_state.glucose_data.to_csv(backup_filename, index=False)
            
            # Clean old backups (keep only last 10)
            backup_files = [f for f in os.listdir('.') if f.startswith('user_data_backup_') and f.endswith('.csv')]
            if len(backup_files) > 10:
                backup_files.sort()
                for old_backup in backup_files[:-10]:
                    try:
                        os.remove(old_backup)
                    except:
                        pass
                        
    except Exception as e:
        st.error(f"数据保存错误: {str(e)}")

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
        
        # Meal record - show if there are actual food details (including 0g carbs)
        if (pd.notna(row['food_details']) and 
            str(row['food_details']).strip() != '' and
            row['food_details'] != ''):
            carbs_total = int(row['carbs']) if pd.notna(row['carbs']) and float(row['carbs']).is_integer() else (row['carbs'] if pd.notna(row['carbs']) else 0)
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
    st.session_state.selected_time = datetime.now(HK_TZ).time()

# Version and title display
col1, col2 = st.columns([1, 10])
with col1:
    st.caption("v2.1.0")
with col2:
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
                # Prepare text for JavaScript (escape special characters)
                escaped_summary = daily_summary.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')
                
                # Create header with copy button using Streamlit columns approach
                header_col1, header_col2 = st.columns([0.8, 0.2])
                with header_col1:
                    st.markdown("#### 每日摘要 (可复制)")
                with header_col2:
                    # Copy button using HTML component
                    components.html(f"""
                    <button onclick="copyToClipboard()" 
                            style="background: #ff4b4b; color: white; border: none; 
                                   border-radius: 4px; padding: 6px 12px; font-size: 12px; 
                                   cursor: pointer; width: 100%; margin-top: 8px;">
                        📋 复制
                    </button>
                    
                    <script>
                    function copyToClipboard() {{
                        const textToCopy = `{escaped_summary}`;
                        navigator.clipboard.writeText(textToCopy).then(function() {{
                            alert('每日摘要已复制到剪贴板！');
                        }}).catch(function(err) {{
                            console.error('Failed to copy: ', err);
                            // Fallback for older browsers
                            const textArea = document.createElement('textarea');
                            textArea.value = textToCopy;
                            document.body.appendChild(textArea);
                            textArea.select();
                            document.execCommand('copy');
                            document.body.removeChild(textArea);
                            alert('每日摘要已复制到剪贴板！');
                        }});
                    }}
                    </script>
                    """, height=50)
                
                # Summary text area without label
                st.text_area(
                    label="",
                    value=daily_summary,
                    height=200,
                    key="daily_summary_text",
                    label_visibility="collapsed"
                )
            else:
                st.info("选择的日期没有记录")
        else:
            st.info("暂无数据可显示摘要")
    else:
        st.info("暂无数据可显示摘要")

with col2:
    pass

# Manual Data Entry Section
st.markdown("### 📝 数据录入")

# Data type selection buttons
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
    # Blood glucose input
    st.markdown("#### 🩸 记录血糖")
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
        # Time input with text format and integrated clear
        time_input_col, clear_col = st.columns([0.8, 0.2])
        
        with time_input_col:
            # Initialize time string
            if 'glucose_time_str' not in st.session_state:
                st.session_state.glucose_time_str = datetime.now(HK_TZ).strftime("%H:%M")
            
            time_str = st.text_input(
                "记录时间 (GMT+8)",
                value=st.session_state.glucose_time_str,
                key="glucose_time_text",
                placeholder="HH:MM (例如: 14:30)",
                help="输入时间格式 HH:MM"
            )
            
            # Parse time string to time object
            try:
                record_time = datetime.strptime(time_str, "%H:%M").time()
                st.session_state.glucose_time_str = time_str
            except:
                st.error("时间格式错误，请使用 HH:MM 格式")
                record_time = datetime.now(HK_TZ).time()
        
        with clear_col:
            st.write("")  # Alignment spacing
            if st.button("清除", key="clear_glucose", help="重置为当前时间"):
                current_time = datetime.now(HK_TZ).strftime("%H:%M")
                st.session_state.glucose_time_str = current_time
                st.session_state.glucose_time_text = current_time
                st.rerun()

    glucose_mmol = st.number_input("血糖水平 (mmol/L)", min_value=2.0, max_value=22.0, value=None, step=0.1, key="glucose_level", placeholder="请输入血糖值")

    if st.button("添加血糖记录", use_container_width=True):
        if glucose_mmol is not None:
            record_datetime = datetime.combine(record_date, record_time)
            # Convert mmol/L to mg/dL for internal storage
            glucose_mgdl = glucose_mmol * 18.0182
            new_data = {
                'timestamp': record_datetime,
                'glucose_level': glucose_mgdl,
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
    st.markdown("#### 🍽️ 记录饮食")
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
        # Time input with text format and integrated clear
        time_input_col, clear_col = st.columns([0.8, 0.2])
        
        with time_input_col:
            # Initialize time string
            if 'meal_time_str' not in st.session_state:
                st.session_state.meal_time_str = datetime.now(HK_TZ).strftime("%H:%M")
            
            time_str = st.text_input(
                "用餐时间 (GMT+8)",
                value=st.session_state.meal_time_str,
                key="meal_time_text",
                placeholder="HH:MM (例如: 12:30)",
                help="输入时间格式 HH:MM"
            )
            
            # Parse time string to time object
            try:
                meal_time = datetime.strptime(time_str, "%H:%M").time()
                st.session_state.meal_time_str = time_str
            except:
                st.error("时间格式错误，请使用 HH:MM 格式")
                meal_time = datetime.now(HK_TZ).time()
        
        with clear_col:
            st.write("")  # Alignment spacing
            if st.button("清除", key="clear_meal", help="重置为当前时间"):
                current_time = datetime.now(HK_TZ).strftime("%H:%M")
                st.session_state.meal_time_str = current_time
                st.session_state.meal_time_text = current_time
                st.rerun()

    # Initialize food list
    if 'meal_foods' not in st.session_state:
        st.session_state.meal_foods = []

    # Add food input
    st.write("添加食物:")
    col_food, col_carbs, col_add = st.columns([3, 2, 1])
    
    with col_food:
        food_name = st.text_input("食物名称", key="food_name_input", placeholder="例如：米饭、面条、苹果...")
    
    with col_carbs:
        carbs_amount = st.number_input("碳水化合物 (克)", min_value=0.0, max_value=500.0, value=None, step=0.1, key="carbs_input", placeholder="请输入克数")
    
    with col_add:
        st.write("")  # Empty line for alignment
        if st.button("➕", key="add_food_btn", help="添加食物"):
            if food_name and carbs_amount is not None and carbs_amount >= 0:
                st.session_state.meal_foods.append({
                    'food': food_name,
                    'carbs': carbs_amount
                })
                st.rerun()

    # Display added foods
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
                # Clear food list
                st.session_state.meal_foods = []
                st.success(f"饮食记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
            else:
                st.error("数据保存失败，请重试")
    else:
        st.info("请添加食物后记录用餐")

elif st.session_state.input_type == 'insulin':
    # Insulin input
    st.markdown("#### 💉 记录胰岛素注射")
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
        # Time input with text format and integrated clear
        time_input_col, clear_col = st.columns([0.8, 0.2])
        
        with time_input_col:
            # Initialize time string
            if 'injection_time_str' not in st.session_state:
                st.session_state.injection_time_str = datetime.now(HK_TZ).strftime("%H:%M")
            
            time_str = st.text_input(
                "注射时间 (GMT+8)",
                value=st.session_state.injection_time_str,
                key="injection_time_text",
                placeholder="HH:MM (例如: 18:00)",
                help="输入时间格式 HH:MM"
            )
            
            # Parse time string to time object
            try:
                injection_time = datetime.strptime(time_str, "%H:%M").time()
                st.session_state.injection_time_str = time_str
            except:
                st.error("时间格式错误，请使用 HH:MM 格式")
                injection_time = datetime.now(HK_TZ).time()
        
        with clear_col:
            st.write("")  # Alignment spacing
            if st.button("清除", key="clear_injection", help="重置为当前时间"):
                current_time = datetime.now(HK_TZ).strftime("%H:%M")
                st.session_state.injection_time_str = current_time
                st.session_state.injection_time_text = current_time
                st.rerun()

    insulin_dose = st.number_input("胰岛素剂量 (单位)", min_value=0.0, max_value=100.0, value=None, step=0.5, key="insulin_dose", placeholder="请输入剂量")
    
    insulin_type = st.selectbox(
        "胰岛素类型",
        ["速效", "短效", "中效", "长效", "预混"],
        key="insulin_type_select"
    )
    
    injection_site = st.selectbox(
        "注射部位",
        ["腹部", "大腿", "上臂", "臀部"],
        key="injection_site_select"
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
            # Immediate save with validation
            save_persistent_data()
            # Verify save was successful
            if os.path.exists('user_data.csv'):
                st.success(f"胰岛素记录已保存！当前共有 {len(st.session_state.glucose_data)} 条记录")
            else:
                st.error("数据保存失败，请重试")
        else:
            st.error("请输入胰岛素剂量")

# Data visualization and analysis sections
if not st.session_state.glucose_data.empty:
    st.markdown("---")
    
    # Records display section
    st.markdown("### 📊 数据记录")
    
    # Date range filter
    if len(st.session_state.glucose_data) > 0:
        dates = pd.to_datetime(st.session_state.glucose_data['timestamp']).dt.date
        min_date = dates.min()
        max_date = dates.max()
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", min_date, min_value=min_date, max_value=max_date, key="start_date")
        with col2:
            end_date = st.date_input("结束日期", max_date, min_value=min_date, max_value=max_date, key="end_date")
        
        # Filter data by date range
        mask = (pd.to_datetime(st.session_state.glucose_data['timestamp']).dt.date >= start_date) & \
               (pd.to_datetime(st.session_state.glucose_data['timestamp']).dt.date <= end_date)
        filtered_data = st.session_state.glucose_data[mask]
        
        if not filtered_data.empty:
            # Create tabs for different record types
            tab1, tab2, tab3 = st.tabs(["血糖记录", "饮食记录", "胰岛素记录"])
            
            with tab1:
                st.markdown("#### 🩸 血糖记录")
                glucose_records = filtered_data[filtered_data['glucose_level'] > 0].sort_values('timestamp', ascending=False)
                
                if not glucose_records.empty:
                    for idx, row in glucose_records.iterrows():
                        glucose_mmol = round(row['glucose_level'] / 18.0182, 1)
                        
                        # Create inline layout with simple columns
                        col1, col2 = st.columns([0.9, 0.1])
                        with col1:
                            st.write(f"**{row['timestamp'].strftime('%Y-%m-%d %H:%M')}** | {glucose_mmol} mmol/L")
                        with col2:
                            if st.button("×", key=f"delete_glucose_{idx}"):
                                st.session_state[f"confirm_delete_glucose_{idx}"] = True
                        
                        # Show confirmation dialog if needed
                        if st.session_state.get(f"confirm_delete_glucose_{idx}", False):
                            st.warning("确定要删除此血糖记录吗？")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("确定删除", key=f"confirm_yes_glucose_{idx}", type="primary"):
                                    st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                    save_persistent_data()
                                    del st.session_state[f"confirm_delete_glucose_{idx}"]
                                    st.success("血糖记录已删除")
                                    st.rerun()
                            with col_no:
                                if st.button("取消", key=f"confirm_no_glucose_{idx}"):
                                    del st.session_state[f"confirm_delete_glucose_{idx}"]
                                    st.rerun()
                else:
                    st.info("选择的时间范围内没有血糖记录")
            
            with tab2:
                st.markdown("#### 🍽️ 饮食记录")
                meal_records = filtered_data[
                    (filtered_data['carbs'] > 0) | 
                    (pd.notna(filtered_data['food_details']) & (filtered_data['food_details'] != ''))
                ].sort_values('timestamp', ascending=False)
                
                if not meal_records.empty:
                    for idx, row in meal_records.iterrows():
                        food_details = row['food_details'] if pd.notna(row['food_details']) and row['food_details'] else '未记录详情'
                        
                        # Create inline layout with simple columns
                        col1, col2 = st.columns([0.9, 0.1])
                        with col1:
                            st.write(f"**{row['timestamp'].strftime('%Y-%m-%d %H:%M')}** | {row['carbs']:.1f}g")
                        with col2:
                            if st.button("×", key=f"delete_meal_{idx}"):
                                st.session_state[f"confirm_delete_meal_{idx}"] = True
                        
                        # Show confirmation dialog if needed
                        if st.session_state.get(f"confirm_delete_meal_{idx}", False):
                            st.warning("确定要删除此饮食记录吗？")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("确定删除", key=f"confirm_yes_meal_{idx}", type="primary"):
                                    st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                    save_persistent_data()
                                    del st.session_state[f"confirm_delete_meal_{idx}"]
                                    st.success("饮食记录已删除")
                                    st.rerun()
                            with col_no:
                                if st.button("取消", key=f"confirm_no_meal_{idx}"):
                                    del st.session_state[f"confirm_delete_meal_{idx}"]
                                    st.rerun()
                        
                        # Second line: food details
                        st.caption(f"  → {food_details}")
                else:
                    st.info("选择的时间范围内没有饮食记录")
            
            with tab3:
                st.markdown("#### 💉 胰岛素记录")
                insulin_records = filtered_data[filtered_data['insulin'] > 0].sort_values('timestamp', ascending=False)
                
                if not insulin_records.empty:
                    for idx, row in insulin_records.iterrows():
                        insulin_dose = int(row['insulin']) if float(row['insulin']).is_integer() else row['insulin']
                        
                        # Create inline layout with simple columns  
                        col1, col2 = st.columns([0.9, 0.1])
                        with col1:
                            st.write(f"**{row['timestamp'].strftime('%Y-%m-%d %H:%M')}** | {insulin_dose}U {row['insulin_type']}")
                        with col2:
                            if st.button("×", key=f"delete_insulin_{idx}"):
                                st.session_state[f"confirm_delete_insulin_{idx}"] = True
                        
                        # Show confirmation dialog if needed
                        if st.session_state.get(f"confirm_delete_insulin_{idx}", False):
                            st.warning("确定要删除此胰岛素记录吗？")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("确定删除", key=f"confirm_yes_insulin_{idx}", type="primary"):
                                    st.session_state.glucose_data = st.session_state.glucose_data.drop(idx).reset_index(drop=True)
                                    save_persistent_data()
                                    del st.session_state[f"confirm_delete_insulin_{idx}"]
                                    st.success("胰岛素记录已删除")
                                    st.rerun()
                            with col_no:
                                if st.button("取消", key=f"confirm_no_insulin_{idx}"):
                                    del st.session_state[f"confirm_delete_insulin_{idx}"]
                                    st.rerun()
                        
                        # Second line: injection site
                        st.caption(f"  → 注射部位: {row['injection_site']}")
                else:
                    st.info("选择的时间范围内没有胰岛素记录")
        else:
            st.info("选择的时间范围内没有记录")