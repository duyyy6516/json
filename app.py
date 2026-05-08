import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px
import io

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="JSON Data Pro", layout="wide", page_icon="📊")
st.title("📊 Công cụ Phân tích Dữ liệu Pro")

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
    
    # Tìm cột thời gian
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
    """Trích xuất dữ liệu kèm theo STT để hiển thị khi hover"""
    records = []
    # Kiểm tra xem có cột stt không
    stt_col = next((c for c in df.columns if c.lower() == 'stt'), None)
    
    cols_to_extract = (([stt_col] if stt_col else []) + ['_parsed_time'] + selected_cols)
    working_df = df[cols_to_extract].dropna(subset=['_parsed_time'])
    
    # Biên dịch regex để tăng tốc
    pattern = re.compile(r'(\d{2}-\d{2}-\d{2})/([-+]?\d*\.?\d+)')
    num_pattern = re.compile(r'[-+]?\d*\.?\d+')

    for row in working_df.itertuples(index=False):
        idx_offset = 1 if stt_col else 0
        current_stt = row[0] if stt_col else "N/A"
        main_time = row[idx_offset]
        
        for i, col_name in enumerate(selected_cols, start=idx_offset + 1):
            val = str(row[i]).strip()
            if not val or val.lower() == 'nan':
                continue
                
            matches = pattern.findall(val)
            if matches:
                for t_str, v_str in matches:
                    try:
                        full_t_str = f"{main_time.strftime('%Y-%m-%d')} {t_str.replace('-', ':')}"
                        records.append({
                            'TG': pd.to_datetime(full_t_str), 
                            'Giá trị': float(v_str), 
                            'Chỉ số': col_name.upper(),
                            'STT': current_stt
                        })
                    except: pass
            else:
                num_match = num_pattern.search(val)
                if num_match:
                    records.append({
                        'TG': main_time, 
                        'Giá trị': float(num_match.group()), 
                        'Chỉ số': col_name.upper(),
                        'STT': current_stt
                    })
    return pd.DataFrame(records)

def generate_chart(df, title, is_multi=False):
    """Hàm vẽ biểu đồ với cấu hình hiển thị STT khi hover"""
    num_points = len(df)
    use_webgl = 'webgl' if num_points > 1000 else 'svg'
    show_markers = num_points <= 1000 
    
    fig = px.line(
        df, x='TG', y='Giá trị', 
        color='Chỉ số' if is_multi else None, 
        markers=show_markers, 
        render_mode=use_webgl,
        custom_data=['STT'] if 'STT' in df.columns else None
    )
        
    # Cấu hình Hover Template: Hiện STT lên đầu, định dạng lại thời gian
    hovertemplate = (
        "<b>STT: %{customdata[0]}</b><br>" +
        "Thời gian: %{x|%d/%m/%Y %H:%M:%S}<br>" +
        "Giá trị: <b>%{y}</b>" +
        "<extra></extra>"
    )
    
    fig.update_traces(hovertemplate=hovertemplate)
    
    fig.update_layout(
        title=f"<b>{title}</b>",
        xaxis_title="Trục thời gian",
        yaxis_title="Giá trị cảm biến",
        hovermode="x", # Đổi thành 'x' để tập trung vào điểm dữ liệu theo STT
        dragmode='pan',
        template="plotly_white",
        xaxis=dict(showspikes=True, spikecolor="gray", spikemode="across")
    )
    
    return fig, num_points

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    return output.getvalue()

# ==============================================================================
# 3. GIAO DIỆN CHÍNH
# ==============================================================================
uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])

