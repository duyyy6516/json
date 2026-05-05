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
            
            # --- BƯỚC QUAN TRỌNG: ÉP KIỂU SỐ ---
            # Chuyển tất cả các cột sang dạng số, nếu không phải số thì để lại là object
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            
            st.write("### Tổng quan dữ liệu")
            st.write(f"Số hàng: {df.shape[0]}, Số cột: {df.shape[1]}")
            
            # Hiển thị bảng dữ liệu
            st.subheader("📋 Bảng dữ liệu")
            st.dataframe(df, use_container_width=True)

            # Vẽ biểu đồ
            # Chỉ lấy các cột thực sự là số
            numeric_df = df.select_dtypes(include=['number'])
            
            if not numeric_df.empty:
                st.subheader("📈 Biểu đồ dữ liệu")
                # Vẽ tất cả các cột số lên biểu đồ
                fig = px.line(df, y=numeric_df.columns)
                fig.update_traces(mode='lines+markers')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Không tìm thấy cột nào là số (Number). Hãy kiểm tra lại file JSON của bạn.")
                st.write("Dữ liệu hiện tại của bạn đang là dạng:", df.dtypes.to_dict())

        except Exception as e:
            st.error(f"Lỗi khi xử lý file: {e}")
    else:
        st.info("Vui lòng tải file JSON lên.")

if __name__ == "__main__":
    main()
