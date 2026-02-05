import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="AI QC Super App", page_icon="🧬", layout="wide")
st.title("🏥 AI Pharma QC: ระบบตรวจ COA (All-in-One)")

# --- ประกาศตัวแปร Global ไว้ก่อน (กัน Error) ---
active_model = None 
api_key = None
sheet_url = None

# --- ระบบความจำสำหรับกล้อง (Session State) ---
if 'camera_images' not in st.session_state:
    st.session_state['camera_images'] = [] 
if 'camera_key' not in st.session_state:
    st.session_state['camera_key'] = 0     

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

# --- ฟังก์ชันช่วย: โหลด Database (เพิ่ม Cache TTL=60 วิ) ---
@st.cache_data(ttl=60)
def load_data(url):
    try:
        csv_url = url.replace('/edit?usp=sharing', '/export?format=csv').replace('/edit', '/export?format=csv')
        df = pd.read_csv(csv_url)
        return df
    except:
        return None

# ==========================================
# SIDEBAR: ตั้งค่า & เชื่อมต่อ
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # 1. พยายามดึง Key จาก Secrets ก่อน
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        # ถ้าไม่มีใน Secrets ให้กรอกเอง (สำรอง)
        api_key = st.text_input("Gemini API Key", type="password")

    # 2. พยายามดึง Link จาก Secrets ก่อน
    if "SHEET_LINK" in st.secrets:
        sheet_url = st.secrets["SHEET_LINK"]
    else:
        sheet_url = st.text_input("Link Google Sheet")
    
    st.markdown("---")
    
    # ปุ่มอัปเดตข้อมูล (Clear Cache)
    if st.button("🔄 อัปเดตฐานข้อมูล (Refresh)"):
        st.cache_data.clear()
        st.rerun()

    st.header("📡 System Status")
    
    # 3. เริ่มเชื่อมต่อ (สร้าง active_model ตรงนี้)
    if api_key and sheet_url:
        try:
            genai.configure(api_key=api_key)
            active_model = get_best_model() # <--- จุดสำคัญ! ห้ามหาย
            
            if active_model:
                st.success(f"✅ Connected!")
                st.info(f"🧠 Model: **{active_model}**")
            else:
                st.error("❌ API Key ผิด หรือเชื่อมต่อไม่ได้")
        except Exception as e:
             st.error(f"❌ Connection Error: {e}")
    else:
        st.warning("⚠️ กรุณาตั้งค่า Key และ Link")

# ==========================================
# MAIN APP
# ==========================================
# ตรวจสอบว่าตัวแปรมีค่าครบไหม
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
        
        all_images = [] 

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
            
            with col_cam:
                st.write("📸 **ถ่ายทีละรูป**")
                pic = st.camera_input("Take Photo", key=f"cam_{st.session_state['camera_key']}")
                
                if pic:
                    st.session_state['camera_images'].append(Image.open(pic))
                    st.session_state['camera_key'] += 1
                    st.rerun()

            with col_preview:
                if st.session_state['camera_images']:
                    st.write(f"✅ ถ่ายไว้แล้ว {len(st.session_state['camera_images'])} รูป")
                    all_images.extend(st.session_state['camera_images'])
                    st.image(st.session_state['camera_images'], width=100)
                    
                    if st.button("🗑️ ล้างรูปทั้งหมด", on_click=clear_images):
                        st.rerun()

        # --- ส่วนแสดงผลและปุ่มกด ---
        if all_images:
            st.markdown("---")
            st.write(f"📂 **พร้อมตรวจสอบทั้งหมด: {len(all_images)} ภาพ**")
            
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
    # ถ้ายังไม่เชื่อมต่อ ไม่ต้องทำอะไร (รอ User ใส่ Key)
    st.write("👈 กรุณาตั้งค่า API Key และ Sheet Link ที่เมนูด้านซ้าย")
