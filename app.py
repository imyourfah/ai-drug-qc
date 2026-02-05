import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="AI QC Super App", page_icon="🧬", layout="wide")
st.title("🏥 AI Pharma QC: ระบบตรวจ COA (All-in-One)")

# --- ระบบความจำสำหรับกล้อง (Session State) ---
if 'camera_images' not in st.session_state:
    st.session_state['camera_images'] = [] # อัลบั้มเก็บรูป
if 'camera_key' not in st.session_state:
    st.session_state['camera_key'] = 0     # ตัวรีเซ็ตกล้อง

# ฟังก์ชันล้างรูป
def clear_images():
    st.session_state['camera_images'] = []
    st.session_state['camera_key'] += 1

# --- ฟังก์ชันช่วย: หาโมเดลที่ดีที่สุด ---
def get_best_model():
    model_name = None
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name and 'vision' not in m.name:
                    model_name = m.name
                    if 'flash' in m.name: 
                        break
        if not model_name: 
            model_name = 'models/gemini-1.5-flash'
        return model_name
    except:
        return None

# --- ฟังก์ชันช่วย: โหลด Database ---
@st.cache_data
def load_data(url):
    try:
        csv_url = url.replace('/edit?usp=sharing', '/export?format=csv').replace('/edit', '/export?format=csv')
        df = pd.read_csv(csv_url)
        return df
    except:
        return None

# ==========================================
# SIDEBAR: ตั้งค่า & สถานะระบบ
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Key และ Link ที่คุณระบุมา
    api_key = "AIzaSyDecXnEY-wlLVjeQLkQyKuxmjLhwHdvr_Q"
    sheet_url = "https://docs.google.com/spreadsheets/d/1ASUPDJ_p0dV2hCGN4btD3PFGoBJyCBZEbJXs376k8MQ/edit?usp=sharing"
    
    st.markdown("---")
    st.header("📡 System Status")
    
    active_model = None
    
    if api_key and sheet_url:
        try:
            genai.configure(api_key=api_key)
            active_model = get_best_model()
            
            if active_model:
                st.success(f"✅ Connected!")
                st.info(f"🧠 Model: **{active_model}**")
            else:
                st.error("❌ API Key ผิด หรือเชื่อมต่อไม่ได้")
        except:
             st.error("❌ API Key ผิด")
    else:
        st.warning("⚠️ กรุณาใส่ Key และ Link ในโค้ด")

# ==========================================
# MAIN APP
# ==========================================
if active_model and sheet_url:
    # โหลด Database
    df = load_data(sheet_url)
    
    if df is not None:
        # เตรียม Context
        db_context = ""
        for index, row in df.iterrows():
            if len(row) >= 3:
                db_context += f"Drug: {row[1]} | Spec: {row[2]}\n"
        
        st.success(f"📚 ฐานข้อมูลพร้อม: มียา {len(df)} รายการ")
        
        # --- ส่วนรับรูปภาพ (TABs) ---
        st.subheader("📸 นำเข้าใบ COA")
        
        tab1, tab2 = st.tabs(["📂 อัปโหลดไฟล์ (Upload)", "📷 ถ่ายรูป (Camera)"])
        
        all_images = [] # ลิสต์รวมรูปที่จะส่งให้ AI

        # Tab 1: Upload File
        with tab1:
            uploaded_files = st.file_uploader("เลือกไฟล์รูปภาพ (ได้หลายไฟล์)", 
                                            type=["jpg", "png", "jpeg"], 
                                            accept_multiple_files=True)
            if uploaded_files:
                for f in uploaded_files:
                    all_images.append(Image.open(f))

        # Tab 2: Camera Input
        with tab2:
            col_cam, col_preview = st.columns([1, 2])
            
            # ด้านซ้าย: กล้องถ่ายรูป
            with col_cam:
                st.write("📸 **ถ่ายทีละรูป**")
                pic = st.camera_input("Take Photo", key=f"cam_{st.session_state['camera_key']}")
                
                if pic:
                    st.session_state['camera_images'].append(Image.open(pic))
                    st.session_state['camera_key'] += 1
                    st.rerun()

            # ด้านขวา: โชว์รูปที่ถ่ายไว้แล้ว
            with col_preview:
                if st.session_state['camera_images']:
                    st.write(f"✅ ถ่ายไว้แล้ว {len(st.session_state['camera_images'])} รูป")
                    
                    # เอารูปจากกล้อง ไปรวมกับ List หลัก (all_images)
                    all_images.extend(st.session_state['camera_images'])
                    
                    st.image(st.session_state['camera_images'], width=100)
                    
                    if st.button("🗑️ ล้างรูปทั้งหมด", on_click=clear_images):
                        st.rerun()

        # --- ส่วนแสดงผลและปุ่มกด ---
        if all_images:
            st.markdown("---")
            st.write(f"📂 **พร้อมตรวจสอบทั้งหมด: {len(all_images)} ภาพ**")
            
            # โชว์รูปเรียงกัน
            cols = st.columns(min(len(all_images), 3))
            for idx, img in enumerate(all_images):
                with cols[idx % 3]:
                    st.image(img, caption=f"Img {idx+1}", use_column_width=True)
            
            # ปุ่ม Run
            if st.button("🚀 เริ่มตรวจสอบ (Analyze All)", type="primary"):
                with st.spinner(f"กำลังส่งข้อมูลให้ {active_model} วิเคราะห์..."):
                    model = genai.GenerativeModel(active_model)
                    
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
                    
                    Output: Markdown Table.
                    """
                    
                    try:
                        response = model.generate_content([prompt, *all_images])
                        st.markdown(response.text)
                        if "PASS" in response.text:
                            st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("👈 กรุณาอัปโหลดไฟล์ หรือถ่ายรูปก่อนกดตรวจสอบครับ")

    else:
        st.error("❌ อ่าน Google Sheet ไม่ได้ (เช็ค Link นะครับ)")
else:
    st.write("👈 กรุณาตั้งค่าที่แถบด้านซ้าย")
