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

# ====================== PHẦN MỚI: KẾT NỐI SUPABASE ======================
from supabase import create_client, Client

# ====================== KẾT NỐI SUPABASE (CÁCH MỚI - ỔN ĐỊNH) ======================
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["SUPABASE_URL"]
    key = st.secrets["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = get_supabase_client()

if "user" not in st.session_state:
    st.session_state.user = None

# ====================== AUTHENTICATION ======================
if st.session_state.user is None:
    st.title("🧠 AI Theo Dõi Mức Độ Căng Thẳng")
    st.markdown("**Đăng nhập để tiếp tục**")

    tab1, tab2 = st.tabs(["🔑 Đăng nhập", "📝 Đăng ký"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mật khẩu", type="password", key="login_pass")
        if st.button("Đăng nhập", type="primary", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success(f"Chào mừng {res.user.email}!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi đăng nhập: {e}")

    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Mật khẩu (ít nhất 6 ký tự)", type="password", key="signup_pass")
        if st.button("Đăng ký", type="primary", use_container_width=True):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Đăng ký thành công! Kiểm tra email để xác thực.")
            except Exception as e:
                st.error(f"Lỗi đăng ký: {e}")
    st.stop()

# ====================== SAU KHI ĐĂNG NHẬP ======================
st.success(f"👋 Xin chào {st.session_state.user.email}!")

# ====================== LẤY USER_ID ======================
user_id = st.session_state.user.id

# ====================== KHỞI TẠO SESSION_STATE ======================
if "latest_ai_advice" not in st.session_state:
    st.session_state.latest_ai_advice = None
if "image_analysis_result" not in st.session_state:
    st.session_state.image_analysis_result = None
if "messages" not in st.session_state:
    st.session_state.messages = None
if "class_data" not in st.session_state:
    st.session_state.class_data = []

# ====================== LƯU DỮ LIỆU VÀO SUPABASE ======================
def load_user_data():
    try:
        response = supabase.table("user_data").select("*").eq("user_id", user_id).execute()
        if response.data and response.data and response.data[0].get("content"):
            return json.loads(response.data[0]["content"])
        return []
    except:
        return []

def save_user_data(entries):
    try:
        data_to_save = json.dumps(entries)
        supabase.table("user_data").delete().eq("user_id", user_id).execute()
        supabase.table("user_data").insert({
            "user_id": user_id,
            "content": data_to_save
        }).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi lưu Supabase: {e}")
        return False

# Load dữ liệu cho user hiện tại
if "class_data" not in st.session_state or st.session_state.class_data is None:
    st.session_state.class_data = load_user_data()

class_data = st.session_state.class_data

# ====================== Code APP Chính ======================
st.title("🧠 AI Theo Dõi Mức Độ Căng Thẳng")
st.markdown("**Người bạn đồng hành sức khoẻ tâm lý đắc lực cho học sinh THCS & THPT Phú Quới**")

# ====================== CẤU HÌNH LỚP HỌC ======================
BLOCKS = ["6", "7", "8", "9"]
CLASSES = {block: [f"{block}A{i}" for i in range(1, 8)] for block in BLOCKS}

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("🔑 Cài đặt")
    st.link_button(label="🌐 Lấy Gemini API Key miễn phí", url="https://aistudio.google.com/", use_container_width=True)
    api_key = st.text_input("Gemini API Key", type="password", value="")
    model_name = "gemini-2.5-flash-lite"
    if api_key:
        genai.configure(api_key=api_key)
        st.success(f"✅ Đã kết nối {model_name}")

    st.markdown("---")
    if "selected_role" in st.session_state and "selected_class" in st.session_state:
        st.info(f"**Vai trò:** {st.session_state.selected_role}\n**Lớp:** {st.session_state.selected_class}")
    
    if st.button("🔄 Đổi vai trò / Lớp", use_container_width=True):
        for key in ["selected_role", "selected_block", "selected_class", "messages"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.markdown("---")
    st.markdown("**Tác giả:** Trần Quốc Thông  \n**Trường:** THCS và THPT Phú Quới")
    st.caption("Dự án phần mềm theo dõi mức độ stress của học sinh THCS & THPT")

# ====================== CHỌN VAI TRÒ + KHỐI + LỚP ======================
if "selected_role" not in st.session_state or "selected_class" not in st.session_state:
    # (giữ nguyên toàn bộ phần này của bạn)
    st.subheader("🎯 Chào mừng bạn đến với AI StressGuard!")
    role = st.radio("Bạn là:", ["🧑‍🎓 Học sinh", "👩‍🏫 Giáo viên chủ nhiệm"], horizontal=True)
    selected_role = "Học sinh" if "Học sinh" in role else "Giáo viên chủ nhiệm"
    
    st.markdown("---")
    st.subheader("📚 Chọn khối học")
    col_block = st.columns(4)
    for i, block in enumerate(BLOCKS):
        with col_block[i]:
            if st.button(f"Khối {block}", use_container_width=True):
                st.session_state.selected_block = block
                st.rerun()
    
    if "selected_block" in st.session_state:
        block = st.session_state.selected_block
        st.subheader(f"📋 Chọn lớp {block}")
        cols = st.columns(4)
        for i, class_name in enumerate(CLASSES[block]):
            with cols[i % 4]:
                if st.button(class_name, use_container_width=True):
                    st.session_state.selected_role = selected_role
                    st.session_state.selected_class = class_name
                    st.success(f"✅ Đã vào lớp **{class_name}**")
                    st.rerun()
    st.stop()

# ====================== APP CHÍNH ======================
current_class = st.session_state.selected_class
current_role = st.session_state.selected_role

st.caption(f"📍 Đang làm việc tại: **{current_class}** — Vai trò: **{current_role}**")

# ====================== TABS ======================
tabs_list = ["📝 Nhật ký cá nhân", "📸 Phân tích ảnh mặt", "📊 Thống kê cá nhân"]
if current_role == "Giáo viên chủ nhiệm":
    tabs_list.append("📋 Báo cáo Lớp")
tabs_list.append("💬 Chatbot AI")

tabs = st.tabs(tabs_list)

# ==================== TAB 1: Nhật ký cá nhân ====================
with tabs[0]:
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
                    st.session_state.class_data = class_data
                    save_user_data(class_data)
                    st.session_state.latest_ai_advice = ai_advice
                    st.success("✅ Đã lưu và phân tích thành công!")
                except Exception as e:
                    st.error(f"❌ Lỗi AI: {e}")

    # Kiểm tra an toàn trước khi hiển thị
    if st.session_state.get("latest_ai_advice"):
        st.markdown("### 🤖 Phân tích từ AI:")
        st.write(st.session_state.latest_ai_advice)
# ==================== TAB 2: Phân tích ảnh mặt ====================
with tabs[1]:
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
            st.session_state.class_data = class_data
            save_user_data(class_data)
            st.success("✅ Đã lưu vào nhật ký!")
            del st.session_state.image_analysis_result
            st.rerun()

# ==================== TAB 3: Thống kê cá nhân ====================
with tabs[2]:
    st.subheader("📊 Thống kê cá nhân")
    if class_data:
        df = pd.DataFrame(class_data)
        df['date'] = pd.to_datetime(df['date'])
        st.plotly_chart(px.line(df, x='date', y='mood', markers=True, title="Mức stress theo thời gian"), use_container_width=True)
        st.dataframe(df[['date', 'mood', 'emotion', 'note']], use_container_width=True)
        
        st.markdown("---")
        if st.button("🗑️ Xóa toàn bộ nhật ký cá nhân", type="secondary"):
            if st.checkbox("Tôi chắc chắn muốn xóa HẾT dữ liệu của lớp này (không thể khôi phục)"):
                st.session_state.class_data = []
                save_user_data(class_data)
                st.success("✅ Đã xóa toàn bộ nhật ký!")
                st.rerun()
    else:
        st.info("Chưa có dữ liệu.")

# ==================== TAB 4: Báo cáo Lớp (chỉ giáo viên) ====================
if current_role == "Giáo viên chủ nhiệm":
    with tabs[3]:
        st.subheader("📋 Báo cáo lớp học")
        if class_data:
            df = pd.DataFrame(class_data)
            st.metric("Stress trung bình lớp", f"{df['mood'].mean():.1f}/10" if len(df) > 0 else "0.0/10")
            st.plotly_chart(px.histogram(df, x='mood', title="Phân bố mức stress"), use_container_width=True)
            st.dataframe(df[['date', 'mood', 'emotion']], use_container_width=True)
        else:
            st.info("Chưa có dữ liệu lớp nào.")

# ==================== TAB 5: Chatbot AI ====================
chat_index = 4 if current_role == "Giáo viên chủ nhiệm" else 3
with tabs[chat_index]:
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
                style_prompt = {"Thân thiện ❤️": "Bạn là người bạn rất thân thiện, ấm áp, hay dùng emoji.",
                                "Chuyên nghiệp 📋": "Bạn là chuyên gia tâm lý chuyên nghiệp, trả lời logic và rõ ràng.",
                                "Cân bằng ⚖️": "Bạn vừa thân thiện vừa chuyên nghiệp."}[chat_style]
                full_prompt = style_prompt + "\n\nLịch sử:\n" + "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                response = model.generate_content(full_prompt)
                ai_reply = response.text
                st.markdown(f"**{vn_time}** — {ai_reply}")
                st.session_state.messages.append({"role": "assistant", "content": ai_reply, "timestamp": vn_time})

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
            st.session_state.messages = [{"role": "assistant", "content": "Đã xóa lịch sử. Chúng ta bắt đầu lại nhé!", "timestamp": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M")}]
            st.rerun()
    with col2:
        if st.button("💾 Lưu cuộc trò chuyện vào nhật ký", use_container_width=True):
            if len(st.session_state.messages) > 1:
                chat_text = "\n".join([f"{m['timestamp']} {m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
                entry = {"date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y-%m-%d %H:%M"), 
                         "mood": 5, "emotion": "Từ chatbot", "note": chat_text, "ai_advice": "Đã lưu từ chatbot"}
                class_data.append(entry)
                st.session_state.class_data = class_data
                save_user_data(class_data)
                st.success("✅ Đã lưu vào nhật ký!")

st.caption("AI StressGuard • Tác giả: Trần Quốc Thông • Trường THCS & THPT Phú Quới • 2026")