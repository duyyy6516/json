import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px
import io

# ==============================================================================
# --- CẤU HÌNH TRANG & THÔNG SỐ TỐI ƯU ---
# ==============================================================================
st.set_page_config(page_title="JSON Data Pro", layout="wide", page_icon="🌱")
st.title("🌱 Công cụ Phân tích Dữ liệu Nông Nghiệp")

# Cấu hình khoảng dữ liệu "Đẹp" (loại bỏ nhiễu, lỗi cảm biến, ngoài khoảng)
KHOANG_TOI_UU = {
    # Môi trường Không khí
    'TEMPKK': (10.0, 45.0),         # Nhiệt độ không khí hợp lý (10 - 45 °C)
    'HUMIKK': (20.0, 100.0),        # Độ ẩm không khí (20% - 100%)
    'SOIL_ASKK': (0, 100000),       # Cường độ ánh sáng môi trường
    'AS': (0, 100000),              # Cường độ ánh sáng lúc tưới

    # Môi trường Đất (Dữ liệu đang nhân 10 hoặc 100 từ cảm biến)
    'NHIỆT ĐỘ': (100.0, 500.0),     # Tương đương 10°C - 50°C
    'ĐỘ ẨM': (0.0, 100.0),          # Tương đương 0% - 100%
    
    # Dinh dưỡng Nước & Đất
    'PH': (400.0, 800.0),           # Tương đương pH 4.0 - 8.0
    'EC': (500.0, 4000.0),          # Tương đương 0.5 - 4.0 mS/cm
    'N': (0.0, 500.0),              # Nitơ
    'P': (0.0, 500.0),              # Phốt pho
    'K': (0.0, 500.0)               # Kali
}

# ==============================================================================
# 1. CÁC HÀM XỬ LÝ LÕI (CÓ CACHE)
# ==============================================================================
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
            for i, a in enumerate(x):
                flatten(a, name + str(i) + '.')
        else:
            out[name[:-1]] = x
    flatten(y)
    return out

@st.cache_data
def load_and_process_data(file_bytes):
    try:
        raw_data = json.loads(file_bytes)
    except json.JSONDecodeError:
        raise ValueError("File tải lên không đúng định dạng JSON hợp lệ.")
        
    if isinstance(raw_data, dict): 
        raw_data = [raw_data]
    
    clean_json = normalize_keys(raw_data)
    df = pd.DataFrame([flatten_json(row) for row in clean_json])
    df = df.dropna(axis=1, how='all').loc[:, ~df.columns.duplicated()]
    df = df.replace(r'^\s*$', np.nan, regex=True)
    
    # Chuẩn hóa thời gian
    time_col = next((col for col in df.columns if 'time' in col.lower() or 'thời gian' in col.lower()), None)
    if time_col:
        df['_parsed_time'] = pd.to_datetime(
            df[time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), 
            errors='coerce'
        )
    return df, time_col

# ==============================================================================
# 2. CÁC HÀM TIỆN ÍCH CHO BIỂU ĐỒ
# ==============================================================================
def extract_sensor_data(df, selected_cols):
    records = []
    cols_to_extract = ['_parsed_time'] + selected_cols
    working_df = df[cols_to_extract].dropna(subset=['_parsed_time'])
    
    for row in working_df.itertuples(index=False):
        main_time = row[0] # Cột _parsed_time
        for i, col_name in enumerate(selected_cols, start=1):
            val = str(row[i]).strip()
            if not val or val.lower() == 'nan':
                continue
                
            matches = re.findall(r'(\d{2}-\d{2}-\d{2})/([-+]?\d*\.?\d+)', val)
            if matches:
                for t_str, v_str in matches:
                    try:
                        full_t_str = f"{main_time.strftime('%Y-%m-%d')} {t_str.replace('-', ':')}"
                        records.append({
                            'TG': pd.to_datetime(full_t_str), 
                            'Giá trị': float(v_str), 
                            'Chỉ số': col_name.upper()
                        })
                    except Exception:
                        pass
            else:
                num_match = re.search(r'[-+]?\d*\.?\d+', val)
                if num_match:
                    records.append({
                        'TG': main_time, 
                        'Giá trị': float(num_match.group()), 
                        'Chỉ số': col_name.upper()
                    })
                    
    return pd.DataFrame(records)

def generate_chart(df, title, is_multi=False):
    num_points = len(df)
    use_webgl = 'webgl' if num_points > 1000 else 'svg'
    show_markers = num_points <= 1000 
    
    if is_multi:
        fig = px.line(df, x='TG', y='Giá trị', color='Chỉ số', markers=show_markers, render_mode=use_webgl)
    else:
        fig = px.line(df, x='TG', y='Giá trị', markers=show_markers, render_mode=use_webgl)
        
    fig.update_layout(
        title=f"<b>{title}</b>",
        xaxis_title="Thời gian (TG)",
        yaxis_title="Giá trị",
        hovermode="x unified",
        dragmode='pan',
        xaxis=dict(rangeslider=dict(visible=False), type="date")
    )
    
    fig.update_xaxes(showspikes=True, spikecolor="gray", spikesnap="cursor", spikemode="across")
    fig.update_yaxes(showspikes=True, spikecolor="gray", spikemode="across")
    
    return fig, num_points

