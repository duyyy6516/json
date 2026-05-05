import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="JSON Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích File JSON")
    
    if 'df' not in st.session_state:
        st.session_state.df = None

    with st.sidebar:
        uploaded_file = st.file_uploader("Tải file JSON", type=['json'])
        if st.button("Reset / Xóa dữ liệu"):
            st.session_state.df = None
            st.rerun()

    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            df = pd.json_normalize(data)
            # Ép kiểu dữ liệu số tự động
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            st.session_state.df = df
        except Exception:
            pass

    if st.session_state.df is not None:
        df = st.session_state.df
        
        # Vẽ biểu đồ tự động tất cả các cột số
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            st.subheader("📈 Biểu đồ dữ liệu")
            fig = px.line(df, y=numeric_cols, title="Biểu đồ tất cả các chỉ số")
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

        # Hiển thị bảng
        st.subheader("📋 Dữ liệu thô")
        st.data_editor(
            df, 
            use_container_width=True,
            column_config={col: st.column_config.TextColumn(col, width="medium") for col in df.columns},
            disabled=True
        )
    else:
        st.info("Hãy tải file JSON ở menu bên trái.")

if __name__ == "__main__":
    main()
