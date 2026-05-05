import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="JSON Data Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích dữ liệu JSON")
    
    uploaded_file = st.file_uploader("Tải file JSON", type=['json'])
    
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            df = pd.json_normalize(data)
            
            # --- KIỂM TRA DỮ LIỆU ---
            st.write("### Tổng quan dữ liệu")
            st.write(f"Số hàng: {df.shape[0]}, Số cột: {df.shape[1]}")
            
            # Tự động ép kiểu số (quan trọng)
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            
            # Hiển thị bảng dữ liệu (để bạn xem cột nào là số)
            st.subheader("📋 Bảng dữ liệu thô")
            st.dataframe(df)

            # Vẽ biểu đồ nếu tìm thấy cột số
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                st.subheader("📈 Biểu đồ dữ liệu")
                fig = px.line(df, y=numeric_cols)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Không tìm thấy cột nào có dạng số (Number) để vẽ biểu đồ.")
                st.write("Kiểm tra lại xem các số trong file của bạn có bị để trong dấu ngoặc kép ' ' không?")

        except Exception as e:
            st.error(f"Lỗi khi xử lý file: {e}")
    else:
        st.info("Vui lòng tải file JSON lên.")

if __name__ == "__main__":
    main()
