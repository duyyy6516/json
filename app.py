import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px

# Cấu hình trang
st.set_page_config(page_title="JSON Data Pro", layout="wide")
st.title("📊 Công cụ Phân tích Dữ liệu Chuyên sâu")

# --- 1. TỐI ƯU HÓA HIỆU NĂNG VỚI CACHE ---
@st.cache_data
def normalize_keys(data):
    if isinstance(data, list):
        return [normalize_keys(item) for item in data]
    elif isinstance(data, dict):
        return {str(k).strip().lower(): normalize_keys(v) for k, v in data.items()}
    return data

@st.cache_data
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

@st.cache_data
def load_and_process_data(file_bytes):
    raw_data = json.loads(file_bytes)
    if isinstance(raw_data, dict): 
        raw_data = [raw_data]
    clean_json = normalize_keys(raw_data)
    df = pd.DataFrame([flatten_json(row) for row in clean_json])
    df = df.dropna(axis=1, how='all').loc[:, ~df.columns.duplicated()]
    df = df.replace(r'^\s*$', np.nan, regex=True)
    return df

# --- XỬ LÝ FILE UPLOAD ---
uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])

if uploaded_file is not None:
    try:
        # Xử lý dữ liệu ban đầu
        file_bytes = uploaded_file.getvalue().decode("utf-8")
        df = load_and_process_data(file_bytes)
        display_df = df.fillna("")

        # --- TẠO 3 TABS ĐỘC LẬP ---
        tab1, tab2, tab3 = st.tabs(["🗂️ Bảng dữ liệu gốc", "📈 Biểu đồ Đơn", "📊 Biểu đồ Lồng nhau (So sánh)"])

        # -------------------------------------------------------------
        # TAB 1: HIỂN THỊ DỮ LIỆU
        # -------------------------------------------------------------
        with tab1:
            st.subheader(f"🗂️ Bảng dữ liệu gốc ({len(df)} bản ghi)")
            st.data_editor(display_df, use_container_width=True, key="editor_tab1")

        # -------------------------------------------------------------
        # TAB 2: VẼ BIỂU ĐỒ ĐƠN LẺ
        # -------------------------------------------------------------
        with tab2:
            st.subheader("⚙️ Thiết lập biểu đồ đơn lẻ")
            
            time_col = next((col for col in df.columns if 'time' in col.lower() or 'thời gian' in col.lower()), None)
            start_d, end_d = None, None
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if time_col:
                    t_dates = pd.to_datetime(df[time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), errors='coerce')
                    valid_ts = t_dates.dropna()
                    if not valid_ts.empty:
                        min_d, max_d = valid_ts.min().date(), valid_ts.max().date()
                        sel_date = st.date_input("Lọc theo ngày:", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="date_tab2")
                        start_d, end_d = (sel_date[0], sel_date[1]) if len(sel_date) == 2 else (sel_date[0], sel_date[0])
                
                resample_choice = st.selectbox(
                    "Làm mượt dữ liệu:", 
                    ["Nguyên bản", "Trung bình mỗi phút", "Trung bình mỗi 5 phút"], 
                    key="res_tab2"
                )
                resample_dict = {"Nguyên bản": None, "Trung bình mỗi phút": "1min", "Trung bình mỗi 5 phút": "5min"}

            with col2:
                exclude = [time_col, 'stt', 'tên khu', 'trạng thái', 'phương thức hoạt động', 'người điều khiển']
                numeric_options = [c for c in df.columns if c not in exclude and '_id' not in c]
                
                st.write("Chọn chỉ số vẽ biểu đồ:")
                cols_ui = st.columns(4)
                selected_keys = [k for i, k in enumerate(numeric_options) if cols_ui[i % 4].checkbox(k.upper(), key=f"c_tab2_{k}")]

            if st.button("🚀 TẠO BIỂU ĐỒ ĐƠN", type="primary", key="btn_tab2"):
                if not selected_keys:
                    st.warning("Hãy chọn ít nhất 1 chỉ số!")
                else:
                    working_df = df.copy()
                    if time_col and start_d and end_d:
                        working_df[time_col] = pd.to_datetime(working_df[time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), errors='coerce')
                        working_df = working_df.dropna(subset=[time_col])
                        mask = (working_df[time_col].dt.date >= start_d) & (working_df[time_col].dt.date <= end_d)
                        working_df = working_df[mask]

                    for col in selected_keys:
                        all_points = []
                        for idx, row in working_df.iterrows():
                            main_time = row[time_col]
                            val = str(row[col]).strip()
                            
                            if val and val.lower() != 'nan':
                                matches = re.findall(r'(\d{2}-\d{2}-\d{2})/([-+]?\d*\.?\d+)', val)
                                if matches:
                                    for t_str, v_str in matches:
                                        try:
                                            full_t_str = f"{main_time.strftime('%Y-%m-%d')} {t_str.replace('-', ':')}"
                                            all_points.append({'TG': pd.to_datetime(full_t_str), 'Giá trị': float(v_str)})
                                        except Exception:
                                            pass
                                else:
                                    num_match = re.search(r'[-+]?\d*\.?\d+', val)
                                    if num_match:
                                        all_points.append({'TG': main_time, 'Giá trị': float(num_match.group())})
                        
                        if all_points:
                            chart_df = pd.DataFrame(all_points)
                            rule = resample_dict[resample_choice]
                            
                            if rule:
                                plot_data = chart_df.set_index('TG').resample(rule)['Giá trị'].mean().dropna().reset_index()
                            else:
                                plot_data = chart_df.groupby('TG')['Giá trị'].mean().reset_index()

                            if not plot_data.empty:
                                plot_data = plot_data.sort_values(by='TG')
                                st.write(f"### Biểu đồ: {col.upper()}")
                                
                                num_points = len(plot_data)
                                use_webgl = 'webgl' if num_points > 1000 else 'svg'
                                show_markers = num_points <= 1000 

                                fig = px.line(plot_data, x='TG', y='Giá trị', markers=show_markers, render_mode=use_webgl)
                                fig.update_layout(
                                    xaxis_title="Thời gian (TG)",
                                    yaxis_title=f"Giá trị ({col.upper()})",
                                    hovermode="x unified",
                                    dragmode='pan',
                                    xaxis=dict(rangeslider=dict(visible=False), type="date")
                                )
                                
                                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
                                
                                with st.expander(f"Xem chi tiết {num_points} điểm dữ liệu cho {col.upper()}"):
                                    st.dataframe(plot_data, use_container_width=True)
                                st.write("---")

        # -------------------------------------------------------------
        # TAB 3: VẼ BIỂU ĐỒ LỒNG NHAU (SO SÁNH MULTI-LINE)
        # -------------------------------------------------------------
        with tab3:
            st.subheader("⚙️ Thiết lập biểu đồ đối chiếu lồng nhau")
            st.info("Chức năng này gộp các chỉ số bạn tích chọn vào cùng một biểu đồ để so sánh sự tương quan theo thời gian.")

            time_col_multi = next((col for col in df.columns if 'time' in col.lower() or 'thời gian' in col.lower()), None)
            exclude_m = [time_col_multi, 'stt', 'tên khu', 'trạng thái', 'phương thức hoạt động', 'người điều khiển']
            numeric_opts_multi = [c for c in df.columns if c not in exclude_m and '_id' not in c]

            col1_m, col2_m = st.columns([1, 2])
            
            with col1_m:
                st.write("🎯 **1. Chọn các chỉ số (tích vào ô vuông):**")
                check_multi_ui = st.columns(3)
                selected_comparison_keys = [k for i, k in enumerate(numeric_opts_multi) if check_multi_ui[i % 3].checkbox(k.upper(), key=f"c_multi_{k}")]

            with col2_m:
                st.write("✨ **2. Tùy chỉnh biểu đồ:**")
                start_d_m, end_d_m = None, None
                if time_col_multi:
                    t_dates_m = pd.to_datetime(df[time_col_multi].astype(str).str.replace('-', ':').str.replace(':', '-', 2), errors='coerce')
                    valid_ts_m = t_dates_m.dropna()
                    if not valid_ts_m.empty:
                        min_d_m, max_d_m = valid_ts_m.min().date(), valid_ts_m.max().date()
                        sel_date_m = st.date_input("Lọc theo ngày:", value=(min_d_m, max_d_m), min_value=min_d_m, max_value=max_d_m, key="date_multi")
                        start_d_m, end_d_m = (sel_date_m[0], sel_date_m[1]) if len(sel_date_m) == 2 else (sel_date_m[0], sel_date_m[0])

                res_choice_multi = st.selectbox(
                    "Làm mượt dữ liệu:", 
                    ["Nguyên bản (Khuyên dùng cho chi tiết)", "Trung bình mỗi phút", "Trung bình mỗi 5 phút"], 
                    key="res_multi"
                )
                r_dict_multi = {"Nguyên bản (Khuyên dùng cho chi tiết)": None, "Trung bình mỗi phút": "1min", "Trung bình mỗi 5 phút": "5min"}
                
                normalize_scale = st.checkbox("⚖️ Tự động cân bằng tỷ lệ (Đưa về thang 0-100%) để chống đè đường vẽ", value=True)

            if st.button("🚀 TẠO BIỂU ĐỒ ĐỐI CHIẾU", type="primary", key="btn_multi"):
                if len(selected_comparison_keys) < 2:
                    st.warning("Hãy tích chọn ít nhất 2 chỉ số để lồng vào nhau!")
                else:
                    all_multi_points = []
                    working_df_multi = df.copy()
                    
                    if time_col_multi and start_d_m and end_d_m:
                        working_df_multi[time_col_multi] = pd.to_datetime(working_df_multi[time_col_multi].astype(str).str.replace('-', ':').str.replace(':', '-', 2), errors='coerce')
                        working_df_multi = working_df_multi.dropna(subset=[time_col_multi])
                        mask_m = (working_df_multi[time_col_multi].dt.date >= start_d_m) & (working_df_multi[time_col_multi].dt.date <= end_d_m)
                        working_df_multi = working_df_multi[mask_m]

                    for col in selected_comparison_keys:
                        for idx, row in working_df_multi.iterrows():
                            main_time = row[time_col_multi]
                            val = str(row[col]).strip()
                            
                            if val and val.lower() != 'nan':
                                matches = re.findall(r'(\d{2}-\d{2}-\d{2})/([-+]?\d*\.?\d+)', val)
                                if matches:
                                    for t_str, v_str in matches:
                                        try:
                                            full_t_str = f"{main_time.strftime('%Y-%m-%d')} {t_str.replace('-', ':')}"
                                            all_multi_points.append({'TG': pd.to_datetime(full_t_str), 'Giá trị': float(v_str), 'Loại chỉ số': col.upper()})
                                        except Exception: 
                                            pass
                                else:
                                    num_match = re.search(r'[-+]?\d*\.?\d+', val)
                                    if num_match:
                                        all_multi_points.append({'TG': main_time, 'Giá trị': float(num_match.group()), 'Loại chỉ số': col.upper()})
                    
                    if all_multi_points:
                        multi_chart_df = pd.DataFrame(all_multi_points)
                        rule_multi = r_dict_multi[res_choice_multi]
                        
                        if rule_multi:
                            plot_data_multi = multi_chart_df.set_index('TG').groupby('Loại chỉ số')['Giá trị'].resample(rule_multi).mean().dropna().reset_index()
                        else:
                            plot_data_multi = multi_chart_df.groupby(['TG', 'Loại chỉ số'])['Giá trị'].mean().reset_index()

                        if not plot_data_multi.empty:
                            plot_data_multi = plot_data_multi.sort_values(by='TG')
                            yaxis_label = "Giá trị đo (Thực tế)"
                            
                            if normalize_scale:
                                plot_data_multi['Giá trị hiển thị'] = plot_data_multi.groupby('Loại chỉ số')['Giá trị'].transform(
                                    lambda x: (x - x.min()) / (x.max() - x.min()) * 100 if x.max() != x.min() else (x * 0 + 50)
                                )
                                y_target = 'Giá trị hiển thị'
                                yaxis_label = "Mức độ biến thiên (%)"
                            else:
                                y_target = 'Giá trị'

                            st.write(f"### Biểu đồ so sánh đối chiếu")
                            
                            num_multi_points = len(plot_data_multi)
                            use_webgl_multi = 'webgl' if num_multi_points > 2000 else 'svg'
                            show_markers_multi = num_multi_points <= 1000

                            fig_multi = px.line(
                                plot_data_multi, 
                                x='TG', 
                                y=y_target, 
                                color='Loại chỉ số', 
                                markers=show_markers_multi,
                                custom_data=['Giá trị'],
                                render_mode=use_webgl_multi
                            )
                            
                            if normalize_scale:
                                fig_multi.update_traces(hovertemplate="<b>Thời gian:</b> %{x}<br><b>Giá trị gốc:</b> %{customdata[0]:.2f}<br><b>Biến thiên:</b> %{y:.1f}%")
                            else:
                                fig_multi.update_traces(hovertemplate="<b>Thời gian:</b> %{x}<br><b>Giá trị:</b> %{y:.2f}")
                                
                            fig_multi.update_layout(
                                xaxis_title="Thời gian (TG)", 
                                yaxis_title=yaxis_label,
                                hovermode="x unified", 
                                dragmode='pan',
                                xaxis=dict(rangeslider=dict(visible=False), type="date")
                            )
                            
                            st.plotly_chart(fig_multi, use_container_width=True, config={'scrollZoom': True})

                            with st.expander(f"Xem bảng dữ liệu so sánh ({num_multi_points} điểm)"):
                                st.dataframe(plot_data_multi, use_container_width=True)
                        else:
                            st.error("Dữ liệu sau khi xử lý bị rỗng.")
                    else:
                        st.warning("Không tìm thấy dữ liệu số hợp lệ trong thời gian đã chọn cho các chỉ số này.")

    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
