import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px

# Cấu hình trang
st.set_page_config(page_title="JSON Data Pro", layout="wide", page_icon="📊")

# Custom CSS để giao diện đẹp hơn
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 1. Hàm Đồng nhất Key
def normalize_keys(data):
    if isinstance(data, list):
        return [normalize_keys(item) for item in data]
    elif isinstance(data, dict):
        return {str(k).strip().lower(): normalize_keys(v) for k, v in data.items()}
    return data

# 2. Hàm Làm phẳng JSON
def flatten_json(y):
    out = {}
    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x: flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            i = 0
            for a in x:
                flatten(a, name + str(i) + '.')
                i += 1
        else: out[name[:-1]] = x
    flatten(y)
    return out

st.title("📊 JSON Data Pro: Phân tích Dữ liệu")

# --- SIDEBAR CẤU HÌNH ---
with st.sidebar:
    st.header("⚙️ Tải & Cấu hình")
    uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])
    st.divider()
    resample_choice = st.selectbox("Làm mượt dữ liệu:", ["Nguyên bản", "Trung bình mỗi phút", "Trung bình mỗi 5 phút"])
    resample_dict = {"Nguyên bản": None, "Trung bình mỗi phút": "1min", "Trung bình mỗi 5 phút": "5min"}

# --- XỬ LÝ CHÍNH ---
if uploaded_file is not None:
    try:
        with st.spinner("Đang xử lý dữ liệu..."):
            raw_data = json.load(uploaded_file)
            if isinstance(raw_data, dict): raw_data = [raw_data]
            clean_json = normalize_keys(raw_data)
            df = pd.DataFrame([flatten_json(row) for row in clean_json])
            df = df.dropna(axis=1, how='all').loc[:, ~df.columns.duplicated()]
            df = df.replace(r'^\s*$', np.nan, regex=True)

        st.success(f"Đã tải thành công {len(df)} bản ghi.")
        
        # Lấy cột thời gian
        time_col = next((col for col in df.columns if 'time' in col.lower() or 'thời gian' in col.lower()), None)
        
        col1, col2 = st.columns([1, 2])
        start_d, end_d = None, None
        
        with col1:
            if time_col:
                t_dates = pd.to_datetime(df[time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), errors='coerce')
                valid_ts = t_dates.dropna()
                if not valid_ts.empty:
                    min_d, max_d = valid_ts.min().date(), valid_ts.max().date()
                    sel_date = st.date_input("Lọc theo ngày:", value=(min_d, max_d), min_value=min_d, max_value=max_d)
                    start_d, end_d = (sel_date[0], sel_date[1]) if len(sel_date) == 2 else (sel_date[0], sel_date[0])

        with col2:
            exclude = [time_col, 'stt', 'tên khu', 'trạng thái', 'phương thức hoạt động', 'người điều khiển']
            numeric_options = [c for c in df.columns if c not in exclude and '_id' not in c]
            selected_keys = st.multiselect("Chọn các chỉ số (vẽ lồng):", numeric_options)

        # --- VẼ BIỂU ĐỒ LỒNG ---
        if st.button("🚀 TẠO BIỂU ĐỒ SO SÁNH", type="primary"):
            if not selected_keys:
                st.warning("Hãy chọn ít nhất 1 chỉ số!")
            else:
                all_combined_data = []
                working_df = df.copy()
                
                # Filter thời gian
                if time_col and start_d and end_d:
                    working_df[time_col] = pd.to_datetime(working_df[time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), errors='coerce')
                    working_df = working_df.dropna(subset=[time_col])
                    mask = (working_df[time_col].dt.date >= start_d) & (working_df[time_col].dt.date <= end_d)
                    working_df = working_df[mask]

                # Thu thập dữ liệu
                for col in selected_keys:
                    for idx, row in working_df.iterrows():
                        main_time = row[time_col]
                        val = str(row[col]).strip()
                        if val and val.lower() != 'nan':
                            matches = re.findall(r'(\d{2}-\d{2}-\d{2})/([-+]?\d*\.?\d+)', val)
                            if matches:
                                for t_str, v_str in matches:
                                    try:
                                        full_t_str = f"{main_time.strftime('%Y-%m-%d')} {t_str.replace('-', ':')}"
                                        all_combined_data.append({'TG': pd.to_datetime(full_t_str), 'Giá trị': float(v_str), 'Chỉ số': col.upper()})
                                    except: pass
                            else:
                                num_match = re.search(r'[-+]?\d*\.?\d+', val)
                                if num_match:
                                    all_combined_data.append({'TG': main_time, 'Giá trị': float(num_match.group()), 'Chỉ số': col.upper()})

                if all_combined_data:
                    combined_df = pd.DataFrame(all_combined_data)
                    rule = resample_dict[resample_choice]
                    
                    if rule:
                        plot_df = combined_df.set_index('TG').groupby('Chỉ số').resample(rule)['Giá trị'].mean().reset_index()
                    else:
                        plot_df = combined_df.groupby(['TG', 'Chỉ số'])['Giá trị'].mean().reset_index()

                    st.subheader("📈 Phân tích tương quan")
                    fig = px.line(plot_df, x='TG', y='Giá trị', color='Chỉ số', markers=True)
                    fig.update_layout(
                        hovermode="x unified",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        dragmode='pan'
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
                else:
                    st.error("Không tìm thấy dữ liệu số hợp lệ.")
    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
else:
    st.info("Vui lòng tải lên file JSON tại thanh bên trái.")
