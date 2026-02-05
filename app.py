import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="AI Pharma QC (Easy Mode)", page_icon="💊")
st.title("🏥 AI Pharma QC: ระบบตรวจ COA (แบบง่าย)")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ ตั้งค่า")
    api_key = st.text_input("ใส่ Gemini API Key", type="password")
    
    # ตรงนี้ให้ใส่ลิ้งค์ Google Sheet ธรรมดาได้เลย
    sheet_url = st.text_input("แปะลิ้งค์ Google Sheet (Database)", 
                              help="ต้องเปิด Share เป็น 'Anyone with the link' ก่อนนะ")

# --- ฟังก์ชันโหลดข้อมูลแบบไม่ต้องใช้กุญแจ ---
@st.cache_data
def load_data(url):
    try:
        # แปลงลิ้งค์ Google Sheet ธรรมดา ให้เป็นลิ้งค์ดาวน์โหลด CSV
        csv_url = url.replace('/edit?usp=sharing', '/export?format=csv').replace('/edit', '/export?format=csv')
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        return None

# --- MAIN APP ---
if api_key and sheet_url:
    genai.configure(api_key=api_key)
    
    df = load_data(sheet_url)
    
    if df is not None:
        st.success(f"✅ เชื่อมต่อ Database สำเร็จ! (พบยา {len(df)} รายการ)")
        
        # เตรียมข้อมูล
        db_context = ""
        for index, row in df.iterrows():
            # สมมติ Column 1 คือชื่อยา, Column 2 คือ Spec
            # (ต้องแน่ใจว่าใน Excel เรียงตามนี้ หรือแก้ index เอา)
            db_context += f"Drug: {row[1]} | Spec: {row[2]}\n"
            
        # ส่วนอัปโหลดรูป
        st.header("📸 ตรวจสอบ COA")
        uploaded_img = st.file_uploader("เลือกรูปใบ COA", type=["jpg", "png"])
        
        if uploaded_img:
            image = Image.open(uploaded_img)
            st.image(image, caption="COA Preview", width=300)
            
            if st.button("🚀 ตรวจสอบทันที"):
                with st.spinner("AI กำลังทำงาน..."):
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"""
                    Role: QC Pharmacist.
                    Database Specs: {db_context}
                    Task: Identify Drug Name, Find Spec, Compare Result.
                    Rules: Strict Range Check, NMT/NLT Logic, Ph.Eur Color Logic.
                    Output: Markdown Table with Pass/Fail.
                    """
                    try:
                        response = model.generate_content([prompt, image])
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.error("❌ อ่าน Google Sheet ไม่ได้ (อย่าลืมเปิด Share เป็น Public นะครับ)")
else:
    st.info("👈 กรอกข้อมูลด้านซ้ายให้ครบก่อนครับ")
