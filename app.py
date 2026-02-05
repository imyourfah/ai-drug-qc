import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from PIL import Image
import datetime

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="AI Pharma Super App", page_icon="💊", layout="wide")
st.title("🏥 AI Pharma Hub: ระบบตรวจ QC และจัดการฐานข้อมูล")

# --- Initialize Session State ---
if 'camera_images' not in st.session_state: st.session_state['camera_images'] = []
if 'camera_key' not in st.session_state: st.session_state['camera_key'] = 0
if 'spec_images' not in st.session_state: st.session_state['spec_images'] = []
if 'spec_key' not in st.session_state: st.session_state['spec_key'] = 0

# --- Functions ---
def clear_cam_images():
    st.session_state['camera_images'] = []
    st.session_state['camera_key'] += 1

def clear_spec_images():
    st.session_state['spec_images'] = []
    st.session_state['spec_key'] += 1

@st.cache_resource
def connect_google_sheet():
    try:
        if "gcp_service_account" in st.secrets:
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            client = gspread.authorize(creds)
            return client
        else:
            return None
    except Exception as e:
        return None

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.header("🎮 Menu")
    app_mode = st.radio("เลือกโหมดทำงาน:", ["🕵️‍♀️ ตรวจสอบ QC (Checker)", "➕ เพิ่มยาใหม่ (Update DB)"])
    
    st.markdown("---")
    st.header("⚙️ Config")
    
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
        st.success("🔑 API Key: Ready")
    else:
        api_key = st.text_input("Gemini API Key", type="password")

    if "SHEET_LINK" in st.secrets:
        sheet_url = st.secrets["SHEET_LINK"]
        st.success("📄 Sheet: Ready")
    else:
        sheet_url = st.text_input("Link Google Sheet")

