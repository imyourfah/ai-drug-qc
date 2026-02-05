import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="AI QC Super App", page_icon="🧬", layout="wide")
st.title("🏥 AI Pharma QC: ระบบตรวจ COA (All-in-One)")

# --- ฟังก์ชันช่วย: หาโมเดลที่ดีที่สุด (เหมือนใน Colab) ---
def get_best_model():
    model_name = None
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name and 'vision' not in m.name:
                    model_name = m.name
                    # ถ้าเจอตัว Flash ให้เอาเลย (เร็วและถูก)
                    if 'flash' in m.name: 
                        break
        if not model_name: 
            model_name = 'models/gemini-1.5-flash' # fallback
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
    api_key = st.text_input("1. Gemini API Key", type="password")
    sheet_url = st.text_input("2. Link Google Sheet", help="อย่าลืมเปิด Share เป็น Anyone with link")
    
    st.markdown("---")
    st.header("📡 System Status")
    
    active_model = None
    
    # เช็คสถานะ API และ Model
    if api_key:
        genai.configure(api_key=api_key)
        active_model = get_best_model()
        
        if active_model:
            st.success(f"✅ Connected!")
            st.info(f"🧠 Model: **{active_model}**") # <--- โชว์ชื่อรุ่นตรงนี้ครับ
        else:
            st.error("❌ API Key ผิด หรือเชื่อมต่อไม่ได้")
    else:
        st.warning("⚠️ รอใส่ API Key")

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
        
        # สร้าง Tab ให้เลือกใช้ง่ายๆ
        tab1, tab2 = st.tabs(["📂 อัปโหลดไฟล์ (Upload)", "📷 ถ่ายรูป (Camera)"])
        
        all_images = [] # ลิสต์รวมรูปทั้งหมด (ทั้งจากอัปโหลดและกล้อง)

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
            camera_pic = st.camera_input("ถ่ายรูปใบ COA")
            if camera_pic:
                all_images.append(Image.open(camera_pic))
                st.success("บันทึกภาพจากกล้องแล้ว!")

        # --- ส่วนแสดงผลและปุ่มกด ---
        if all_images:
            st.markdown("---")
            st.write(f"📂 **ได้รับรูปภาพทั้งหมด: {len(all_images)} ภาพ**")
            
            # โชว์รูปเรียงกัน
            cols = st.columns(min(len(all_images), 3)) # จัดสูงสุด 3 คอลัมน์
            for idx, img in enumerate(all_images):
                with cols[idx % 3]:
                    st.image(img, caption=f"Img {idx+1}", use_column_width=True)
            
            # ปุ่ม Run
            if st.button("🚀 เริ่มตรวจสอบ (Analyze All)", type="primary"):
                with st.spinner(f"กำลังส่งข้อมูลให้ {active_model} วิเคราะห์..."):
                    
                    model = genai.GenerativeModel(active_model) # ใช้รุ่นที่ Auto-detect เจอ
                    
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
