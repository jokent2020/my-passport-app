import streamlit as st
import pandas as pd
from google.cloud import vision
from google.oauth2 import service_account
import json
import re
from PIL import Image
import io

# 頁面配置
st.set_page_config(page_title="專業證件批量辨識系統", layout="wide")
st.title("🗂️ 證件批量辨識與自動歸檔系統")
st.markdown("---")

# 1. 讀取 Google AI 鑰匙 (沿用先前的設定)
if "GCP_SERVICE_ACCOUNT" in st.secrets:
    try:
        raw_json = st.secrets["GCP_SERVICE_ACCOUNT"].strip()
        info = json.loads(raw_json)
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        credentials = service_account.Credentials.from_service_account_info(info)
        client = vision.ImageAnnotatorClient(credentials=credentials)
    except Exception as e:
        st.error(f"金鑰解析失敗: {e}")
        st.stop()
else:
    st.error("請先設定 Secrets!")
    st.stop()

# 2. 初始化 Session State 儲存資料
if 'master_df' not in st.session_state:
    st.session_state.master_df = pd.DataFrame(columns=[
        "核對狀態", "證件類型", "繁體姓名", "英文姓名", "出生日期", "性別", 
        "護照號碼", "護照效期", "台胞證號", "台胞證效期", "台灣身分證號", "文件狀態", "原始檔名"
    ])

# --- 強大的資料提取函數 ---
def extract_document_info(full_text, filename):
    text = full_text.upper()
    data = {
        "核對狀態": "待核對",
        "證件類型": "未知",
        "繁體姓名": "",
        "英文姓名": "",
        "出生日期": "",
        "性別": "",
        "護照號碼": "",
        "護照效期": "",
        "台胞證號": "",
        "台胞證效期": "",
        "台灣身分證號": "",
        "文件狀態": "辨識成功",
        "原始檔名": filename
    }

    # 判斷證件類型
    if "PASSPORT" in text or "P<" in text:
        data["證件類型"] = "護照"
    elif "台胞證" in text or "MAINLAND" in text or "TRAVEL PERMIT" in text:
        data["證件類型"] = "台胞證"
    else:
        data["證件類型"] = "需人工判斷"

    # 提取身分證號 (1字母+9數字)
    id_match = re.search(r'[A-Z][1-2][0-9]{8}', text)
    if id_match: data["台灣身分證號"] = id_match.group(0)

    # 提取護照號碼 (通常為 9 碼，大寫字母開頭)
    p_match = re.search(r'[A-Z][0-9]{8}', text)
    if p_match: data["護照號碼"] = p_match.group(0)

    # 提取台胞證號 (8位數字)
    mtp_match = re.search(r'[^0-9]([0-9]{8})[^0-9]', text)
    if mtp_match: data["台胞證號"] = mtp_match.group(1)

    # 提取繁體中文姓名 (找 2-4 個中文字)
    c_names = re.findall(r'[\u4e00-\u9fa5]{2,4}', full_text)
    if c_names: 
        # 過濾掉「中華民國」、「護照」等關鍵字
        filtered_names = [n for n in c_names if n not in ["中華民國", "護照", "台灣", "台胞證"]]
        if filtered_names: data["繁體姓名"] = filtered_names[0]

    # 提取日期 (YYYY.MM.DD 或 YYYY/MM/DD)
    dates = re.findall(r'(\d{4}[./]\d{2}[./]\d{2})', text)
    if dates:
        data["出生日期"] = dates[0]
        if len(dates) > 1: data["護照效期"] = dates[-1]

    return data

# --- UI 介面 ---
col_up, col_info = st.columns([1, 1])

with col_up:
    st.subheader("1. 批量上傳照片")
    uploaded_files = st.file_uploader("可同時選取多張護照與台胞證圖片", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 開始批量分析", use_container_width=True):
        new_rows = []
        progress_bar = st.progress(0)
        
        for index, file in enumerate(uploaded_files):
            # 讀取圖片
            content = file.read()
            image = vision.Image(content=content)
            
            # Google AI 辨識
            response = client.text_detection(image=image)
            if response.text_annotations:
                full_text = response.text_annotations[0].description
                # 提取與分類
                row_info = extract_document_info(full_text, file.name)
                new_rows.append(row_info)
            
            progress_bar.progress((index + 1) / len(uploaded_files))
        
        # 合併到主表格
        new_df = pd.DataFrame(new_rows)
        st.session_state.master_df = pd.concat([st.session_state.master_df, new_df], ignore_index=True)
        st.success(f"成功處理 {len(new_rows)} 份文件！")

# 3. 資料整理區
st.markdown("---")
st.subheader("2. 資料核對與整理中心")

if not st.session_state.master_df.empty:
    # 讓使用者可以點擊刪除或修改
    edited_df = st.data_editor(
        st.session_state.master_df, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "核對狀態": st.column_config.SelectboxColumn("核對狀態", options=["待核對", "正確", "有誤"]),
            "性別": st.column_config.SelectboxColumn("性別", options=["M", "F"]),
        }
    )
    st.session_state.master_df = edited_df

    # 4. 一鍵導出
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🧹 清空清單"):
            st.session_state.master_df = st.session_state.master_df.iloc[0:0]
            st.rerun()
    with c3:
        file_name = "證件資料彙整表.xlsx"
        edited_df.to_excel(file_name, index=False)
        with open(file_name, "rb") as f:
            st.download_button(
                label="📥 下載整理好的 Excel 報表",
                data=f,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
else:
    st.info("尚未上傳任何檔案。")
