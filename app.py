import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="JSON Data Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích JSON Nâng cao")
    
    if 'df' not in st.session_state:
        st.session_state.df = None

    with st.sidebar:
        st.header("Cấu hình")
        uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])
        if st.button("Reset / Xóa dữ liệu"):
            st.session_state.df = None
            st.rerun()

    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.session_state.df = pd.json_normalize(data)
        except Exception:
            pass 

    if st.session_state.df is not None:
        df = st.session_state.df
        
        st.subheader("🛠 Lựa chọn & Bộ lọc")
        
        # 1. Bộ lọc Thời gian (nếu có cột datetime)
        col_time = st.selectbox("Chọn cột thời gian (để lọc khoảng thời gian):", [None] + list(df.columns))
        if col_time:
            df[col_time] = pd.to_datetime(df[col_time], errors='coerce')
            # Lọc khoảng thời gian
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("Ngày bắt đầu", df[col_time].min())
            with col2:
                end = st.date_input("Ngày kết thúc", df[col_time].max())
            df = df[(df[col_time].dt.date >= start) & (df[col_time].dt.date <= end)]

        # 2. Chọn nhiều key để vẽ biểu đồ
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        selected_keys = st.multiselect("Tích chọn các cột giá trị muốn vẽ:", numeric_cols)
        
        # 3. Vẽ biểu đồ
        if selected_keys:
            x_axis = col_time if col_time else df.index
            fig = px.line(df, x=x_axis, y=selected_keys, title="Biểu đồ các cột đã chọn")
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

        # 4. Bảng dữ liệu
        st.subheader("📋 Bảng dữ liệu")
        st.data_editor(df, use_container_width=True, disabled=True)
    
    else:
        st.info("Hãy tải file JSON ở sidebar để bắt đầu.")

if __name__ == "__main__":
    main()
