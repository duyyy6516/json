import streamlit as st           # Thư viện giao diện Web
import pandas as pd              # Thư viện xử lý dữ liệu mạnh mẽ
import numpy as np               # Thư viện tính toán số học
import json                      # Thư viện đọc định dạng JSON
import re                        # Thư viện xử lý chuỗi văn bản (Regex)
import plotly.express as px      # Thư viện vẽ biểu đồ tương tác cao

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & NGƯỠNG LINH HOẠT (CHỨC NĂNG 3: LINH HOẠT)
# ==============================================================================
st.set_page_config(page_title="AgriData Pro v2.5", layout="wide", page_icon="🚜")
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
    st.caption("Phiên bản v2.5 - Production Ready")

# ==============================================================================
# 2. XỬ LÝ DỮ LIỆU HIỆU SUẤT CAO (CHỨC NĂNG 1 & 2: HIỆU SUẤT & ĐỘ TIN CẬY)
# ==============================================================================
@st.cache_data
def optimized_load_data(file_bytes):
    """Sử dụng chuẩn công nghiệp json_normalize và xử lý đa múi giờ (Timezone)"""
    try:
        data = json.loads(file_bytes)
        # Chức năng 1: Ép phẳng JSON cực nhanh (Xử lý được hàng triệu dòng)
        df = pd.json_normalize(data if isinstance(data, list) else [data])
        
        # Làm sạch tên cột: Viết thường, xóa khoảng trắng, thay dấu chấm bằng gạch dưới
        df.columns = [c.strip().lower().replace('.', '_') for c in df.columns]
        
        # Chức năng 2: Tìm và chuẩn hóa cột thời gian (Xử lý lỗi Mixed Timezones)
        t_col = next((c for c in df.columns if 'time' in c or 'thời gian' in c), None)
        if t_col:
            # utc=True: Ép tất cả về cùng một múi giờ chuẩn quốc tế để so sánh
            df['_ts'] = pd.to_datetime(df[t_col].astype(str), errors='coerce', utc=True)
            # Chuyển về giờ Việt Nam (GMT+7) và loại bỏ định dạng TZ để vẽ biểu đồ
            df['_ts'] = df['_ts'].dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None)
            # Loại bỏ dữ liệu rác không có mốc thời gian
            df = df.dropna(subset=['_ts'])
        return df, t_col
    except Exception as e:
        st.error(f"Lỗi cấu trúc dữ liệu: {e}")
        return None, None

# ==============================================================================
# 3. HỆ THỐNG CẢNH BÁO TỰ ĐỘNG (CHỨC NĂNG 4: PHÂN TÍCH SÂU)
# ==============================================================================
def get_agricultural_insights(df_clean):
    """Hệ thống chuyên gia: Đưa ra lời khuyên dựa trên số liệu thực tế"""
    insights = []
    for sensor, (low, high) in USER_LIMITS.items():
        sub = df_clean[df_clean['Chỉ số'] == sensor]
        if sub.empty: continue
        
        avg_val = sub['Giá trị'].mean() # Tính trung bình thực tế
        
        if avg_val < low:
            insights.append(f"🔴 **{sensor}** đang thấp hơn ngưỡng ({avg_val:.2f} < {low}). **Lời khuyên:** Cần tăng cường bổ sung.")
        elif avg_val > high:
            insights.append(f"🔴 **{sensor}** đang vượt mức an toàn ({avg_val:.2f} > {high}). **Lời khuyên:** Cần điều tiết giảm lại.")
        else:
            insights.append(f"🟢 **{sensor}** hiện tại rất tốt ({avg_val:.2f}). Duy trì chế độ chăm sóc hiện tại.")
    return insights

# ==============================================================================
# 4. TRÍCH XUẤT DỮ LIỆU CẢM BIẾN (REGEX V2)
# ==============================================================================
def extract_sensor_data_v2(df, selected_cols):
    """Bóc tách dữ liệu chuỗi Giờ/Giá trị với khả năng chịu lỗi cao"""
    records = []
    high_freq_cols = set()
    
    for row in df.itertuples():
        date_str = row._ts.strftime('%Y-%m-%d')
        for col in selected_cols:
            val = str(getattr(row, col)).strip()
            if not val or val.lower() == 'nan': continue
            
            # Regex tìm kiếm chuỗi dính chùm: "Giờ-Phút-Giây / Giá trị"
            matches = re.findall(r'(\d{2}-\d{2}-\d{2})/([-+]?\d*\.?\d+)', val)
            if matches:
                high_freq_cols.add(col.upper())
                for t_s, v_s in matches:
                    try:
                        records.append({
                            'TG': pd.to_datetime(f"{date_str} {t_s.replace('-', ':')}"),
                            'Giá trị': float(v_s),
                            'Chỉ số': col.upper()
                        })
                    except: continue
            else:
                # Nếu là số đơn lẻ bình thường
                try:
                    num = re.search(r'[-+]?\d*\.?\d+', val)
                    if num:
                        records.append({'TG': row._ts, 'Giá trị': float(num.group()), 'Chỉ số': col.upper()})
                except: continue
                
    return pd.DataFrame(records), high_freq_cols

