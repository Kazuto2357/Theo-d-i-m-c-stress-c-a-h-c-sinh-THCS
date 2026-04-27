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
st.markdown("**Người bạn đồng hành sức khoẻ tâm lý đắc lực cho học sinh THCS & THPT Phú Quới**")

# ====================== CẤU HÌNH LỚP HỌC ======================
BLOCKS = ["6", "7", "8", "9"]
CLASSES = {block: [f"{block}A{i}" for i in range(1, 8)] for block in BLOCKS}

# ====================== LƯU DỮ LIỆU THEO LỚP ======================
DATA_FILE = Path("stress_data.json")

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data_dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=2)

if "data" not in st.session_state:
    st.session_state.data = load_data()

if "latest_ai_advice" not in st.session_state:
    st.session_state.latest_ai_advice = None

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("🔑 Cài đặt")
    
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
    # Hiển thị thông tin lớp hiện tại
    if "selected_role" in st.session_state and "selected_class" in st.session_state:
        st.info(f"**Vai trò:** {st.session_state.selected_role}\n**Lớp:** {st.session_state.selected_class}")
    
    if st.button("🔄 Đổi vai trò / Lớp", use_container_width=True):
        for key in ["selected_role", "selected_block", "selected_class"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.markdown("---")
    st.markdown("**Tác giả:** Trần Quốc Thông  \n**Trường:** THCS và THPT Phú Quới")
    st.caption("Dự án phần mềm theo dõi mức độ stress của học sinh THCS & THPT")

# ====================== CHỌN VAI TRÒ + KHỐI + LỚP (MÀN HÌNH ĐẦU) ======================
if "selected_role" not in st.session_state or "selected_class" not in st.session_state:
    st.subheader("🎯 Chào mừng bạn đến với AI StressGuard!")
    
    # Chọn vai trò
    role = st.radio("Bạn là:", ["🧑‍🎓 Học sinh", "👩‍🏫 Giáo viên chủ nhiệm"], horizontal=True, label_visibility="collapsed")
    selected_role = "Học sinh" if "Học sinh" in role else "Giáo viên chủ nhiệm"
    
    st.markdown("---")
    st.subheader("📚 Chọn khối học")
    col_block = st.columns(4)
    selected_block = None
    for i, block in enumerate(BLOCKS):
        with col_block[i]:
            if st.button(f"Khối {block}", use_container_width=True):
                selected_block = block
                st.session_state.selected_block = block
    
    if "selected_block" in st.session_state:
        selected_block = st.session_state.selected_block
        st.subheader(f"📋 Chọn lớp {selected_block}")
        cols = st.columns(4)
        for i, class_name in enumerate(CLASSES[selected_block]):
            with cols[i % 4]:
                if st.button(class_name, use_container_width=True):
                    st.session_state.selected_role = selected_role
                    st.session_state.selected_class = class_name
                    st.success(f"✅ Đã vào lớp **{class_name}**")
                    st.rerun()

    st.stop()  # Dừng lại cho đến khi chọn xong

# ====================== ĐÃ CHỌN XONG → VÀO APP CHÍNH ======================
current_class = st.session_state.selected_class
current_role = st.session_state.selected_role

# Lấy dữ liệu của lớp hiện tại
class_data = st.session_state.data.get(current_class, [])
st.session_state.data[current_class] = class_data  # Đảm bảo key tồn tại

st.caption(f"📍 Đang làm việc tại: **{current_class}** — Vai trò: **{current_role}**")

# ====================== TABS (động theo vai trò) ======================
tabs_list = ["📝 Nhật ký cá nhân", "📸 Phân tích ảnh mặt", "📊 Thống kê cá nhân", "💬 Chatbot AI"]
if current_role == "Giáo viên chủ nhiệm":
    tabs_list.append("📋 Báo cáo Lớp")

tab1, tab2, tab3, tab5, *tab4 = st.tabs(tabs_list) if current_role == "Giáo viên chủ nhiệm" else st.tabs(tabs_list)

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
                    class_data.append(entry)
                    st.session_state.data[current_class] = class_data
                    save_data(st.session_state.data)
                    st.session_state.latest_ai_advice = ai_advice
                    st.success("✅ Đã lưu và phân tích thành công!")
                except Exception as e:
                    st.error(f"❌ Lỗi AI: {e}")

    if st.session_state.latest_ai_advice:
        st.markdown("### 🤖 Phân tích từ AI:")
        st.write(st.session_state.latest_ai_advice)

# ==================== TAB 2: Phân tích ảnh mặt (đã cập nhật lưu vào lớp) ====================
with tab2:
    st.subheader("📸 Upload ảnh khuôn mặt")
    uploaded_file = st.file_uploader("Chọn ảnh selfie", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True)
        
        if st.button("🔍 Phân tích cảm xúc bằng AI", type="primary", use_container_width=True):
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

    # Phần lưu vào nhật ký (chung cho cả học sinh và giáo viên)
    if "image_analysis_result" in st.session_state:
        st.markdown("---")
        st.subheader("💾 Lưu phân tích vào Nhật ký cá nhân")
        col1, col2 = st.columns(2)
        with col1:
            mood_from_image = st.select_slider("Mức độ stress (0-10)", options=range(0, 11), value=5, key="mood_image")
        with col2:
            emotion_from_image = st.selectbox("Cảm xúc chính", 
                ["😊 Vui vẻ", "😐 Bình thường", "😟 Lo lắng", "😢 Buồn", "😡 Tức giận", "😴 Mệt mỏi", "🤯 Quá tải"],
                key="emotion_image")
        
        if st.button("💾 Lưu phân tích ảnh vào nhật ký", type="primary", use_container_width=True):
            entry = {
                "date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M"),
                "mood": mood_from_image,
                "emotion": emotion_from_image,
                "note": f"📸 Phân tích từ ảnh khuôn mặt:\n\n{st.session_state.image_analysis_result}",
                "ai_advice": st.session_state.image_analysis_result
            }
            class_data.append(entry)
            st.session_state.data[current_class] = class_data
            save_data(st.session_state.data)
            st.success("✅ Đã lưu phân tích ảnh vào nhật ký cá nhân!")
            del st.session_state.image_analysis_result
            st.rerun()

