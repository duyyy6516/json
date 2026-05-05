import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 1. Cấu hình trang
st.set_page_config(page_title="JSON Data Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích File JSON thông minh")
    
    # Khởi tạo lưu trữ dữ liệu
    if 'df' not in st.session_state:
        st.session_state.df = None

    # 2. Sidebar: Tải file
    with st.sidebar:
        st.header("Cấu hình")
        uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])
        
        # Nút Reset
        if st.button("Reset / Xóa dữ liệu"):
            st.session_state.df = None
            st.rerun()

    # Xử lý file JSON
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.session_state.df = pd.json_normalize(data)
        except Exception:
            pass # Bỏ qua thông báo lỗi để giao diện sạch

    # 3. Phần thân: Hiển thị và Phân tích
    if st.session_state.df is not None:
        df = st.session_state.df
        
        # Hiển thị cột
        with st.expander("Xem danh sách tất cả các cột (Keys)"):
            st.write(df.columns.tolist())
        
        st.subheader("🛠 Cấu hình bộ lọc & Biểu đồ")
        
        # Lọc Thời gian
        col_time = st.selectbox("Chọn cột thời gian (để lọc):", [None] + list(df.columns))
        
        if col_time:
            # Chuyển đổi và xử lý lỗi ngầm
            df[col_time] = pd.to_datetime(df[col_time], errors='coerce')
            if not df[col_time].isna().all():
                start_date = st.date_input("Ngày bắt đầu", df[col_time].min())
                end_date = st.date_input("Ngày kết thúc", df[col_time].max())
                df = df[(df[col_time].dt.date >= start_date) & (df[col_time].dt.date <= end_date)]

        # Vẽ biểu đồ
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            val_col = st.selectbox("Chọn cột giá trị (số) để vẽ:", numeric_cols)
            x_col = col_time if col_time else df.index
            
            # Vẽ Plotly
            fig = px.line(df, x=x_col, y=val_col, title=f"Biểu đồ {val_col}")
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

        # Bảng dữ liệu
        st.subheader("📋 Bảng dữ liệu đã làm phẳng")
        st.dataframe(df, use_container_width=True)
    
    else:
        st.info("Hãy tải file JSON ở sidebar để bắt đầu.")

if __name__ == "__main__":
    main()
