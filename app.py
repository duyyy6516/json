import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px

# Cấu hình trang
st.set_page_config(page_title="JSON Data Pro", layout="wide")
st.title("📊 Công cụ Phân tích Dữ liệu")

# 1. Đồng nhất Key
def normalize_keys(data):
    if isinstance(data, list):
        return [normalize_keys(item) for item in data]
    elif isinstance(data, dict):
        return {str(k).strip().lower(): normalize_keys(v) for k, v in data.items()}
    return data

# 2. Làm phẳng JSON
def flatten_json(y):
    out = {}
    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x: 
                flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            i = 0
            for a in x:
                flatten(a, name + str(i) + '.')
                i += 1
        else: 
            out[name[:-1]] = x
    flatten(y)
    return out

# --- XỬ LÝ FILE UPLOAD ---
uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])

if uploaded_file is not None:
    try:
        raw_data = json.load(uploaded_file)
        if isinstance(raw_data, dict): 
            raw_data = [raw_data]
        
        clean_json = normalize_keys(raw_data)
        df = pd.DataFrame([flatten_json(row) for row in clean_json])
        
        df = df.dropna(axis=1, how='all').loc[:, ~df.columns.duplicated()]
        df = df.replace(r'^\s*$', np.nan, regex=True)
        display_df = df.fillna("")

        st.subheader(f"📋 Bảng dữ liệu gốc ({len(df)} bản ghi)")
        st.data_editor(display_df, use_container_width=True)
        
        st.divider()

        # --- THIẾT LẬP BIỂU ĐỒ ---
        st.subheader("⚙️ Thiết lập biểu đồ & Đối chiếu X-Y")
        
        time_col = next((col for col in df.columns if 'time' in col.lower() or 'thời gian' in col.lower()), None)
        start_d, end_d = None, None
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if time_col:
                t_dates = pd.to_datetime(df[time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), errors='coerce')
                valid_ts = t_dates.dropna()
                if not valid_ts.empty:
                    min_d, max_d = valid_ts.min().date(), valid_ts.max().date()
                    sel_date = st.date_input("Lọc theo ngày:", value=(min_d, max_d), min_value=min_d, max_value=max_d)
                    start_d, end_d = (sel_date[0], sel_date[1]) if len(sel_date) == 2 else (sel_date[0], sel_date[0])
            
            resample_choice = st.selectbox(
                "Làm mượt dữ liệu:",
                ["Nguyên bản", "Trung bình mỗi phút", "Trung bình mỗi 5 phút"]
            )
            resample_dict = {"Nguyên bản": None, "Trung bình mỗi phút": "1min", "Trung bình mỗi 5 phút": "5min"}

        with col2:
            exclude = [time_col, 'stt', 'tên khu', 'trạng thái', 'phương thức hoạt động', 'người điều khiển']
            numeric_options = [c for c in df.columns if c not in exclude and '_id' not in c]
            
            st.write("Chọn chỉ số vẽ biểu đồ:")
            cols_ui = st.columns(4)
            selected_keys = [k for i, k in enumerate(numeric_options) if cols_ui[i % 4].checkbox(k.upper(), key=f"c_{k}")]
            
            lock_zoom = st.checkbox("🔒 Khóa trượt (Chỉ cho phép Zoom)", value=True)

        # --- XỬ LÝ VÀ VẼ BIỂU ĐỒ ---
        if st.button("🚀 TẠO BIỂU ĐỒ & BẢNG ĐỐI CHIẾU", type="primary"):
            if not selected_keys:
                st.warning("Hãy chọn ít nhất 1 chỉ số!")
            else:
                working_df = df.copy()
                if time_col and start_d and end_d:
                    working_df[time_col] = pd.to_datetime(working_df[time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), errors='coerce')
