import streamlit as st
import google.generativeai as genai
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import json
from pathlib import Path
from PIL import Image

st.set_page_config(page_title="AI Theo Dõi Mức Độ Căng Thẳng", page_icon="🧠", layout="wide")
st.title("🧠 AI Theo Dõi Mức Độ Căng Thẳng")
st.markdown("**Người bạn đồng hành sức khoẻ tâm lý đắc lực cho học sinh THCS**")

# ====================== SIDEBAR ======================
# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("🔑 Cài đặt")
    
    # ==================== NÚT LINK API KEY ====================
    st.link_button(
        label="🌐 Lấy Gemini API Key miễn phí",
        url="https://aistudio.google.com/",
        use_container_width=True
    )
    st.caption("Nhấn nút trên để truy cập **Google AI Studio** và tạo API key ngay (miễn phí)")

    api_key = st.text_input("Gemini API Key", type="password", value="")
    model_name = st.selectbox("Chọn mô hình AI", 
                             ["gemini-3.1-flash-lite-preview", "gemini-2.5-flash-lite"], 
                             index=0)
    if api_key:
        genai.configure(api_key=api_key)
        st.success(f"✅ Đã kết nối {model_name}")
    
    st.markdown("---")
    st.markdown("**Tác giả:** Trần Quốc Thông  \n**Trường:** THCS và THPT Phú Quới")
    st.caption("Dự án phần mềm theo dõi mức độ stress của học sinh THCS")

# ====================== LƯU DỮ LIỆU ======================
DATA_FILE = Path("stress_data.json")

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(data_list):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)

if "data" not in st.session_state:
    st.session_state.data = load_data()

if "latest_ai_advice" not in st.session_state:
    st.session_state.latest_ai_advice = None

# ====================== TABS ======================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Nhật ký cá nhân", 
    "📸 Phân tích ảnh mặt", 
    "📊 Thống kê cá nhân", 
    "📋 Báo cáo Lớp (Giáo viên)", 
    "💬 Chatbot AI"
])

# ==================== TAB 1: Nhật ký cá nhân ====================
with tab1:
    st.subheader("Hôm nay bạn cảm thấy thế nào?")
    col1, col2 = st.columns(2)
    with col1:
        mood = st.select_slider("Mức độ stress (0-10)", options=range(0, 11), value=5)
    with col2:
        emotion = st.selectbox("Cảm xúc chính", 
            ["😊 Vui vẻ", "😐 Bình thường", "😟 Lo lắng", "😢 Buồn", "😡 Tức giận", "😴 Mệt mỏi", "🤯 Quá tải"])
    note = st.text_area("Viết vài dòng về hôm nay...", height=150)
    
    if st.button("💾 Lưu nhật ký & Phân tích AI", type="primary", use_container_width=True):
        if not api_key:
            st.error("❌ Vui lòng nhập Gemini API Key ở sidebar!")
        else:
            with st.spinner("AI đang phân tích..."):
                try:
                    model = genai.GenerativeModel(model_name)
                    prompt = f"""Bạn là chuyên gia tâm lý dành cho học sinh THCS và THPT Việt Nam. 
Phân tích mức stress {mood}/10, cảm xúc {emotion}, nhật ký: {note}. 
Đưa lời khuyên ngắn gọn, tích cực, dễ thực hiện bằng tiếng Việt."""
                    response = model.generate_content(prompt)
                    ai_advice = response.text.strip()
                    
                    entry = {
                        "date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M"),
                        "mood": mood, "emotion": emotion, "note": note, "ai_advice": ai_advice
                    }
                    st.session_state.data.append(entry)
                    save_data(st.session_state.data)
                    st.session_state.latest_ai_advice = ai_advice
                    st.success("✅ Đã lưu và phân tích thành công!")
                except Exception as e:
                    st.error(f"❌ Lỗi AI: {e}")

    if st.session_state.latest_ai_advice:
        st.markdown("### 🤖 Phân tích từ AI:")
        st.write(st.session_state.latest_ai_advice)

# ==================== TAB 2: Phân tích ảnh mặt ====================
with tab2:
    st.subheader("📸 Upload ảnh khuôn mặt")
    uploaded_file = st.file_uploader("Chọn ảnh selfie", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True)
        
        if st.button("🔍 Phân tích cảm xúc bằng AI"):
            if not api_key:
                st.error("❌ Vui lòng nhập API Key!")
            else:
                with st.spinner("AI đang phân tích..."):
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content([
                            "Phân tích cảm xúc khuôn mặt của học sinh THCS và THPT, đưa lời khuyên ngắn gọn bằng tiếng Việt.",
                            image
                        ])
                        analysis_result = response.text.strip()
                        
                        st.session_state.image_analysis_result = analysis_result
                        st.success("✅ Phân tích hoàn tất!")
                        st.markdown("### 📊 Kết quả phân tích cảm xúc:")
                        st.write(analysis_result)
                    except Exception as e:
                        st.error(f"❌ Lỗi khi phân tích ảnh: {e}")

    # ==================== PHẦN LƯU VÀO NHẬT KÝ (mới thêm) ====================
    if "image_analysis_result" in st.session_state:
        st.markdown("---")
        st.subheader("💾 Lưu phân tích vào Nhật ký cá nhân")
        
        col1, col2 = st.columns(2)
        with col1:
            mood_from_image = st.select_slider(
                "Mức độ stress (0-10)", 
                options=range(0, 11), 
                value=5,
                key="mood_image"
            )
        with col2:
            emotion_from_image = st.selectbox(
                "Cảm xúc chính", 
                ["😊 Vui vẻ", "😐 Bình thường", "😟 Lo lắng", "😢 Buồn", "😡 Tức giận", "😴 Mệt mỏi", "🤯 Quá tải"],
                key="emotion_image"
            )
        
        if st.button("💾 Lưu phân tích ảnh vào nhật ký", type="primary", use_container_width=True):
            entry = {
                "date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M"),
                "mood": mood_from_image,
                "emotion": emotion_from_image,
                "note": f"📸 Phân tích từ ảnh khuôn mặt:\n\n{st.session_state.image_analysis_result}",
                "ai_advice": st.session_state.image_analysis_result
            }
            st.session_state.data.append(entry)
            save_data(st.session_state.data)
            st.success("✅ Đã lưu phân tích ảnh vào nhật ký cá nhân! Bạn có thể xem trong Tab 3 - Thống kê cá nhân.")
            
            # Xóa kết quả tạm
            if "image_analysis_result" in st.session_state:
                del st.session_state.image_analysis_result
            st.rerun()