# ==================== TAB 3: Thống kê cá nhân ====================
with tab3:
    st.subheader("📊 Thống kê cá nhân")
    if class_data:
        df = pd.DataFrame(class_data)
        df['date'] = pd.to_datetime(df['date'])
        st.plotly_chart(px.line(df, x='date', y='mood', markers=True, title="Mức stress theo thời gian"), use_container_width=True)
        st.dataframe(df[['date', 'mood', 'emotion', 'note']], use_container_width=True)
        
        st.markdown("---")
        if st.button("🗑️ Xóa toàn bộ nhật ký cá nhân", type="secondary"):
            if st.checkbox("Tôi chắc chắn muốn xóa HẾT dữ liệu của lớp này (không thể khôi phục)"):
                st.session_state.data[current_class] = []
                save_data(st.session_state.data)
                st.success("✅ Đã xóa toàn bộ nhật ký của lớp!")
                st.rerun()
    else:
        st.info("Chưa có dữ liệu nhật ký.")

# ==================== TAB 4: Báo cáo Lớp (chỉ giáo viên) ====================
if current_role == "Giáo viên chủ nhiệm":
    with tab4[0]:
        st.subheader("📋 Báo cáo lớp học")
        if class_data:
            df = pd.DataFrame(class_data)
            st.metric("Stress trung bình lớp", f"{df['mood'].mean():.1f}/10")
            st.plotly_chart(px.histogram(df, x='mood', title="Phân bố mức stress"), use_container_width=True)
            st.dataframe(df[['date', 'mood', 'emotion']], use_container_width=True)
        else:
            st.info("Chưa có dữ liệu lớp nào.")

# ==================== TAB 5: Chatbot AI ====================
with (tab5 if current_role == "Học sinh" else tab4[-1] if current_role == "Giáo viên chủ nhiệm" else tab5):
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
                class_data.append(entry)
                st.session_state.data[current_class] = class_data
                save_data(st.session_state.data)
                st.success("✅ Đã lưu cuộc trò chuyện vào nhật ký!")

st.caption("AI StressGuard Student • Tác giả: Trần Quốc Thông • Trường THCS & THPT Phú Quới • 2026")
