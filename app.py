import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="JSON Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích JSON Nâng cao")
    
    # 1. Sidebar tải file
    with st.sidebar:
        uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])
        if st.button("Reset / Xóa dữ liệu"):
            st.session_state.df = None
            st.rerun()

    # 2. Xử lý dữ liệu
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            df = pd.json_normalize(data)
            
            # Ép kiểu số an toàn
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            st.session_state.df = df
        except Exception as e:
            st.error(f"Lỗi: {e}")

    # 3. Giao diện chính
    if 'df' in st.session_state and st.session_state.df is not None:
        df = st.session_state.df
        
        st.subheader("🛠 Lựa chọn cột để vẽ")
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        # Chọn nhiều cột
        selected_keys = st.multiselect("Tích chọn các cột giá trị muốn vẽ:", numeric_cols)
        
        # --- VẼ BIỂU ĐỒ TỪNG KEY RIÊNG BIỆT ---
        if selected_keys:
            for key in selected_keys:
                st.write(f"### Biểu đồ: {key}")
                fig = px.line(df, y=key, title=f"Dữ liệu của {key}")
                fig.update_traces(mode='lines+markers', line_color='#636EFA')
                st.plotly_chart(fig, use_container_width=True)
        
        # 4. Bảng dữ liệu
        st.subheader("📋 Bảng dữ liệu")
        st.dataframe(df, use_container_width=True)
    
    else:
        st.info("Hãy tải file JSON để bắt đầu.")

if __name__ == "__main__":
    main()
