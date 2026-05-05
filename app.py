import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="JSON Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích JSON Nâng cao")
    
    with st.sidebar:
        uploaded_file = st.file_uploader("Tải file JSON", type=['json'])
        if st.button("Reset / Xóa dữ liệu"):
            st.session_state.df = None
            st.rerun()

    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            # Làm phẳng dữ liệu
            df = pd.json_normalize(data)
            
            # --- XỬ LÝ DỮ LIỆU ĐỂ KHÔNG BỊ NONE ---
            # 1. Thay vì để None, ta điền là "N/A" để bảng nhìn rõ hơn
            df = df.fillna("N/A")
            
            # 2. Ép kiểu số cho tất cả các cột có thể ép được
            for col in df.columns:
                # Bỏ qua cột _id.$oid vì nó là ID không cần vẽ biểu đồ
                if "_id" not in col:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
            
            st.session_state.df = df
        except Exception as e:
            st.error(f"Lỗi: {e}")

    if 'df' in st.session_state and st.session_state.df is not None:
        df = st.session_state.df
        
        # 3. Chọn cột vẽ biểu đồ (chỉ hiện cột số)
        st.subheader("📈 Trực quan hóa")
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        selected_keys = st.multiselect("Chọn các chỉ số muốn vẽ:", numeric_cols)
        
        if selected_keys:
            for key in selected_keys:
                fig = px.line(df, y=key, title=f"Biểu đồ: {key}")
                fig.update_traces(mode='lines+markers', line_color='#E74C3C')
                st.plotly_chart(fig, use_container_width=True)
        
        # 4. Bảng dữ liệu hiển thị đầy đủ
        st.subheader("📋 Bảng dữ liệu chi tiết")
        st.data_editor(df, use_container_width=True, disabled=True)

if __name__ == "__main__":
    main()
