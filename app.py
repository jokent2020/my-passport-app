import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import re
from datetime import datetime
import uuid

# --- 1. UI 視覺風格配置 (仿 React Lucide 風格) ---
st.set_page_config(page_title="跨境資料整合助手", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #020617;
        color: #f1f5f9;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {display: none !important;}
    
    /* 模仿 React 的 Mode Switcher */
    .mode-container {
        display: flex;
        background: #0f172a;
        padding: 5px;
        border-radius: 15px;
        border: 1px solid #1e293b;
        margin-bottom: 20px;
    }
    
    /* 卡片設計 */
    .record-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
    }
    
    /* 按鈕樣式 */
    .stButton>button {
        border-radius: 12px !important;
        background: #4f46e5 !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 核心邏輯配置 (Gemini AI) ---
TODAY = datetime(2026, 3, 25)

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 自動偵測可用模型名稱以避免 NotFound 錯誤
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
        model = genai.GenerativeModel(model_name)
    except:
        st.error("API Key 驗證失敗或無可用模型")
        st.stop()
else:
    st.error("請先設定 GEMINI_API_KEY Secrets")
    st.stop()

# 初始化 Session State (對標 React 的 records)
if 'records' not in st.session_state:
    st.session_state.records = []

# --- 3. 仿 React 的「更新或新增」邏輯 (updateOrAddRecord) ---
def update_or_add_record(new_data):
    records = st.session_state.records
    found = False
    
    # 清理姓名空格以便比對
    def clean(s): return re.sub(r'[\s,]', '', str(s)).upper() if s else ""

    for r in records:
        # 匹配邏輯：英文名匹配 OR 繁體中文名匹配
        match_en = clean(r.get('nameEN')) == clean(new_data.get('nameEN')) and clean(new_data.get('nameEN')) != ""
        match_ch = clean(r.get('nameTraditional')) == clean(new_data.get('nameTraditional')) and clean(new_data.get('nameTraditional')) != ""
        
        if match_en or match_ch:
            # 找到現有紀錄，執行合併 (Merge)
            for key in new_data:
                if new_data[key]: # 只更新有值的欄位
                    r[key] = new_data[key]
            
            # 更新狀態標籤 (對標 React Logic)
            r['hasPassport'] = bool(r.get('passportNo'))
            r['hasPermitFront'] = bool(r.get('permitNo'))
            r['hasPermitBack'] = bool(r.get('taiwanID'))
            found = True
            break
            
    if not found:
        # 新增紀錄 (對標 React Logic)
        new_entry = {
            **new_data,
            "id": str(uuid.uuid4()),
            "checked": False,
            "hasPassport": bool(new_data.get('passportNo')),
            "hasPermitFront": bool(new_data.get('permitNo')),
            "hasPermitBack": bool(new_data.get('taiwanID'))
        }
        records.append(new_entry)
    
    st.session_state.records = records

# --- 4. 辨識處理程序 (processFile) ---
def process_file(image, mode):
    mode_restriction = ""
    if mode == '護照模式': mode_restriction = "現在是【護照專用模式】，若非護照請回傳 {\"error\": \"此文件非護照\"}"
    elif mode == '台胞證模式': mode_restriction = "現在是【台胞證專用模式】，若非台胞證請回傳 {\"error\": \"此文件非台胞證\"}"

    prompt = f"""你是一個專業證件辨識專家。{mode_restriction}
    請辨識圖片資訊並回傳 JSON 陣列格式：
    [{{
        "docType": "passport" | "permit_front" | "permit_back",
        "nameTraditional": "姓名(繁體)",
        "nameSimplified": "姓名(簡體)",
        "nameEN": "英文姓名(需準確大寫)",
        "birthDate": "YYYY.MM.DD",
        "gender": "男/女",
        "passportNo": "護照號碼",
        "passportExpiry": "YYYY.MM.DD",
        "permitNo": "台胞證號",
        "permitExpiry": "YYYY.MM.DD",
        "taiwanID": "台灣身分證號"
    }}]
    注意：英文姓名必須與證件底部 MRZ 區完全一致。"""

    response = model.generate_content([prompt, image])
    try:
        # 提取 JSON 內容
        json_str = re.search(r'\[.*\]|\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(json_str)
        return data if isinstance(data, list) else [data]
    except:
        return {"error": "辨識解析失敗"}

# --- 5. UI 介面佈局 ---
# 頂部導航
st.markdown('<h1 style="font-weight:900; letter-spacing:-2px;">🛡️ 跨境資料整合助手</h1>', unsafe_allow_html=True)

# 模式切換器 (仿 React Switcher)
filter_mode = st.radio("選擇辨識模式", ["整合模式", "護照模式", "台胞證模式"], horizontal=True, label_visibility="collapsed")

# 上傳區域
uploaded_files = st.file_uploader("點擊上傳證件 (支援批量)", type=['jpg','jpeg','png'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"🚀 開始執行 ({len(uploaded_files)} 個檔案)"):
        progress_bar = st.progress(0)
        for i, file in enumerate(uploaded_files):
            img = Image.open(file)
            results = process_file(img, filter_mode)
            
            if isinstance(results, dict) and "error" in results:
                st.error(f"檔案 {file.name}: {results['error']}")
            else:
                for item in results:
                    update_or_add_record(item)
            progress_bar.progress((i + 1) / len(uploaded_files))
        st.toast("✅ 批量辨識完成")

# --- 6. 名單顯示區 (仿 React Card List) ---
st.markdown(f"### 👥 旅客名單 ({len(st.session_state.records)})")

def is_expired(date_str):
    if not date_str: return False
    try:
        d = datetime.strptime(date_str.replace('.', '-'), '%Y-%m-%d')
        return d < TODAY
    except: return False

if st.session_state.records:
    # 轉換為 DataFrame 顯示方便編輯
    df = pd.DataFrame(st.session_state.records)
    
    # 重新整理顯示用的欄位
    display_df = df[[
        "checked", "nameTraditional", "nameEN", "birthDate", "gender", 
        "passportNo", "passportExpiry", "permitNo", "permitExpiry", "taiwanID"
    ]].copy()

    # 編輯區域
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "checked": st.column_config.CheckboxColumn("核對"),
            "gender": st.column_config.SelectboxColumn("性別", options=["男", "女"]),
        }
    )

    # 下載區 (對標 React 導出 CSV)
    c1, c2 = st.columns([4, 1])
    with c1:
        # 生成 CSV 下載
        csv_data = edited_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 下載整合後的 CSV 報表",
            data=csv_data,
            file_name=f"Passport_Export_{datetime.now().strftime('%m%d')}.csv",
            mime="text/csv"
        )
    with c2:
        if st.button("🗑️ 重置所有數據"):
            st.session_state.records = []
            st.rerun()
else:
    st.markdown("""
    <div style="text-align:center; padding:50px; border:2px dashed #1e293b; border-radius:20px; opacity:0.3;">
        <p style="font-size:40px;">📸</p>
        <p>尚未有任何紀錄，請開始上傳證件照片</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><p style='text-align:center; opacity:0.2; font-size:10px;'>TOUR OPERATION INTELLIGENCE V3.2</p>", unsafe_allow_html=True)
