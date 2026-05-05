import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="JSON Analyzer", layout="wide")

if 'df' not in st.session_state:
    st.session_state.df = None

with st.sidebar:
    st.header("Cấu hình")
    uploaded_file = st.file_uploader("Tải file JSON", type=['json'])
    if st.button("Reset / Xóa dữ liệu"):
        st.session_state.df = None
        st.rerun()

if uploaded_file is not None:
    try:
        data = json.load(uploaded_file)
        st.session_state.df = pd.json_normalize(data)
    except Exception as e:
        st.error(f"Lỗi: {e}")

if st.session_state.df is not None:
    df = st.session_state.df
    st.success("Tải dữ liệu thành công!")
    
    col_time = st.selectbox("Chọn cột thời gian (để lọc):", [None] + list(df.columns))
    if col_time:
        df[col_time] = pd.to_datetime(df[col_time], errors='coerce')
        start = st.date_input("Ngày bắt đầu", df[col_time].min())
        end = st.date_input("Ngày kết thúc", df[col_time].max())
        df = df[(df[col_time].dt.date >= start) & (df[col_time].dt.date <= end)]

    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    val_col = st.selectbox("Chọn cột giá trị để vẽ:", numeric_cols)
    
    if val_col:
        fig = px.line(df, x=col_time if col_time else df.index, y=val_col, markers=True)
        st.plotly_chart(fig, use_container_width=True)
        
    st.dataframe(df, use_container_width=True)
