import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="JSON Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích JSON (Chế độ quét toàn bộ)")
    
    with st.sidebar:
        uploaded_file = st.file_uploader("Tải file JSON", type=['json'])
        if st.button("Reset"):
            st.session_state.df = None
            st.rerun()

    if uploaded_file is not None:
        try:
            # 1. Đọc dữ liệu
            data = json.load(uploaded_file)
            
            # 2. Xử lý dữ liệu: Quét toàn bộ key từ mọi dòng
            # Dùng cách này để đảm bảo dù dòng đầu thiếu key, vẫn tìm thấy ở dòng sau
            df = pd.DataFrame(data)
            
            # Nếu vẫn thiếu cột, ta thử dùng json_normalize lại một lần nữa với dict lồng
            if df.empty:
                df = pd.json_normalize(data)
            
            # 3. Ép kiểu dữ liệu (tự động chuyển "2.53" -> 2.53)
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            
            st.session_state.df = df
            st.success(f"Đã tải thành công {len(df)} dòng dữ liệu.")
            
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")

    if 'df' in st.session_state and st.session_state.df is not None:
        df = st.session_state.df
        
        # Hiển thị bảng dữ liệu
        st.subheader("📋 Dữ liệu thô")
        st.data_editor(df, use_container_width=True, disabled=True)
        
        # Vẽ biểu đồ
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            selected_keys = st.multiselect("Chọn chỉ số để vẽ:", numeric_cols)
            for key in selected_keys:
                st.line_chart(df[key])
    else:
        st.info("Hãy tải file JSON để bắt đầu.")

if __name__ == "__main__":
    main()