# ==============================================================================
# 3. XỬ LÝ GIAO DIỆN & FILE UPLOAD
# ==============================================================================
uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])

if uploaded_file is not None:
    try:
        with st.spinner("Đang xử lý dữ liệu..."):
            file_bytes = uploaded_file.getvalue().decode("utf-8")
            df, time_col = load_and_process_data(file_bytes)
            display_df = df.drop(columns=['_parsed_time'], errors='ignore').fillna("")

        min_d, max_d = None, None
        if '_parsed_time' in df.columns:
            valid_ts = df['_parsed_time'].dropna()
            if not valid_ts.empty:
                min_d, max_d = valid_ts.min().date(), valid_ts.max().date()

        exclude = [time_col, 'stt', 'tên khu', 'trạng thái', 'phương thức hoạt động', 'người điều khiển', '_parsed_time']
        numeric_options = [c for c in df.columns if c not in exclude and '_id' not in c]

        tab1, tab2, tab3 = st.tabs(["🗂️ Bảng dữ liệu gốc", "📈 Biểu đồ Đơn (Lọc sạch)", "📊 Biểu đồ Lồng nhau"])

        # --- TAB 1: DỮ LIỆU GỐC ---
        with tab1:
            col_head1, col_head2 = st.columns([3, 1])
            with col_head1:
                st.subheader(f"Bảng dữ liệu gốc ({len(df)} bản ghi)")
            with col_head2:
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Tải xuống CSV", data=csv, file_name='data_export.csv',
                    mime='text/csv', use_container_width=True
                )
            st.dataframe(display_df, use_container_width=True)

        # --- TAB 2: BIỂU ĐỒ ĐƠN LẺ ---
        with tab2:
            st.subheader("⚙️ Thiết lập biểu đồ đơn lẻ")
            col1, col2 = st.columns([1, 2])
            with col1:
                sel_date_2 = st.date_input("Lọc theo ngày:", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="date_tab2") if min_d else None
                start_d_2 = sel_date_2[0] if sel_date_2 else None
                end_d_2 = sel_date_2[1] if sel_date_2 and len(sel_date_2) == 2 else start_d_2
                
                res_choice_2 = st.selectbox("Làm mượt dữ liệu:", ["Nguyên bản", "Trung bình mỗi phút", "Trung bình mỗi 5 phút"], key="res_tab2")
                r_dict = {"Nguyên bản": None, "Trung bình mỗi phút": "1min", "Trung bình mỗi 5 phút": "5min"}

            with col2:
                st.write("Chọn chỉ số vẽ biểu đồ:")
                cols_ui = st.columns(4)
                selected_keys_2 = [k for i, k in enumerate(numeric_options) if cols_ui[i % 4].checkbox(k.upper(), key=f"c_tab2_{k}")]

            if st.button("🚀 TẠO BIỂU ĐỒ ĐƠN", type="primary", key="btn_tab2"):
                if not selected_keys_2:
                    st.warning("Hãy chọn ít nhất 1 chỉ số!")
                elif not time_col:
                    st.error("Dữ liệu không có cột thời gian hợp lệ.")
                else:
                    mask = (df['_parsed_time'].dt.date >= start_d_2) & (df['_parsed_time'].dt.date <= end_d_2)
                    filtered_df = df[mask]
                    chart_df = extract_sensor_data(filtered_df, selected_keys_2)
                    
                    if not chart_df.empty:
                        rule = r_dict[res_choice_2]
                        if start_d_2 and end_d_2 and (end_d_2 - start_d_2).days > 7 and not rule:
                            rule = "5min"

                        for col in selected_keys_2:
                            sub_df = chart_df[chart_df['Chỉ số'] == col.upper()]
                            if sub_df.empty: continue
                            
                            ten_chi_so = col.upper()
                            
                            # ========================================================
                            # LỌC DỮ LIỆU SẠCH CHO TAB 2
                            # ========================================================
                            if ten_chi_so in KHOANG_TOI_UU:
                                min_val, max_val = KHOANG_TOI_UU[ten_chi_so]
                                sub_df = sub_df[(sub_df['Giá trị'] >= min_val) & (sub_df['Giá trị'] <= max_val)]
                                
                                if sub_df.empty:
                                    st.warning(f"⚠️ {ten_chi_so}: Toàn bộ dữ liệu nằm ngoài khoảng chuẩn, đã bị loại bỏ!")
                                    continue
                            # ========================================================
                            
                            if rule:
                                plot_data = sub_df.set_index('TG').resample(rule)['Giá trị'].mean().dropna().reset_index()
                            else:
                                plot_data = sub_df.groupby('TG')['Giá trị'].mean().reset_index()
                                
                            plot_data = plot_data.sort_values(by='TG')
                            fig, pts = generate_chart(plot_data, f"Chỉ số: {ten_chi_so}", is_multi=False)

                            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
                            
                            with st.expander(f"Xem chi tiết {pts} điểm dữ liệu ĐÃ LỌC SẠCH"):
                                st.dataframe(plot_data, use_container_width=True)
                            st.write("---")
                    else:
                        st.info("Không có dữ liệu hợp lệ trong khoảng thời gian đã chọn.")

        # --- TAB 3: BIỂU ĐỒ ĐỐI CHIẾU ---
        with tab3:
            st.subheader("⚙️ Thiết lập biểu đồ đối chiếu lồng nhau")
            col1_m, col2_m = st.columns([1, 2])
            with col1_m:
                st.write("🎯 **1. Chọn các chỉ số:**")
                check_multi_ui = st.columns(3)
                selected_keys_3 = [k for i, k in enumerate(numeric_options) if check_multi_ui[i % 3].checkbox(k.upper(), key=f"c_multi_{k}")]

            with col2_m:
                st.write("✨ **2. Tùy chỉnh:**")
                sel_date_3 = st.date_input("Lọc theo ngày:", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="date_multi") if min_d else None
                start_d_3 = sel_date_3[0] if sel_date_3 else None
                end_d_3 = sel_date_3[1] if sel_date_3 and len(sel_date_3) == 2 else start_d_3
                
                res_choice_3 = st.selectbox("Làm mượt dữ liệu:", ["Nguyên bản", "Trung bình mỗi phút", "Trung bình mỗi 5 phút"], key="res_multi")

            if st.button("🚀 TẠO BIỂU ĐỒ ĐỐI CHIẾU", type="primary", key="btn_multi"):
                if len(selected_keys_3) < 2:
                    st.warning("Hãy chọn ít nhất 2 chỉ số để so sánh!")
                else:
                    mask = (df['_parsed_time'].dt.date >= start_d_3) & (df['_parsed_time'].dt.date <= end_d_3)
                    filtered_df = df[mask]
                    multi_chart_df = extract_sensor_data(filtered_df, selected_keys_3)
                    
                    if not multi_chart_df.empty:
                        # ========================================================
                        # LỌC DỮ LIỆU SẠCH CHO TỪNG CHỈ SỐ TRONG TAB 3
                        # ========================================================
                        clean_dfs = []
                        for col in selected_keys_3:
                            sub_df = multi_chart_df[multi_chart_df['Chỉ số'] == col.upper()]
                            ten_chi_so = col.upper()
                            
                            if ten_chi_so in KHOANG_TOI_UU:
                                min_val, max_val = KHOANG_TOI_UU[ten_chi_so]
                                sub_df = sub_df[(sub_df['Giá trị'] >= min_val) & (sub_df['Giá trị'] <= max_val)]
                            
                            if not sub_df.empty:
                                clean_dfs.append(sub_df)
                        
                        # Gộp lại sau khi đã lọc
                        multi_chart_df = pd.concat(clean_dfs) if clean_dfs else pd.DataFrame()
                        # ========================================================
                        
                        if not multi_chart_df.empty:
                            rule = r_dict[res_choice_3]
                            if start_d_3 and end_d_3 and (end_d_3 - start_d_3).days > 7 and not rule:
                                rule = "5min"
                                
                            if rule:
                                plot_data = multi_chart_df.set_index('TG').groupby('Chỉ số')['Giá trị'].resample(rule).mean().dropna().reset_index()
                            else:
                                plot_data = multi_chart_df.groupby(['TG', 'Chỉ số'])['Giá trị'].mean().reset_index()
                                
                            plot_data = plot_data.sort_values(by='TG')
                            fig, pts = generate_chart(plot_data, "Biểu đồ Đối chiếu Trực tiếp (Đã loại bỏ nhiễu)", is_multi=True)
                            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
                            
                            with st.expander(f"Xem bảng dữ liệu gộp SẠCH ({pts} điểm)"):
                                pivot_df = plot_data.pivot(index='TG', columns='Chỉ số', values='Giá trị').reset_index()
                                st.dataframe(pivot_df, use_container_width=True)
                        else:
                            st.warning("Toàn bộ dữ liệu của các chỉ số này đều nằm ngoài khoảng chuẩn hoặc bị lỗi.")
                    else:
                        st.info("Không có dữ liệu hợp lệ trong khoảng thời gian đã chọn.")

    except ValueError as ve:
        st.error(f"❌ {ve}")
    except Exception as e:
        st.error(f"Đã xảy ra lỗi: {e}")
