import streamlit as st           # Thư viện giao diện Web
import pandas as pd              # Thư viện xử lý dữ liệu
import numpy as np               # Thư viện tính toán
import json                      # Thư viện đọc JSON
import re                        # Thư viện xử lý chuỗi (Regex)
import plotly.express as px      # Thư viện vẽ biểu đồ

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==============================================================================
st.set_page_config(page_title="AgriData Pro v2.7", layout="wide", page_icon="🚜")
st.title("🚜 Hệ thống Phân tích & Cảnh báo Nông nghiệp Thông minh")

# Sidebar cấu hình ngưỡng linh hoạt
with st.sidebar:
    st.header("⚙️ Cấu hình Ngưỡng tối ưu")
    USER_LIMITS = {
        'PH': st.slider("Ngưỡng PH", 0.0, 14.0, (5.5, 7.5)),
        'NHIỆT ĐỘ': st.slider("Ngưỡng Nhiệt độ (°C)", -10, 60, (20, 35)),
        'EC': st.slider("Ngưỡng EC", 0, 5000, (500, 2500)),
        'ĐỘ ẨM': st.slider("Ngưỡng Độ ẩm (%)", 0, 100, (60, 90))
    }
    st.caption("Phiên bản v2.7 - Đã sửa lỗi AttributeError")

# ==============================================================================
# 2. HÀM XỬ LÝ DỮ LIỆU HIỆU SUẤT CAO
# ==============================================================================
@st.cache_data
def optimized_load_data(file_bytes):
    try:
        data = json.loads(file_bytes)
        # Sử dụng json_normalize để ép phẳng dữ liệu cực nhanh
        df = pd.json_normalize(data if isinstance(data, list) else [data])
        
        # Làm sạch tên cột: bỏ khoảng trắng, viết thường
        df.columns = [c.strip().lower().replace('.', '_') for c in df.columns]
        
        # Tìm cột thời gian
        t_col = next((c for c in df.columns if 'time' in c or 'thời gian' in c), None)
        if t_col:
            # Sửa lỗi Mixed Timezones bằng utc=True
            df['_ts'] = pd.to_datetime(df[t_col].astype(str), errors='coerce', utc=True)
            # Chuyển về giờ Việt Nam và xóa định dạng timezone để tránh lỗi so sánh
            df['_ts'] = df['_ts'].dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None)
            # Quan trọng: Xóa bỏ những dòng không có thời gian
            df = df.dropna(subset=['_ts'])
        return df, t_col
    except Exception as e:
        st.error(f"Lỗi nạp dữ liệu: {e}")
        return None, None

# ==============================================================================
# 3. TRÍCH XUẤT DỮ LIỆU CẢM BIẾN (FIX LỖI ATTRIBUTEERROR)
# ==============================================================================
def extract_sensor_data_v2(df, selected_cols):
    records = []
    high_freq_cols = set()
    
    # Bước 1: Chỉ lấy dòng có thời gian hợp lệ
    working_df = df.dropna(subset=['_ts']).copy()
    
    # Bước 2: Duyệt từng dòng một cách an toàn
    for row in working_df.itertuples(index=True):
        # Kiểm tra nếu _ts tồn tại trong row (itertuples đôi khi đổi tên cột nếu có ký tự lạ)
        # Chúng ta truy cập qua thuộc tính hoặc dùng chỉ số cột
        try:
            ts_val = getattr(row, '_ts')
            if pd.isna(ts_val): continue
            date_str = ts_val.strftime('%Y-%m-%d')
        except AttributeError:
            continue # Bỏ qua dòng nếu không tìm thấy thuộc tính _ts
            
        for col in selected_cols:
            val = str(getattr(row, col, '')).strip()
            if not val or val.lower() == 'nan': continue
            
            col_upper = col.upper()
            # Regex tìm dữ liệu dạng: 12-00-00/25.5
            matches = re.findall(r'(\d{2}-\d{2}-\d{2})/([-+]?\d*\.?\d+)', val)
            
            if matches:
                high_freq_cols.add(col_upper)
                for t_s, v_s in matches:
                    try:
                        full_t = f"{date_str} {t_s.replace('-', ':')}"
                        records.append({
                            'TG': pd.to_datetime(full_t),
                            'Giá trị': float(v_s),
                            'Chỉ số': col_upper
                        })
                    except: continue
            else:
                # Dữ liệu số đơn lẻ
                try:
                    num = re.search(r'[-+]?\d*\.?\d+', val)
                    if num:
                        records.append({'TG': ts_val, 'Giá trị': float(num.group()), 'Chỉ số': col_upper})
                except: continue
                
    return pd.DataFrame(records), high_freq_cols

# ==============================================================================
# 4. GIAO DIỆN CHÍNH
# ==============================================================================
uploaded_file = st.file_uploader("📥 Tải file JSON dữ liệu", type=['json'])

if uploaded_file:
    df_raw, time_key = optimized_load_data(uploaded_file.getvalue().decode("utf-8"))
    
    if df_raw is not None:
        # Lọc danh sách cột có thể vẽ biểu đồ
        exclude = [time_key, 'stt', 'tên khu', 'trạng thái', '_ts']
        numeric_options = [c for c in df_raw.columns if c not in exclude and 'id' not in c]
        
        tab1, tab2, tab3 = st.tabs(["📝 Bảng dữ liệu", "🤖 Cảnh báo thông minh", "📈 Biểu đồ"])

        with tab1:
            st.subheader("Bảng dữ liệu gốc")
            st.dataframe(df_raw.drop(columns=['_ts'], errors='ignore'))
            st.download_button("Tải CSV", df_raw.to_csv(index=False).encode('utf-8'), "data.csv")

        # Chọn cảm biến để phân tích
        targets = st.multiselect("Chọn chỉ số cảm biến:", [c.upper() for c in numeric_options])
        targets_raw = [c.lower() for c in targets]

        if targets:
            c_df, hf_list = extract_sensor_data_v2(df_raw, targets_raw)
            
            if not c_df.empty:
                with tab2:
                    st.subheader("Đánh giá từ hệ thống")
                    for s in targets:
                        sub = c_df[c_df['Chỉ số'] == s]
                        if sub.empty: continue
                        avg = sub['Giá trị'].mean()
                        low, high = USER_LIMITS.get(s, (0, 100))
                        
                        if avg < low: st.error(f"🔴 {s}: Trung bình {avg:.2f} (Thấp hơn ngưỡng {low})")
                        elif avg > high: st.error(f"🔴 {s}: Trung bình {avg:.2f} (Cao hơn ngưỡng {high})")
                        else: st.success(f"🟢 {s}: Trung bình {avg:.2f} (Ổn định)")

                with tab3:
                    # Gộp dữ liệu theo ngày nếu xem thời gian dài
                    days_range = (df_raw['_ts'].max() - df_raw['_ts'].min()).days
                    rule = "1D" if days_range > 3 else None
                    
                    for s in targets:
                        sub = c_df[c_df['Chỉ số'] == s]
                        if sub.empty: continue
                        
                        # Vẽ biểu đồ
                        plot_data = sub.set_index('TG').resample(rule)['Giá trị'].mean().reset_index() if rule else sub
                        fig = px.line(plot_data, x='TG', y='Giá trị', title=f"Xu hướng {s}")
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Không tìm thấy dữ liệu phù hợp để hiển thị biểu đồ.")
