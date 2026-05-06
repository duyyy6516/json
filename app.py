import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="Universal JSON Analyzer", layout="wide")
st.title("🚀 Công cụ Phân tích Dữ liệu JSON Đa năng")

def load_and_flatten(file):
    try:
        data = json.load(file)
        # Sử dụng json_normalize để làm phẳng mọi cấu trúc JSON tự động
        df = pd.json_normalize(data)
        return df
    except Exception as e:
        st.error(f"Không thể đọc file: {e}")
        return None

uploaded_file = st.file_uploader("Tải lên file JSON bất kỳ", type=['json'])

if uploaded_file:
    df = load_and_flatten(uploaded_file)
    
    if df is not None:
        st.success("Đã tải dữ liệu thành công!")
        
        # Tự động nhận diện cột thời gian
        # Quét các cột có chứa từ khóa liên quan đến thời gian
        time_cols = [c for c in df.columns if any(x in c.lower() for x in ['time', 'date', 'thời gian', 'timestamp'])]
        
        # Tự động nhận diện cột số (để vẽ biểu đồ)
        numeric_cols = df.select_dtypes(include=['number', 'float', 'int']).columns.tolist()

        with st.sidebar:
            st.subheader("Cấu hình phân tích")
            selected_time = st.selectbox("Chọn cột thời gian:", [None] + time_cols)
            selected_metrics = st.multiselect("Chọn các chỉ số muốn vẽ:", numeric_cols)

        st.write("### Dữ liệu đã xử lý (Phẳng hóa):")
        st.dataframe(df.head(20))

        if selected_time and selected_metrics:
            # Chuyển cột thời gian sang định dạng chuẩn
            df[selected_time] = pd.to_datetime(df[selected_time], errors='coerce')
            df = df.sort_values(by=selected_time)

            for metric in selected_metrics:
                st.write(f"### Biểu đồ: {metric}")
                fig = px.line(df, x=selected_time, y=metric, markers=True)
                
                # Cấu hình giao diện sạch, zoom chuột và kéo thả
                fig.update_layout(
                    xaxis_title=selected_time,
                    yaxis_title=metric,
                    hovermode="x unified",
                    dragmode='pan',
                    xaxis=dict(rangeslider=dict(visible=False), type="date")
                )
                
                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
        else:
            st.info("👈 Hãy chọn cột Thời gian và chỉ số ở cột bên trái để bắt đầu vẽ biểu đồ.")
