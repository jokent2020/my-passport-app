import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import re
from datetime import datetime

# --- 1. 頁面基礎配置與 CSS 注入 (UI/UX 核心) ---
st.set_page_config(
    page_title="跨境資料整合助手 | PRO",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 全局背景與字體 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;900&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #020617;
        font-family: 'Inter', sans-serif;
        color: #f1f5f9;
    }

    /* 隱藏預設元件 */
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {display: none !important;}

    /* 卡片設計 */
    .st-emotion-cache-1r6slb0, .st-emotion-cache-1kyx0rg {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 24px !important;
        padding: 20px;
    }

    /* 自定義標題區 */
    .main-header {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 2.5rem;
        letter-spacing: -2px;
        margin-bottom: 0.5rem;
    }

    /* 功能按鈕美化 */
    .stButton>button {
        background: #6366f1 !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 800 !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(99, 102, 241, 0.4);
    }

    /* 下載按鈕 (特殊顏色) */
    [data-testid="stDownloadButton"] > button {
        background: #f8fafc !important;
        color: #0f172a !important;
    }

    /* 狀態標籤 */
    .status-badge {
        padding: 4px 12px;
        border-radius: 99px;
        font-size: 10px;
        font-weight: 900;
        text-transform: uppercase;
    }
    .status-verified { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
    .status-pending { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid #f59e0b; }

    /* 表格容器自定義 */
    div[data-testid="stDataFrame"] {
        border: 1px solid #1e293b;
        border-radius: 20px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 核心邏輯 (Gemini 1.5 Flash) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 自動選擇可用模型
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("❌ 尚未在 Secrets 中配置 GEMINI_API_KEY")
    st.stop()

if 'records' not in st.session_state:
    st.session_state.records = {}

def process_with_ai(image):
    prompt = """
    辨識證件資訊並回傳 JSON。必須包含：
    {
        "nameTraditional": "姓名(繁)",
        "nameEN": "英文姓名(大寫)",
        "birthDate": "YYYY.MM.DD",
        "gender": "男/女",
        "passportNo": "護照號碼",
        "passportExpiry": "YYYY.MM.DD",
        "permitNo": "台胞證號",
        "permitExpiry": "YYYY.MM.DD",
        "taiwanID": "台灣身分證號"
    }
    如果欄位不存在請留空。
    """
    response = model.generate_content([prompt, image])
    try:
        clean_json = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(clean_json)
    except:
        return None

def update_db(new_data):
    # 合併邏輯：以姓名或英文姓名為 Key
    key = new_data.get("nameTraditional") or new_data.get("nameEN")
    if not key: return
    if key in st.session_state.records:
        st.session_state.records[key].update({k: v for k, v in new_data.items() if v})
    else:
        st.session_state.records[key] = new_data

# --- 3. UI 顯示區塊 ---

# Header Section
st.markdown('<p class="main-header">🛡️ 跨境資料助手 PRO</p>', unsafe_allow_html=True)
st.markdown('<p style="color:#64748b; font-weight:600; margin-top:-15px;">智能辨識 • 批量合併 • 快速導出</p>', unsafe_allow_html=True)

# 統計數據 (小卡片)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div style="background:#1e1b4b; padding:15px; border-radius:15px; border-left:4px solid #6366f1;">
        <p style="color:#818cf8; font-size:12px; font-weight:bold; margin:0;">已辨識旅客</p>
        <p style="font-size:24px; font-weight:900; margin:0;">{len(st.session_state.records)}</p>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div style="background:#064e3b; padding:15px; border-radius:15px; border-left:4px solid #10b981;">
        <p style="color:#34d399; font-size:12px; font-weight:bold; margin:0;">資料核對狀態</p>
        <p style="font-size:24px; font-weight:900; margin:0;">AI ENABLED</p>
    </div>""", unsafe_allow_html=True)

st.write("") # 留白

# 上傳區
with st.container():
    col_up, col_btn = st.columns([4, 1])
    with col_up:
        files = st.file_uploader("", type=['jpg','png','jpeg'], accept_multiple_files=True, label_visibility="collapsed")
    with col_btn:
        st.write("") # 對齊用
        run_btn = st.button("🚀 開始分析")

if files and run_btn:
    progress_container = st.empty()
    bar = st.progress(0)
    for i, f in enumerate(files):
        img = Image.open(f)
        result = process_with_ai(img)
        if result:
            update_db(result)
        bar.progress((i+1)/len(files))
    st.toast("✅ 批量分析完成！", icon='🎉')

# 資料整理區
if st.session_state.records:
    df = pd.DataFrame(list(st.session_state.records.values()))
    
    # 欄位美化
    display_cols = {
        "nameTraditional": "姓名(繁)", "nameEN": "英文姓名", "birthDate": "生日",
        "gender": "性別", "passportNo": "護照號", "passportExpiry": "護照效期",
        "permitNo": "台胞證號", "permitExpiry": "台胞效期", "taiwanID": "身分證"
    }
    df = df.rename(columns=display_cols)

    st.markdown("### 📋 旅客清單管理")
    # 使用可編輯表格，這裡可以讓使用者直接修正
    edited_df = st.data_editor(
        df, 
        use_container_width=True, 
        num_rows="dynamic",
        column_config={
            "性別": st.column_config.SelectboxColumn("性別", options=["男", "女"]),
        }
    )

    # 底部操作區
    st.write("")
    bc1, bc2, bc3 = st.columns([2, 2, 1])
    with bc1:
        csv = edited_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 Excel (CSV) 報表", data=csv, file_name=f"Passport_Data_{datetime.now().strftime('%m%d')}.csv")
    with bc3:
        if st.button("🔄 重置清單"):
            st.session_state.records = {}
            st.rerun()

else:
    st.markdown("""
    <div style="text-align:center; padding:100px; border:2px dashed #1e293b; border-radius:30px; opacity:0.5;">
        <p style="font-size:50px;">📸</p>
        <p style="font-weight:bold;">尚無數據，請先上傳證件照片</p>
    </div>
    """, unsafe_allow_html=True)

# 頁尾
st.markdown("<p style='text-align:center; margin-top:50px; opacity:0.2; font-size:10px; letter-spacing:5px;'>TOUR OPERATION INTELLIGENCE V3.0</p>", unsafe_allow_html=True)
