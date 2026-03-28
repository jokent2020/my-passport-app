import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import re
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="跨境資料整合助手", layout="wide", initial_sidebar_state="collapsed")

# 注入自定義 CSS 仿造 React 提供的深色 UI
st.markdown("""
<style>
    .main { background-color: #020617; color: #f1f5f9; }
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .stDataFrame { border: 1px solid #1e293b; border-radius: 15px; }
</style>
""", unsafe_allow_html=True)

# --- 初始化 Gemini AI ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

# --- 初始化資料儲存 (Session State) ---
if 'records' not in st.session_state:
    st.session_state.records = {} # 使用字典，以姓名為 Key 方便合併

# --- 核心邏輯：更新或新增紀錄 ---
def update_records(new_data):
    # 根據姓名(繁)或英文姓名作為合併基準
    name_key = new_data.get("nameTraditional") or new_data.get("nameEN")
    if not name_key:
        return

    if name_key in st.session_state.records:
        # 如果人名已存在，則合併資料 (補洞)
        old_data = st.session_state.records[name_key]
        for key, value in new_data.items():
            if value: # 只更新有抓到新資料的欄位
                old_data[key] = value
    else:
        # 新增紀錄
        st.session_state.records[name_key] = new_data

# --- 調用 AI 辨識 ---
def process_with_gemini(image):
    prompt = """
    你是一個專業證件辨識專家。請分析這張圖片，並嚴格回傳 JSON 格式。
    如果是護照，請填入 passport 欄位；如果是台胞證，請填入 permit 欄位。
    JSON 格式如下：
    {
        "nameTraditional": "姓名(繁體)",
        "nameEN": "英文姓名(大寫)",
        "birthDate": "YYYY.MM.DD",
        "gender": "男/女",
        "passportNo": "護照號碼",
        "passportExpiry": "YYYY.MM.DD",
        "permitNo": "台胞證號",
        "permitExpiry": "YYYY.MM.DD",
        "taiwanID": "台灣身分證號"
    }
    """
    response = model.generate_content([prompt, image])
    try:
        # 提取 JSON 字串
        clean_json = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(clean_json)
    except:
        return None

# --- UI 佈局 ---
st.title("🛡️ 跨境資料整合助手")
st.caption("支援批量上傳護照、台胞證，自動偵測重複並合併資料")

# 檔案上傳
uploaded_files = st.file_uploader("點擊或拖拽上傳證件照片...", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"🚀 開始處理 {len(uploaded_files)} 個檔案"):
        progress_bar = st.progress(0)
        for i, file in enumerate(uploaded_files):
            img = Image.open(file)
            result = process_with_gemini(img)
            if result:
                update_records(result)
            progress_bar.progress((i + 1) / len(uploaded_files))
        st.success("處理完成！")

# --- 資料清單 ---
st.markdown("---")
st.subheader(f"👥 旅客名單 ({len(st.session_state.records)})")

if st.session_state.records:
    # 轉換成 DataFrame 顯示
    df = pd.DataFrame(list(st.session_state.records.values()))
    
    # 欄位重新排序與美化標籤
    column_mapping = {
        "nameTraditional": "姓名(繁)",
        "nameEN": "英文姓名",
        "birthDate": "出生日期",
        "gender": "性別",
        "passportNo": "護照號碼",
        "passportExpiry": "護照效期",
        "permitNo": "台胞證號",
        "permitExpiry": "台胞證效期",
        "taiwanID": "台灣身分證"
    }
    df = df.rename(columns=column_mapping)
    
    # 可編輯表格
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    # 匯出與重置
    col_dl, col_rs = st.columns([4, 1])
    with col_dl:
        csv = edited_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 CSV 報表", data=csv, file_name=f"跨境資料_{datetime.now().strftime('%m%d')}.csv", mime='text/csv')
    with col_rs:
        if st.button("🗑️ 重置清單", type="secondary"):
            st.session_state.records = {}
            st.rerun()
else:
    st.info("目前尚無紀錄，請上傳證件照片。")

# 頁尾
st.markdown("<br><p style='text-align: center; opacity: 0.3; font-size: 0.8rem;'>TOUR OPERATION INTELLIGENCE V3.0</p>", unsafe_allow_html=True)
