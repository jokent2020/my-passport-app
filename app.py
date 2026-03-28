import streamlit as st
import pandas as pd
from google.cloud import vision
from google.oauth2 import service_account
import json
import re
from PIL import Image
import io

# 頁面配置
st.set_page_config(page_title="Google AI 護照掃描", layout="wide")
st.title("🚀 Google AI 護照極速辨識系統")

# --- 終極金鑰修復區塊 ---
if "GCP_SERVICE_ACCOUNT" in st.secrets:
    try:
        # 讀取 JSON
        raw_json = st.secrets["GCP_SERVICE_ACCOUNT"].strip()
        info = json.loads(raw_json)
        
        # 針對 private_key 進行徹底修復
        if "private_key" in info:
            key = info["private_key"]
            
            # 1. 處理常見的雙重轉義問題
            key = key.replace("\\n", "\n")
            
            # 2. 確保 PEM 格式的開頭和結尾有正確的換行
            if "-----BEGIN PRIVATE KEY-----" in key and not key.startswith("-----BEGIN PRIVATE KEY-----\n"):
                key = key.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
            if "-----END PRIVATE KEY-----" in key and "\n-----END PRIVATE KEY-----" not in key:
                key = key.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
            
            # 3. 如果中間的內容完全沒有換行，這也是錯誤的，Google 要求的私鑰每 64 字元要一個換行
            # 但通常 .replace("\\n", "\n") 就能解決
            
            info["private_key"] = key

        credentials = service_account.Credentials.from_service_account_info(info)
        client = vision.ImageAnnotatorClient(credentials=credentials)
    except Exception as e:
        st.error(f"金鑰解析失敗: {str(e)}")
        st.stop()
else:
    st.error("請在 Streamlit Secrets 中設定 GCP_SERVICE_ACCOUNT")
    st.stop()
# 初始化清單
if 'data_list' not in st.session_state:
    st.session_state.data_list = []

uploaded_file = st.file_uploader("📷 拍攝或上傳護照 (Google AI 會自動辨識繁體中文)", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    image_content = uploaded_file.read()
    st.image(image_content, width=400)
    
    if st.button("✨ 執行 Google AI 辨識"):
        with st.spinner('Google AI 正在辨識中...'):
            # 送往 Google Vision API
            image = vision.Image(content=image_content)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if not texts:
                st.warning("沒偵測到任何文字，請重新拍照。")
            else:
                full_text = texts[0].description
                lines = full_text.split('\n')
                
                # --- 強大的正規表達式過濾 (針對台灣護照) ---
                # 1. 抓護照號碼 (通常是 9 碼，且大寫開頭)
                p_no_match = re.search(r'[A-Z][0-9]{8}', full_text)
                p_no = p_no_match.group(0) if p_no_match else ""
                
                # 2. 抓繁體姓名 (簡單邏輯：找第一行長度為 2-4 的中文字)
                c_name = ""
                for line in lines:
                    c_matches = re.findall(r'[\u4e00-\u9fa5]{2,4}', line)
                    if c_matches:
                        c_name = c_matches[0]
                        break
                
                # 3. 抓 MRZ (底部兩行) 用於解析英文名
                mrz_lines = [l for l in lines if "<<" in l]
                e_name = ""
                if mrz_lines:
                    # 簡易提取英文名
                    e_name = mrz_lines[0].replace("<", " ").strip()

                # 建立你的欄位架構
                row_data = {
                    "核對狀態": "待核對",
                    "繁體姓名": c_name,
                    "英文姓名": e_name,
                    "出生日期": "", # 日期格式多變，建議手動微調
                    "性別": "",
                    "護照號碼": p_no,
                    "護照效期": "",
                    "台胞證號": "",
                    "台胞證效期": "",
                    "台灣身分證號": "",
                    "文件狀態": "辨識完成",
                    "護照照片": uploaded_file.name
                }
                st.session_state.data_list.append(row_data)
                st.success("Google AI 辨識成功！")

# 顯示表格
if st.session_state.data_list:
    df = pd.DataFrame(st.session_state.data_list)
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空表格"):
            st.session_state.data_list = []
            st.rerun()
    with col2:
        file_name = "護照資料匯出.xlsx"
        edited_df.to_excel(file_name, index=False)
        st.download_button("📥 下載 Excel", data=open(file_name, "rb"), file_name=file_name)
