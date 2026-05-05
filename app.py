import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 1. Cấu hình trang
st.set_page_config(page_title="JSON Data Analyzer", layout="wide")

def main():
    st.title("📊 Phân tích JSON Nâng cao")
    
    # Khởi tạo lưu trữ dữ liệu
    if 'df' not in st.session_state:
        st.session_state.df = None

    # 2. Sidebar: Tải file
    with st.sidebar:
        st.header("Cấu hình")
        uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])
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
        
        st.subheader("🛠 Lựa chọn & Bộ lọc")
        
        # --- BỘ LỌC THỜI GIAN (ĐÃ SỬA LỖI VALUEERROR) ---
        col_time = st.selectbox("Chọn cột thời gian (để lọc khoảng thời gian):", [None] + list(df.columns))
        
        if col_time:
            # Copy để tránh lỗi ghi đè dữ liệu gốc
            df_temp = df.copy()
            # Chuyển đổi an toàn, gán NaT cho các giá trị không hợp lệ
            df_temp[col_time] = pd.to_datetime(df_temp[col_time], errors='coerce')
            
            # Chỉ lọc nếu có dữ liệu thời gian hợp lệ
            if not df_temp[col_time].isna().all():
                valid_df = df_temp.dropna(subset=[col_time])
                col1, col2 = st.columns(2)
                with col1:
                    start = st.date_input("Ngày bắt đầu", valid_df[col_time].min())
                with col2:
                    end = st.date_input("Ngày kết thúc", valid_df[col_time].max())
                
                # Áp dụng bộ lọc cho df chính
                df = df[(df_temp[col_time].dt.date >= start) & (df_temp[col_time].dt.date <= end)]
            else:
                st.info("Cột đã chọn không chứa định dạng thời gian hợp lệ.")

        # 4. CHỌN NHIỀU KEY & VẼ BIỂU ĐỒ
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        selected_keys = st.multiselect("Tích chọn các cột giá trị muốn vẽ:", numeric_cols)
        
        if selected_keys:
            x_axis = col_time if (col_time and col_time in df.columns) else None
            fig = px.line(df, x=x_axis, y=selected_keys, title="Biểu đồ các cột đã chọn")
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)

        # 5. BẢNG DỮ LIỆU HIỂN THỊ FULL
        st.subheader("📋 Bảng dữ liệu")
        st.data_editor(
            df, 
            use_container_width=True,
            column_config={
                col: st.column_config.TextColumn(col, width="medium") for col in df.columns
            },
            disabled=True
        )
    
    else:
        st.info("Hãy tải file JSON ở sidebar để bắt đầu.")

if __name__ == "__main__":
    main()
