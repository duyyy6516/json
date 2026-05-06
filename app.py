import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px

# Cấu hình trang
st.set_page_config(page_title="JSON Data Analytics", layout="wide")
st.title("📊 Công cụ Phân tích Dữ liệu Cảm biến")

# 1. Đồng nhất Key (Chuyển hết về chữ thường)
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
            for a in x: flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            i = 0
            for a in x:
                flatten(a, name + str(i) + '.')
                i += 1
        else: out[name[:-1]] = x
    flatten(y)
    return out

# --- XỬ LÝ FILE UPLOAD ---
uploaded_file = st.file_uploader("Tải lên file JSON chứa dữ liệu EC/PH/Lưu lượng", type=['json'])

if uploaded_file is not None:
    try:
        raw_data = json.load(uploaded_file)
        if isinstance(raw_data, dict): raw_data = [raw_data]
        
        clean_json = normalize_keys(raw_data)
        df = pd.DataFrame([flatten_json(row) for row in clean_json])
        
        # Dọn dẹp cột trống
        df = df.dropna(axis=1, how='all').loc[:, ~df.columns.duplicated()]
        display_df = df.fillna("")

        st.subheader(f"📋 Dữ liệu thô ({len(df)} bản ghi)")
        st.data_editor(display_df, use_container_width=True)
        
        st.divider()

        # --- THIẾT LẬP BIỂU ĐỒ ---
        st.subheader("⚙️ Cấu hình vẽ biểu đồ")
        
        # Tìm cột thời gian gốc
        time_col = next((col for col in df.columns if 'time' in col.lower() or 'thời gian' in col.lower()), None)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            resample_choice = st.selectbox(
                "Chế độ hiển thị:",
                ["Nguyên bản (Từng điểm)", "Trung bình mỗi phút", "Trung bình mỗi 5 phút"]
            )
            resample_dict = {"Nguyên bản (Từng điểm)": None, "Trung bình mỗi phút": "1min", "Trung bình mỗi 5 phút": "5min"}

        with col2:
            # Các cột không dùng để vẽ biểu đồ
            exclude = [time_col, 'stt', 'tên khu', 'trạng thái', 'phương thức hoạt động', 'người điều khiển']
            numeric_options = [c for c in df.columns if c not in exclude and '_id' not in c]
            
            st.write("Chọn chỉ số cần xem (Có thể chọn EC, PH hoặc Lưu lượng):")
            cols_ui = st.columns(4)
            selected_keys = [k for i, k in enumerate(numeric_options) if cols_ui[i % 4].checkbox(k.upper(), key=f"c_{k}")]

        # --- XỬ LÝ DỮ LIỆU PHỨC TẠP (EC/PH STRING) ---
        if st.button("🚀 XỬ LÝ VÀ VẼ BIỂU ĐỒ", type="primary"):
            if not selected_keys:
                st.warning("Vui lòng chọn ít nhất một chỉ số để vẽ!")
            elif not time_col:
                st.error("Không tìm thấy cột Thời gian trong file để làm mốc!")
            else:
                # Chuyển đổi cột thời gian gốc sang định dạng chuẩn
                working_df = df.copy()
                working_df[time_col] = pd.to_datetime(
                    working_df[time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), 
                    errors='coerce'
                )
                working_df = working_df.dropna(subset=[time_col])

                for col in selected_keys:
                    all_points = []
                    for _, row in working_df.iterrows():
                        base_time = row[time_col]
                        val_str = str(row[col]).strip()
                        
                        if not val_str or val_str.lower() == 'nan':
                            continue

                        # Regex tìm mẫu HH-MM-SS/Value hoặc HH:MM:SS/Value (Cho EC, PH)
                        complex_matches = re.findall(r'(\d{2}[-:]\d{2}[-:]\d{2})/([-+]?\d*\.?\d+)', val_str)
                        
                        if complex_matches:
                            for t_part, v_part in complex_matches:
                                try:
                                    # Ghép ngày từ cột Thời gian với giờ từ chuỗi EC/PH
                                    time_str = f"{base_time.strftime('%Y-%m-%d')} {t_part.replace('-', ':')}"
                                    all_points.append({
                                        'Thời gian': pd.to_datetime(time_str),
                                        'Giá trị': float(v_part)
                                    })
                                except: pass
                        else:
                            # Nếu là số đơn lẻ (Lưu lượng tổng, Lưu lượng m2/h)
                            simple_match = re.search(r'[-+]?\d*\.?\d+', val_str)
                            if simple_match:
                                all_points.append({
                                    'Thời gian': base_time,
                                    'Giá trị': float(simple_match.group())
                                })

                    if all_points:
                        chart_df = pd.DataFrame(all_points).sort_values('Thời gian')
                        rule = resample_dict[resample_choice]
                        
                        if rule:
                            plot_data = chart_df.set_index('Thời gian').resample(rule)['Giá trị'].mean().dropna().reset_index()
                        else:
                            plot_data = chart_df.groupby('Thời gian')['Giá trị'].mean().reset_index()

                        if not plot_data.empty:
                            st.write(f"### Biểu đồ chỉ số: {col.upper()}")
                            fig = px.line(plot_data, x='Thời gian', y='Giá trị', markers=True, template="plotly_white")
                            fig.update_layout(
                                xaxis_title="Thời gian hệ thống",
                                yaxis_title=col.upper(),
                                dragmode='zoom',
                                hovermode="x unified"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                            with st.expander(f"Chi tiết bảng dữ liệu {col.upper()}"):
                                st.dataframe(plot_data, use_container_width=True)
                    else:
                        st.info(f"Không trích xuất được dữ liệu số từ cột: {col.upper()}")
                    st.write("---")

    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
