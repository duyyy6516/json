import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 1. Cấu hình trang
st.set_page_config(page_title="JSON Data Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích File JSON")
    
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
            pass 

    # 3. Phần thân: Hiển thị và Phân tích
    if st.session_state.df is not None:
        df = st.session_state.df
        
        # Hiển thị cột
        with st.expander("Xem danh sách tất cả các cột (Keys)"):
            st.write(df.columns.tolist())
        
        st.subheader("📈 Trực quan hóa dữ liệu")
        
        # Chỉ vẽ biểu đồ nếu có cột số
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            val_col = st.selectbox("Chọn cột giá trị (số) để vẽ:", numeric_cols)
            
            # Vẽ Plotly
            fig = px.line(df, y=val_col, title=f"Biểu đồ giá trị: {val_col}")
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

        # Bảng dữ liệu hiển thị đầy đủ
        st.subheader("📋 Bảng dữ liệu (Click vào ô để xem nội dung đầy đủ)")
        
        # Dùng data_editor để xử lý hiển thị văn bản dài
        st.data_editor(
            df, 
            use_container_width=True,
            column_config={
                col: st.column_config.TextColumn(col, width="medium") for col in df.columns
            },
            disabled=True # Chỉ hiển thị, không cho sửa
        )
    
    else:
        st.info("Hãy tải file JSON ở sidebar để bắt đầu.")

if __name__ == "__main__":
    main()
