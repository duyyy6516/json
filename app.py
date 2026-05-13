import streamlit as st           # Thư viện giao diện Web
import pandas as pd              # Thư viện xử lý dữ liệu mạnh mẽ
import numpy as np               # Thư viện tính toán số học
import json                      # Thư viện đọc định dạng JSON
import re                        # Thư viện xử lý chuỗi văn bản (Regex)
import plotly.express as px      # Thư viện vẽ biểu đồ tương tác cao

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & NGƯỠNG LINH HOẠT (CHỨC NĂNG: LINH HOẠT)
# ==============================================================================
st.set_page_config(page_title="AgriData Pro v2.6", layout="wide", page_icon="🚜")
st.title("🚜 Hệ thống Phân tích & Cảnh báo Nông nghiệp Thông minh")

# Thanh Sidebar cho phép người dùng tùy chỉnh ngưỡng theo từng loại cây trồng
with st.sidebar:
    st.header("⚙️ Cấu hình Ngưỡng tối ưu")
    st.info("Hệ thống sẽ dựa vào đây để đưa ra cảnh báo và lọc dữ liệu lỗi.")
    
    # Tạo từ điển ngưỡng động (User có thể kéo thanh trượt để thay đổi)
    USER_LIMITS = {
        'PH': st.slider("Ngưỡng PH (Lý tưởng)", 0.0, 14.0, (5.5, 7.5), help="Độ PH tối ưu cho cây"),
        'NHIỆT ĐỘ': st.slider("Ngưỡng Nhiệt độ (°C)", -10, 60, (20, 35)),
        'EC': st.slider("Ngưỡng EC (Dinh dưỡng)", 0, 5000, (500, 2500)),
        'ĐỘ ẨM': st.slider("Ngưỡng Độ ẩm (%)", 0, 100, (60, 90))
    }
    st.markdown("---")
    st.caption("Phiên bản v2.6 - Fixed AttributeError")

# ==============================================================================
# 2. XỬ LÝ DỮ LIỆU HIỆU SUẤT CAO (CHỨC NĂNG: HIỆU SUẤT & ĐỘ TIN CẬY)
# ==============================================================================
@st.cache_data
def optimized_load_data(file_bytes):
    """Sử dụng chuẩn công nghiệp json_normalize và xử lý đa múi giờ (Timezone)"""
    try:
        data = json.loads(file_bytes)
        # Ép phẳng JSON cực nhanh (Xử lý được hàng triệu dòng)
        df = pd.json_normalize(data if isinstance(data, list) else [data])
        
        # Làm sạch tên cột: Viết thường, xóa khoảng trắng, thay dấu chấm bằng gạch dưới
        df.columns = [c.strip().lower().replace('.', '_') for c in df.columns]
        
        # Tìm và chuẩn hóa cột thời gian (Xử lý lỗi Mixed Timezones)
        t_col = next((c for c in df.columns if 'time' in c or 'thời gian' in c), None)
        if t_col:
            # utc=True: Ép tất cả về cùng một múi giờ chuẩn quốc tế để tránh lỗi Mixed Timezones
            df['_ts'] = pd.to_datetime(df[t_col].astype(str), errors='coerce', utc=True)
            # Chuyển về giờ Việt Nam (GMT+7) và loại bỏ định dạng TZ để vẽ biểu đồ
            df['_ts'] = df['_ts'].dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None)
            # QUAN TRỌNG: Loại bỏ dữ liệu rác không có mốc thời gian để tránh lỗi xử lý sau này
            df = df.dropna(subset=['_ts'])
        return df, t_col
    except Exception as e:
        st.error(f"Lỗi cấu trúc dữ liệu: {e}")
        return None, None

# ==============================================================================
# 3. HỆ THỐNG CẢNH BÁO TỰ ĐỘNG (CHỨC NĂNG: PHÂN TÍCH SÂU)
# ==============================================================================
def get_agricultural_insights(df_clean):
    """Hệ thống chuyên gia: Đưa ra lời khuyên dựa trên số liệu thực tế"""
    insights = []
    for sensor, (low, high) in USER_LIMITS.items():
        sub = df_clean[df_clean['Chỉ số'] == sensor]
        if sub.empty: continue
        
        avg_val = sub['Giá trị'].mean() # Tính trung bình thực tế
        
        if avg_val < low:
            insights.append(f"🔴 **{sensor}** thấp ({avg_val:.2f} < {low}). Cần tăng cường bổ sung.")
        elif avg_val > high:
            insights.append(f"🔴 **{sensor}** cao ({avg_val:.2f} > {high}). Cần điều tiết giảm lại.")
        else:
            insights.append(f"🟢 **{sensor}** lý tưởng ({avg_val:.2f}). Duy trì chế độ hiện tại.")
    return insights

