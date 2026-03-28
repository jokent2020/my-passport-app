import streamlit as st
import pandas as pd
import numpy as np
import easyocr
from PIL import Image
import re

st.set_page_config(page_title="證件管理系統", layout="wide")

st.title("🛂 護照資訊辨識與整理系統")

# 初始化辨識引擎 (支援繁體中文與英文)
@st.cache_resource
def load_reader():
    return easyocr.Reader(['ch_tra', 'en'])

reader = load_reader()

# 初始化資料表格
if 'data_list' not in st.session_state:
    st.session_state.data_list = []

# 上傳照片
uploaded_file = st.file_uploader("請拍攝或上傳護照照片", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    img = Image.open(uploaded_file)
    st.image(img, caption="已上傳的照片", width=300)
    
    if st.button("🚀 開始辨識"):
        with st.spinner('正在分析資訊...'):
            img_np = np.array(img)
            result = reader.readtext(img_np, detail=0)
            all_text = " ".join(result)
            
            # --- 簡易自動辨識邏輯 (這部分可視需求強化) ---
            passport_no = re.findall(r'[A-Z][0-9]{8}', all_text)
            # ----------------------------------------

            # 根據你的要求建立預設欄位
            new_data = {
                "核對狀態": "待核對",
                "繁體姓名": "",
                "英文姓名": "",
                "出生日期": "",
                "性別": "",
                "護照號碼": passport_no[0] if passport_no else "",
                "護照效期": "",
                "台胞證號": "",
                "台胞證效期": "",
                "台灣身分證號": "",
                "文件狀態": "已掃描",
                "護照照片": uploaded_file.name
            }
            st.session_state.data_list.append(new_data)
            st.success("辨識完成！請在下方表格修正資訊。")

# 顯示與編輯表格
if st.session_state.data_list:
    st.subheader("📋 資料整理清單")
    df = pd.DataFrame(st.session_state.data_list)
    
    # 使用可編輯表格
    edited_df = st.data_editor(df, num_rows="dynamic")
    
    # 一鍵導出
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 清空所有資料"):
            st.session_state.data_list = []
            st.rerun()
            
    with col2:
        file_name = "護照資料匯出.xlsx"
        edited_df.to_excel(file_name, index=False)
        with open(file_name, "rb") as f:
            st.download_button(
                label="📥 一鍵導出 Excel",
                data=f,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.info("目前尚無資料，請上傳照片開始。")
