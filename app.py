import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 1. Cấu hình trang
st.set_page_config(page_title="JSON Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích dữ liệu JSON")
    
    uploaded_file = st.file_uploader("Tải file JSON", type=['json'])
    
    if uploaded_file is not None:
        try:
            # Đọc dữ liệu
            data = json.load(uploaded_file)
            df = pd.json_normalize(data)
            
            # XỬ LÝ SỐ AN TOÀN
            # Dùng 'coerce' để biến các giá trị không phải số thành NaN
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            st.write(f"Số hàng: {df.shape[0]}, Số cột: {df.shape[1]}")
            
            # Bảng dữ liệu
            st.subheader("📋 Bảng dữ liệu")
            st.dataframe(df, use_container_width=True)

            # Vẽ biểu đồ
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            if numeric_cols:
                st.subheader("📈 Biểu đồ dữ liệu")
                fig = px.line(df, y=numeric_cols)
                fig.update_traces(mode='lines+markers')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Không tìm thấy cột nào là số.")

        except Exception as e:
            # Ghi log lỗi chi tiết để bạn dễ kiểm tra
            st.error(f"Lỗi khi xử lý file: {str(e)}")
            st.write("Vui lòng kiểm tra cấu trúc file JSON của bạn.")
    else:
        st.info("Vui lòng tải file JSON lên.")

if __name__ == "__main__":
    main()
