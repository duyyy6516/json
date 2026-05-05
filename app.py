import streamlit as st
import pandas as pd
import plotly.express as px
import json

# Cấu hình trang giao diện rộng
st.set_page_config(page_title="JSON Data Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích File JSON thông minh")
    
    # Khởi tạo session_state để lưu trữ dữ liệu bền vững khi tương tác
    if 'df' not in st.session_state:
        st.session_state.df = None

    # --- SIDEBAR: Cấu hình ---
    with st.sidebar:
        st.header("Cấu hình")
        uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])
        
        # Nút Reset để xóa dữ liệu mà không cần tải lại trang (F5)
        if st.button("Reset / Xóa dữ liệu"):
            st.session_state.df = None
            st.rerun()

    # --- XỬ LÝ DỮ LIỆU ---
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            # Sử dụng pd.json_normalize để làm phẳng cấu trúc lồng nhau
            st.session_state.df = pd.json_normalize(data)
        except Exception as e:
            st.error(f"Lỗi đọc file JSON: {e}")
            return

    # --- HIỂN THỊ DỮ LIỆU & GIAO DIỆN CHÍNH ---
    if st.session_state.df is not None:
        df = st.session_state.df
        st.success("Dữ liệu đã được tải thành công!")
        
        # Hiển thị danh sách các cột (key) đã làm phẳng
        with st.expander("Xem danh sách tất cả các cột (Keys)"):
            st.write(df.columns.tolist())
        
        st.subheader("🛠 Cấu hình bộ lọc & Biểu đồ")
        
        # 1. Bộ lọc Thời gian
        col_time = st.selectbox("Chọn cột thời gian (để lọc):", [None] + list(df.columns))
        
        if col_time:
            try:
                # Chuyển đổi định dạng datetime
                df[col_time] = pd.to_datetime(df[col_time], errors='coerce')
                # Tạo thanh chọn khoảng thời gian
                start_date = st.date_input("Ngày bắt đầu", df[col_time].min())
                end_date = st.date_input("Ngày kết thúc", df[col_time].max())
                df = df[(df[col_time].dt.date >= start_date) & (df[col_time].dt.date <= end_date)]
            except Exception:
                st.warning("Không thể chuyển đổi cột này sang định dạng thời gian.")

        # 2. Trực quan hóa với Plotly
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if not numeric_cols:
            st.error("Dữ liệu không chứa cột số nào để vẽ biểu đồ.")
        else:
            val_col = st.selectbox("Chọn cột giá trị (số) để vẽ:", numeric_cols)
            x_col = col_time if col_time else df.index
            
            # Vẽ biểu đồ Line Chart tương tác
            fig = px.line(df, x=x_col, y=val_col, title=f"Biểu đồ {val_col} theo {x_col}")
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

        # 3. Bảng dữ liệu
        st.subheader("📋 Bảng dữ liệu đã làm phẳng")
        st.dataframe(df, use_container_width=True)
        
    else:
        st.info("Vui lòng tải file JSON ở menu bên trái để bắt đầu.")

if __name__ == "__main__":
    main()