# ==================== TAB 3: Thống kê cá nhân (có nút xóa) ====================
with tab3:
    st.subheader("📊 Thống kê cá nhân")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        df['date'] = pd.to_datetime(df['date'])
        st.plotly_chart(px.line(df, x='date', y='mood', markers=True, title="Mức stress theo thời gian"), use_container_width=True)
        st.dataframe(df[['date', 'mood', 'emotion', 'note']], use_container_width=True)
        
        st.markdown("---")
        if st.button("🗑️ Xóa toàn bộ nhật ký cá nhân", type="secondary"):
            if st.checkbox("Tôi chắc chắn muốn xóa HẾT dữ liệu (không thể khôi phục)"):
                st.session_state.data = []
                save_data([])
                if DATA_FILE.exists():
                    DATA_FILE.unlink()
                st.success("✅ Đã xóa toàn bộ nhật ký!")
                st.rerun()
    else:
        st.info("Chưa có dữ liệu nhật ký.")

# ==================== TAB 4: Báo cáo Lớp ====================
with tab4:
    st.subheader("📋 Báo cáo lớp học (Giáo viên)")
    password = st.text_input("Nhập mật khẩu giáo viên", type="password")
    if password == "giao_vien_2026":
        if st.session_state.data:
            df = pd.DataFrame(st.session_state.data)
            st.metric("Stress trung bình lớp", f"{df['mood'].mean():.1f}/10")
            st.plotly_chart(px.histogram(df, x='mood', title="Phân bố mức stress"), use_container_width=True)
            st.dataframe(df[['date', 'mood', 'emotion']], use_container_width=True)
        else:
            st.info("Chưa có dữ liệu lớp nào.")
    else:
        if password:
            st.error("Mật khẩu sai!")

# ==================== TAB 5: Chatbot AI 24/7 ====================
with tab5:
    st.subheader("💬 Chatbot AI trò chuyện trực tiếp 24/7")
    st.caption("⏰ Giờ Việt Nam (UTC+7)")
    chat_style = st.selectbox("Phong cách trò chuyện", ["Thân thiện ❤️", "Chuyên nghiệp 📋", "Cân bằng ⚖️"])
    
    if "messages" not in st.session_state:
        vn_time = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M")
        st.session_state.messages = [{"role": "assistant", "content": "Chào bạn! Mình là AI StressGuard. Hôm nay bạn muốn chia sẻ gì? ❤️", "timestamp": vn_time}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(f"**{msg.get('timestamp', '')}** — {msg['content']}")

    if prompt := st.chat_input("Nhập tin nhắn của bạn..."):
        vn_time = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M")
        st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": vn_time})
        with st.chat_message("user"):
            st.markdown(f"**{vn_time}** — {prompt}")

        with st.chat_message("assistant"):
            with st.spinner("AI đang suy nghĩ..."):
                model = genai.GenerativeModel(model_name)
                style_prompt = {
                    "Thân thiện ❤️": "Bạn là người bạn rất thân thiện, ấm áp, hay dùng emoji.",
                    "Chuyên nghiệp 📋": "Bạn là chuyên gia tâm lý chuyên nghiệp, trả lời logic và rõ ràng.",
                    "Cân bằng ⚖️": "Bạn vừa thân thiện vừa chuyên nghiệp."
                }[chat_style]
                
                full_prompt = style_prompt + "\n\nLịch sử:\n" + "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                response = model.generate_content(full_prompt)
                ai_reply = response.text
                st.markdown(f"**{vn_time}** — {ai_reply}")
                st.session_state.messages.append({"role": "assistant", "content": ai_reply, "timestamp": vn_time})

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
            vn_time = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M")
            st.session_state.messages = [{"role": "assistant", "content": "Đã xóa lịch sử. Chúng ta bắt đầu lại nhé!", "timestamp": vn_time}]
            st.rerun()
    with col2:
        if st.button("💾 Lưu cuộc trò chuyện vào nhật ký", use_container_width=True):
            if len(st.session_state.messages) > 1:
                chat_text = "\n".join([f"{m['timestamp']} {m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
                entry = {"date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M"), 
                         "mood": 5, "emotion": "Từ chatbot", "note": chat_text, "ai_advice": "Đã lưu từ chatbot"}
                st.session_state.data.append(entry)
                save_data(st.session_state.data)
                st.success("✅ Đã lưu cuộc trò chuyện vào nhật ký!")

st.caption("AI StressGuard Student • Tác giả: Trần Quốc Thông • Trường THCS & THPT Phú Quới • 2026")