# ==============================================================================
# 4. TRÍCH XUẤT DỮ LIỆU CẢM BIẾN (GIA CỐ AN TOÀN - FIXED ATTRIBUTEERROR)
# ==============================================================================
def extract_sensor_data_v2(df, selected_cols):
    """Bóc tách dữ liệu với cơ chế kiểm tra lỗi NaT/NaN nghiêm ngặt"""
    records = []
    high_freq_cols = set()
    
    # Bước 1: Chỉ xử lý những dòng có thời gian hợp lệ
    working_df = df.dropna(subset=['_ts']).copy()
    
    # Bước 2: Duyệt từng dòng (sử dụng itertuples với tên thuộc tính an toàn)
    for row in working_df.itertuples(index=False):
        # Kiểm tra an toàn: Nếu cột _ts bị lỗi do quá trình xử lý trước đó
        if pd.isna(row._ts):
            continue
            
        try:
            # Lấy chuỗi Ngày (Y-m-d) từ cột _ts
            date_str = row._ts.strftime('%Y-%m-%d')
        except:
            continue # Bỏ qua nếu dòng này không định dạng được ngày tháng
            
        for col in selected_cols:
            # Lấy giá trị của cột cảm biến (dùng getattr để tránh lỗi nếu tên cột lạ)
            val = str(getattr(row, col, '')).strip()
            if not val or val.lower() == 'nan': 
                continue
            
            col_upper = col.upper()
            
            # Kiểm tra Regex cho dữ liệu High-Frequency (Giờ-Phút-Giây/Giá trị)
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
                # Nếu là dữ liệu số đơn lẻ
                try:
                    num = re.search(r'[-+]?\d*\.?\d+', val)
                    if num:
                        records.append({
                            'TG': row._ts, 
                            'Giá trị': float(num.group()), 
                            'Chỉ số': col_upper
                        })
                except: continue
                
    return pd.DataFrame(records), high_freq_cols

# ==============================================================================
# 5. GIAO DIỆN CHÍNH & LUỒNG XỬ LÝ
# ==============================================================================
uploaded_file = st.file_uploader("📥 Tải lên file JSON dữ liệu nông nghiệp", type=['json'])

if uploaded_file:
    # Nạp dữ liệu
    df_raw, time_key = optimized_load_data(uploaded_file.getvalue().decode("utf-8"))
    
    if df_raw is not None:
        # Tìm các cột có thể phân tích (loại trừ các cột metadata)
        exclude_list = [time_key, 'stt', 'tên khu', 'trạng thái', '_ts']
        filterable_cols = [c for c in df_raw.columns if c not in exclude_list and 'id' not in c]
        
        # Tạo Tabs giao diện
        tab_data, tab_expert, tab_chart = st.tabs(["📝 Bảng dữ liệu", "🤖 Hệ thống chuyên gia", "📈 Biểu đồ xu hướng"])
        
        with tab_data:
            st.subheader("🌾 Dữ liệu gốc đã chuẩn hóa")
            # Hiển thị bảng và nút tải file
            st.dataframe(df_raw.drop(columns=['_ts'], errors='ignore'), use_container_width=True)
            st.download_button("📥 Tải CSV", data=df_raw.to_csv(index=False).encode('utf-8'), file_name="agri_data.csv")

        # Widget chọn cảm biến dùng chung cho các Tab
        target_sensors = st.multiselect("Chọn cảm biến muốn phân tích:", 
                                        [c.upper() for c in filterable_cols], 
                                        default=[filterable_cols[0].upper()] if filterable_cols else [])
        
        if target_sensors:
            # Thực hiện bóc tách dữ liệu
            target_cols_raw = [c.lower() for c in target_sensors]
            with st.spinner("Đang trích xuất số liệu..."):
                c_df, hf_list = extract_sensor_data_v2(df_raw, target_cols_raw)
            
            if not c_df.empty:
                # TAB CHUYÊN GIA (Insights & Statistics)
                with tab_expert:
                    st.subheader("🤖 Phân tích tình trạng sức khỏe")
                    insights = get_agricultural_insights(c_df)
                    for note in insights:
                        if "🔴" in note: st.error(note)
                        else: st.success(note)
                    
                    st.markdown("---")
                    st.subheader("📊 Bảng kê số liệu")
                    summary = c_df.groupby('Chỉ số')['Giá trị'].agg(['min', 'max', 'mean']).rename(
                        columns={'min':'Thấp nhất', 'max':'Cao nhất', 'mean':'Trung bình'}
                    )
                    st.table(summary)

                # TAB BIỂU ĐỒ (Visualizations)
                with tab_chart:
                    st.subheader("📈 Đồ thị biến thiên")
                    
                    # Tự động gộp dữ liệu theo ngày nếu dữ liệu quá dài (> 3 ngày)
                    days_range = (df_raw['_ts'].max() - df_raw['_ts'].min()).days
                    rule = "1D" if days_range > 3 else None
                    if rule: st.warning("💡 Hệ thống đang hiển thị trung bình theo ngày để tối ưu đồ thị.")

                    for sensor in target_sensors:
                        sub = c_df[c_df['Chỉ số'] == sensor]
                        
                        # Lọc nhiễu cảm biến dựa trên ngưỡng linh hoạt (cho phép sai số 50%)
                        if sensor in USER_LIMITS:
                            low, high = USER_LIMITS[sensor]
                            sub = sub[(sub['Giá trị'] >= (low * 0.5)) & (sub['Giá trị'] <= (high * 1.5))]
                        
                        if sub.empty: continue
                        
                        # Vẽ đồ thị line chart
                        plot_data = sub.set_index('TG').resample(rule)['Giá trị'].mean().reset_index() if rule else sub
                        fig = px.line(plot_data, x='TG', y='Giá trị', title=f"Chỉ số: {sensor}", 
                                      template="plotly_white", markers=(not rule))
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Không tìm thấy số liệu cảm biến trong file JSON này.")
    else:
        st.warning("Không thể xử lý file. Vui lòng kiểm tra lại định dạng JSON.")