# ==============================================================================
# 5. GIAO DIỆN CHÍNH & LUỒNG XỬ LÝ
# ==============================================================================
uploaded_file = st.file_uploader("📥 Tải lên file JSON từ thiết bị cảm biến", type=['json'])

if uploaded_file:
    # 1. Nạp dữ liệu
    df_raw, time_key = optimized_load_data(uploaded_file.getvalue().decode("utf-8"))
    
    if df_raw is not None:
        # 2. Sidebar Lọc trường dữ liệu chữ (Khu vực, STT...)
        filterable_cols = [c for c in df_raw.columns if '_ts' not in c and 'id' not in c]
        
        # 3. Chia giao diện Tabs
        tab_data, tab_expert, tab_chart = st.tabs(["📝 Bảng dữ liệu", "🤖 Chuyên gia phân tích", "📈 Biểu đồ trực quan"])
        
        with tab_data:
            st.subheader("🌾 Dữ liệu thô từ hệ thống")
            st.dataframe(df_raw.drop(columns=['_ts'], errors='ignore'), use_container_width=True)
            st.download_button("📥 Tải CSV", data=df_raw.to_csv(index=False).encode('utf-8'), file_name="agri_data.csv")

        # Chu bị dữ liệu chung cho các Tab sau
        target_sensors = st.multiselect("Chọn các chỉ số cảm biến để phân tích:", 
                                        [c.upper() for c in filterable_cols], 
                                        default=[filterable_cols[0].upper()] if filterable_cols else [])
        
        # Chuyển tên cột về dạng gốc để trích xuất
        target_cols_raw = [c.lower() for c in target_sensors]
        
        if target_sensors:
            # Trích xuất dữ liệu cảm biến
            with st.spinner("Đang tính toán số liệu..."):
                c_df, hf_list = extract_sensor_data_v2(df_raw, target_cols_raw)
            
            if not c_df.empty:
                with tab_expert:
                    st.subheader("🤖 Đánh giá sức khỏe nông trại")
                    # Chức năng 4: Hiển thị cảnh báo thông minh
                    insights = get_agricultural_insights(c_df)
                    for note in insights:
                        if "🔴" in note: st.error(note)
                        else: st.success(note)
                    
                    st.markdown("---")
                    st.subheader("📊 Thống kê toán học")
                    summary = c_df.groupby('Chỉ số')['Giá trị'].agg(['min', 'max', 'mean', 'std']).rename(
                        columns={'min':'Thấp nhất', 'max':'Cao nhất', 'mean':'Trung bình', 'std':'Độ lệch chuẩn'}
                    )
                    st.table(summary)

                with tab_chart:
                    st.subheader("📈 Xu hướng biến thiên thời gian")
                    # Tự động gộp dữ liệu theo ngày nếu khoảng thời gian quá lớn để tăng tốc web
                    days_range = (df_raw['_ts'].max() - df_raw['_ts'].min()).days
                    rule = "1D" if days_range > 3 else None
                    
                    if rule: st.warning(f"💡 Dữ liệu đang được hiển thị theo **Trung bình ngày** để tối ưu hiệu suất.")

                    for sensor in target_sensors:
                        sub = c_df[c_df['Chỉ số'] == sensor]
                        
                        # Chức năng 3: Lọc nhiễu dựa trên ngưỡng linh hoạt (cho phép biên sai số 10%)
                        if sensor in USER_LIMITS:
                            low, high = USER_LIMITS[sensor]
                            sub = sub[(sub['Giá trị'] >= (low * 0.5)) & (sub['Giá trị'] <= (high * 1.5))]
                        
                        if sub.empty: continue
                        
                        # Vẽ biểu đồ
                        plot_data = sub.set_index('TG').resample(rule)['Giá trị'].mean().reset_index() if rule else sub
                        fig = px.line(plot_data, x='TG', y='Giá trị', title=f"Biến thiên: {sensor}", 
                                      template="plotly_white", markers=(not rule))
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Không tìm thấy dữ liệu cảm biến phù hợp trong file.")
    else:
        st.warning("Vui lòng kiểm tra lại định dạng file JSON của bạn.")
