import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from PIL import Image
import json

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="AI Pharma QC", page_icon="💊", layout="wide")

st.title("🏥 AI Pharma QC: ระบบตรวจสอบ COA อัจฉริยะ")
st.markdown("---")

# --- SIDEBAR: การตั้งค่า ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าระบบ")
    api_key = st.text_input("1. ใส่ Gemini API Key", type="password")
    
    st.write("2. อัปโหลดไฟล์กุญแจ (JSON Key) ของ Google Sheet")
    creds_file = st.file_uploader("เลือกไฟล์ .json", type=["json"])
    
    st.info("💡 หมายเหตุ: ระบบไม่ได้บันทึกกุญแจของคุณ ปลอดภัย 100%")

# --- MAIN APP ---
if api_key and creds_file:
    # 1. Setup AI
    genai.configure(api_key=api_key)
    
    # 2. Setup Database
    try:
        # อ่านไฟล์ JSON ที่อัปโหลดมา
        creds_dict = json.load(creds_file)
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(creds)
        
        # เชื่อมต่อ Sheet (แก้ชื่อ Sheet ตรงนี้ถ้าชื่อเปลี่ยน)
        SHEET_NAME = 'MasterDrugDB' 
        worksheet = gc.open(SHEET_NAME).sheet1
        rows = worksheet.get_all_values()
        df = pd.DataFrame(rows[1:], columns=rows[0])
        
        st.success(f"✅ เชื่อมต่อ Database สำเร็จ! (พบยา {len(df)} รายการ)")
        
        # เตรียมข้อมูลให้ AI
        db_context = ""
        for index, row in df.iterrows():
            db_context += f"Drug: {row[1]} | Spec: {row[2]}\n"

        # 3. ส่วนอัปโหลดและตรวจ QC
        st.header("📸 ตรวจสอบใบ COA")
        uploaded_img = st.file_uploader("อัปโหลดรูปภาพ COA", type=["jpg", "png", "jpeg"])
        
        if uploaded_img:
            image = Image.open(uploaded_img)
            col1, col2 = st.columns(2)
            with col1:
                st.image(image, caption="รูปที่อัปโหลด", use_column_width=True)
            
            with col2:
                if st.button("🚀 เริ่มตรวจสอบ (Start Analyze)", type="primary"):
                    with st.spinner("🤖 AI กำลังอ่านค่าและตรวจสอบกฎ..."):
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        prompt = f"""
                        Role: Expert QC Pharmacist.
                        Input DB: {db_context}
                        Task: 
                        1. Identify Drug Name from image.
                        2. Find matching Spec in DB.
                        3. Compare Result vs Spec using Pharma Logic (Ranges, Limits, Ph.Eur Color).
                        
                        Output format: Markdown Table.
                        """
                        
                        try:
                            response = model.generate_content([prompt, image])
                            st.markdown(response.text)
                            if "PASS" in response.text:
                                st.balloons()
                        except Exception as e:
                            st.error(f"Error: {e}")

    except Exception as e:
        st.error(f"❌ เชื่อมต่อ Google Sheet ไม่ได้: {e}")
        st.warning("ตรวจสอบชื่อไฟล์ JSON หรือชื่อ Sheet ว่าถูกต้องตรงกันหรือไม่")

else:
    st.info("👈 กรุณากรอกข้อมูลในแถบซ้ายมือให้ครบเพื่อเริ่มใช้งาน")
