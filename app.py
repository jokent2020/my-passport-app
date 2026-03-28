import streamlit as st
import pandas as pd
import numpy as np
import easyocr
from PIL import Image, ImageOps, ImageEnhance
import re

# 頁面設定
st.set_page_config(page_title="專業護照掃描器", layout="wide")
st.title("🛡️ 專業護照資訊提取系統 (MRZ 優化版)")

# 初始化辨識引擎 (限定英文與數字，提高 MRZ 辨識率)
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en']) # 護照關鍵資訊主要在英文區

reader = load_reader()

def preprocess_image(image):
    """加強圖片品質，幫助 OCR 辨識"""
    image = ImageOps.grayscale(image) # 轉灰階
    image = ImageEnhance.Contrast(image).enhance(2.0) # 增加對比
    return image

def parse_mrz(text_list):
    """
    專門解析護照底部兩行 MRZ (ICAO 9303 標準)
    這兩行通常以 P< 開頭
    """
    mrz_lines = []
    # 尋找包含大量 <<<< 的行
    for line in text_list:
        clean_line = line.replace(" ", "").upper()
        if "<<" in clean_line and len(clean_line) > 20:
            mrz_lines.append(clean_line)
    
    info = {
        "護照號碼": "",
        "英文姓名": "",
        "出生日期": "",
        "性別": "",
        "護照效期": ""
    }

    if len(mrz_lines) >= 2:
        line1 = mrz_lines[-2] # 倒數第二行 (姓名行)
        line2 = mrz_lines[-1] # 最後一行 (資料行)

        try:
            # 解析護照號碼 (Line 2 的前 9 碼)
            info["護照號碼"] = line2[0:9].replace("<", "")
            
            # 解析英文姓名 (Line 1 從第 5 碼開始)
            name_part = line1[5:].split("<<")
            surname = name_part[0].replace("<", " ")
            given_name = name_part[1].replace("<", " ") if len(name_part) > 1 else ""
            info["英文姓名"] = f"{surname} {given_name}".strip()

            # 解析出生日期 (Line 2 第 14-19 碼, 格式 YYMMDD)
            dob = line2[13:19]
            info["出生日期"] = f"{dob[0:2]}/{dob[2:4]}/{dob[4:6]}"

            # 解析性別 (Line 2 第 21 碼)
            info["性別"] = "M" if line2[20] == "M" else ("F" if line2[20] == "F" else "U")

            # 解析效期 (Line 2 第 22-27 碼, 格式 YYMMDD)
            exp = line2[21:27]
            info["護照效期"] = f"20{exp[0:2]}/{exp[2:4]}/{exp[4:6]}"
        except:
            pass # 如果解析失敗，回傳空值讓使用者手動填寫

    return info

# 初始化清單
if 'data_list' not in st.session_state:
    st.session_state.data_list = []

uploaded_file = st.file_uploader("請上傳或拍攝護照 (請確保底部兩行文字清晰、無反光)", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="原始圖片", width=400)
    
    if st.button("🔍 執行精準辨識"):
        with st.spinner('正在分析 MRZ 區域...'):
            processed_img = preprocess_image(img)
            # 辨識文字
            result = reader.readtext(np.array(processed_img), detail=0)
            
            # 偵錯用：顯示辨識出的原始文字 (隱藏在摺疊選單)
            with st.expander("查看原始辨識文字 (偵錯用)"):
                st.write(result)

            # 解析資料
            mrz_info = parse_mrz(result)
            
            # 填入你的欄位架構
            row_data = {
                "核對狀態": "待核對",
                "繁體姓名": "", # OCR 難以準確辨識繁體中文，建議手動輸入
                "英文姓名": mrz_info["英文姓名"],
                "出生日期": mrz_info["出生日期"],
                "性別": mrz_info["性別"],
                "護照號碼": mrz_info["護照號碼"],
                "護照效期": mrz_info["護照效期"],
                "台胞證號": "",
                "台胞證效期": "",
                "台灣身分證號": "",
                "文件狀態": "已掃描",
                "檔案名稱": uploaded_file.name
            }
            st.session_state.data_list.append(row_data)

if st.session_state.data_list:
    df = pd.DataFrame(st.session_state.data_list)
    edited_df = st.data_editor(df, num_rows="dynamic")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空表格"):
            st.session_state.data_list = []
            st.rerun()
    with col2:
        file_name = "護照資料匯出.xlsx"
        edited_df.to_excel(file_name, index=False)
        st.download_button("📥 下載 Excel", data=open(file_name, "rb"), file_name=file_name)