# ==========================================
# MAIN APP
# ==========================================
if api_key and sheet_url:
    genai.configure(api_key=api_key)
    gc = connect_google_sheet()
    
    # โหลดข้อมูล
    try:
        csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv').replace('/edit', '/export?format=csv')
        df = pd.read_csv(csv_url)
        db_context = ""
        for index, row in df.iterrows():
            if len(row) >= 3: db_context += f"Drug: {row[1]} | Spec: {row[2]}\n"
    except:
        df = pd.DataFrame()
        db_context = ""

    # ----------------------------------------------------
    # MODE 1: 🕵️‍♀️ ตรวจสอบ QC (Checker)
    # ----------------------------------------------------
    if app_mode == "🕵️‍♀️ ตรวจสอบ QC (Checker)":
        st.subheader("🕵️‍♀️ ตรวจสอบคุณภาพยา (QC Checker)")
        st.info(f"📚 ฐานข้อมูล: {len(df)} รายการ")
        
        tab1, tab2 = st.tabs(["📂 Upload COA", "📷 Camera"])
        qc_images = []

        with tab1:
            files = st.file_uploader("Upload COA Images", accept_multiple_files=True, key="qc_up")
            if files: 
                for f in files: qc_images.append(Image.open(f))

        with tab2:
            col_c, col_p = st.columns([1,2])
            with col_c:
                cam = st.camera_input("Take Photo", key=f"qc_cam_{st.session_state['camera_key']}")
                if cam:
                    st.session_state['camera_images'].append(Image.open(cam))
                    st.session_state['camera_key'] += 1
                    st.rerun()
            with col_p:
                if st.session_state['camera_images']:
                    st.image(st.session_state['camera_images'], width=100)
                    if st.button("🗑️ Clear", on_click=clear_cam_images): st.rerun()
                    qc_images.extend(st.session_state['camera_images'])

        if qc_images and st.button("🚀 Run QC Check", type="primary"):
            with st.spinner("AI Checking..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # --- PROMPT ที่แก้ให้แล้ว (ย่อหน้าถูกต้อง + มีอิโมจิ) ---
                prompt = f"""
                Role: Expert QC Pharmacist.
                Input DB: {db_context}
                Task: 
                1. Analyze ALL images as one COA document.
                2. Identify Drug Name.
                3. Extract Results & Compare with DB Spec.
                
                Universal Rules:
                - Range: Strict math check.
                - Limits: NMT/NLT check.
                - Ph. Eur. Color: B(X) -> Higher X is better (Pass). B1-B5 Fail.
                
                Output Requirements:
                - Generate a Markdown Table.
                - Add a column "Status".
                - In "Status": USE ONLY "PASS ✅" or "FAIL ❌".
                - If Drug Name doesn't match DB, mark "FAIL ❌".
                """
                
                try:
                    response = model.generate_content([prompt, *qc_images])
                    st.markdown(response.text)
                    
                    # สรุปผลตัวใหญ่
                    if "❌" in response.text:
                        st.error("❌ QC FAILED: มีรายการไม่ผ่านเกณฑ์", icon="🚨")
                    else:
                        st.success("✅ QC PASSED: ผ่านทุกรายการ", icon="✅")
                        st.balloons()
                except Exception as e: st.error(e)

    # ----------------------------------------------------
    # MODE 2: ➕ เพิ่มยาใหม่ (Update DB)
    # ----------------------------------------------------
    elif app_mode == "➕ เพิ่มยาใหม่ (Update DB)":
        st.subheader("➕ อัปเดตฐานข้อมูล (เพิ่ม Spec ยา)")
        
        tab_up, tab_cam = st.tabs(["📂 Upload Spec", "📷 Camera Spec"])
        spec_input_images = []

        with tab_up:
            s_files = st.file_uploader("เลือกรูป Spec", accept_multiple_files=True, key="spec_up")
            if s_files:
                for f in s_files: spec_input_images.append(Image.open(f))

        with tab_cam:
            c_col, p_col = st.columns([1,2])
            with c_col:
                s_cam = st.camera_input("ถ่าย Spec", key=f"spec_cam_{st.session_state['spec_key']}")
                if s_cam:
                    st.session_state['spec_images'].append(Image.open(s_cam))
                    st.session_state['spec_key'] += 1
                    st.rerun()
            with p_col:
                if st.session_state['spec_images']:
                    st.image(st.session_state['spec_images'], width=100)
                    if st.button("🗑️ Clear Spec", on_click=clear_spec_images): st.rerun()
                    spec_input_images.extend(st.session_state['spec_images'])

        if spec_input_images:
            if st.button("✨ แกะข้อมูลจากรูป"):
                with st.spinner("Reading Spec..."):
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = "Extract Drug Name and Full Spec details. Output format: Name: [Name] ### [Details]"
                    try:
                        res = model.generate_content([prompt, *spec_input_images])
                        parts = res.text.split("###")
                        st.session_state['new_drug_name'] = parts[0].replace("Name:", "").strip()
                        st.session_state['new_drug_spec'] = parts[1].strip() if len(parts) > 1 else res.text
                    except Exception as e: st.error(e)

        if 'new_drug_name' in st.session_state:
            with st.form("save_db_form"):
                n_name = st.text_input("Drug Name", value=st.session_state['new_drug_name'])
                n_spec = st.text_area("Spec Details", value=st.session_state['new_drug_spec'], height=200)
                if st.form_submit_button("💾 บันทึก"):
                    if gc:
                        try:
                            sh = gc.open_by_url(sheet_url)
                            sh.sheet1.append_row([datetime.datetime.now().strftime("%Y-%m-%d"), n_name, n_spec])
                            st.success(f"บันทึก {n_name} สำเร็จ!")
                            del st.session_state['new_drug_name']
                            del st.session_state['new_drug_spec']
                            clear_spec_images()
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                    else:
                        st.error("บันทึกไม่ได้: ไม่พบการตั้งค่า Service Account")
else:
    st.warning("กรุณาใส่ API Key และ Link ใน Secrets หรือ Sidebar")
