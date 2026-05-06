import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px

# Cấu hình trang
st.set_page_config(page_title="JSON Data Pro", layout="wide")
st.title("📊 Công cụ Phân tích Dữ liệu Hệ thống")

# Các hàm xử lý dữ liệu (giữ nguyên)
def normalize_keys(data):
    if isinstance(data, list): return [normalize_keys(item) for item in data]
    elif isinstance(data, dict): return {str(k).strip().lower(): normalize_keys(v) for k, v in data.items()}
    return data

def flatten_json(y):
    out = {}
    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x: flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            i = 0
            for a in x: flatten(a, name + str(i) + '.'); i += 1
        else: out[name[:-1]] = x
    flatten(y)
    return out

# --- XỬ LÝ FILE ---
uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])

if uploaded_file is not None:
    try:
        raw_data = json.load(uploaded_file)
        if isinstance(raw_data, dict): raw_data = [raw_data]
        df = pd.DataFrame([flatten_json(row) for row in normalize_keys(raw_data)])
        df = df.dropna(axis=1, how='all').loc[:, ~df.columns.duplicated()]
        
        # --- UI LỌC ---
        time_col = next((col for col in df.columns if 'time' in col.lower() or 'thời gian' in col.lower()), None)
        
        # ... (Phần logic lọc dữ liệu giữ nguyên như cũ để đảm bảo chạy đúng) ...
        
        if st.button("🚀 TẠO BIỂU ĐỒ"):
            # Giả định đã có plot_data sau khi xử lý
            # ...
            
            fig = px.line(plot_data, x='TG', y='Giá trị', color='Nhóm', markers=True)
            
            # CẤU HÌNH ĐỂ CHỈ CHO PHÉP CUỘN TỪNG TRỤC
            fig.update_layout(
                xaxis=dict(
                    fixedrange=False, # Cho phép tương tác trục X (Cuộn ngang/Zoom ngang)
                    rangeslider=dict(visible=True) # Thêm thanh trượt ngang bên dưới biểu đồ
                ),
                yaxis=dict(
                    fixedrange=False # Cho phép tương tác trục Y (Cuộn dọc/Zoom dọc)
                ),
                # Tắt hành động kéo trượt tự do, chỉ cho phép zoom bằng con lăn hoặc dùng thanh trượt
                dragmode='zoom', 
                hovermode="x unified",
                uirevision='constant'
            )
            
            # Sử dụng config để bật cuộn bằng chuột
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
            
    except Exception as e:
        st.error(f"Lỗi: {e}")