if uploaded_file is not None:
    try:
        with st.spinner("Đang phân tích cấu trúc JSON..."):
            file_bytes = uploaded_file.getvalue().decode("utf-8")
            df, time_col = load_and_process_data(file_bytes)
            display_df = df.drop(columns=['_parsed_time'], errors='ignore').fillna("")

        # Lấy dải ngày
        min_d, max_d = None, None
        if '_parsed_time' in df.columns:
            valid_ts = df['_parsed_time'].dropna()
            if not valid_ts.empty:
                min_d, max_d = valid_ts.min().date(), valid_ts.max().date()

        # Lọc các cột số
        exclude = [time_col, 'stt', 'tên khu', 'trạng thái', 'phương thức hoạt động', 'người điều khiển', '_parsed_time']
        numeric_options = [c for c in df.columns if c not in exclude and '_id' not in c]

        tab1, tab2, tab3 = st.tabs(["🗂️ Bảng dữ liệu", "📈 Biểu đồ Đơn", "📊 So sánh Đối chiếu"])

        with tab1:
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.subheader(f"Dữ liệu gốc: {len(df)} dòng")
            
            csv = display_df.to_csv(index=False).encode('utf-8')
            c2.download_button("📥 Tải CSV", csv, "data.csv", "text/csv", use_container_width=True)
            
            xlsx = to_excel(display_df)
            c3.download_button("📥 Tải Excel", xlsx, "data.xlsx", use_container_width=True)
            
            st.dataframe(display_df, use_container_width=True)

        # HÀM DÙNG CHUNG CHO TAB 2 & 3
        r_dict = {"Nguyên bản": None, "Trung bình 1 phút": "1min", "Trung bình 5 phút": "5min"}

        with tab2:
            st.subheader("Thiết lập biểu đồ đơn")
            col_a, col_b = st.columns([1, 2])
            with col_a:
                sel_date_2 = st.date_input("Chọn ngày:", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="d2")
                res_2 = st.selectbox("Làm mượt:", list(r_dict.keys()), key="r2")
            with col_b:
                selected_keys_2 = [k for i, k in enumerate(numeric_options) if st.checkbox(k.upper(), key=f"t2_{k}")]

            if st.button("🚀 XUẤT BIỂU ĐỒ ĐƠN", type="primary"):
                if not selected_keys_2:
                    st.warning("Vui lòng chọn chỉ số.")
                else:
                    start, end = (sel_date_2[0], sel_date_2[1]) if len(sel_date_2)==2 else (sel_date_2[0], sel_date_2[0])
                    mask = (df['_parsed_time'].dt.date >= start) & (df['_parsed_time'].dt.date <= end)
                    chart_df = extract_sensor_data(df[mask], selected_keys_2)
                    
                    if not chart_df.empty:
                        rule = r_dict[res_2]
                        for col in selected_keys_2:
                            sub = chart_df[chart_df['Chỉ số'] == col.upper()]
                            if rule:
                                # Khi resample, lấy STT đầu tiên trong khoảng thời gian đó
                                plot_data = sub.set_index('TG').resample(rule).agg({'Giá trị': 'mean', 'STT': 'first'}).dropna().reset_index()
                            else:
                                plot_data = sub.sort_values('TG')
                            
                            fig, _ = generate_chart(plot_data, f"Chỉ số: {col.upper()}", False)
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("Không có dữ liệu trong khoảng này.")

        with tab3:
            st.subheader("Biểu đồ đối chiếu (Nhiều chỉ số)")
            col_m1, col_m2 = st.columns([1, 2])
            with col_m1:
                selected_keys_3 = [k for i, k in enumerate(numeric_options) if st.checkbox(k.upper(), key=f"t3_{k}")]
            with col_m2:
                sel_date_3 = st.date_input("Chọn ngày:", value=(min_d, max_d), key="d3")
                res_3 = st.selectbox("Làm mượt:", list(r_dict.keys()), key="r3")

            if st.button("🚀 XUẤT BIỂU ĐỒ ĐỐI CHIẾU", type="primary"):
                if len(selected_keys_3) < 2:
                    st.warning("Chọn ít nhất 2 chỉ số để so sánh.")
                else:
                    start, end = (sel_date_3[0], sel_date_3[1]) if len(sel_date_3)==2 else (sel_date_3[0], sel_date_3[0])
                    mask = (df['_parsed_time'].dt.date >= start) & (df['_parsed_time'].dt.date <= end)
                    multi_df = extract_sensor_data(df[mask], selected_keys_3)
                    
                    if not multi_df.empty:
                        rule = r_dict[res_3]
                        if rule:
                            plot_data = multi_df.set_index('TG').groupby('Chỉ số').resample(rule).agg({'Giá trị': 'mean', 'STT': 'first'}).dropna().reset_index()
                        else:
                            plot_data = multi_df.sort_values('TG')
                        
                        fig, _ = generate_chart(plot_data, "So sánh các chỉ số cảm biến", True)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("Không có dữ liệu.")

    except Exception as e:
        st.error(f"Lỗi: {e}")
