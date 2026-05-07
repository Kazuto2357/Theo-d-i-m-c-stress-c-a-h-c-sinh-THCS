import streamlit as st
import google.generativeai as genai
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import json
from supabase import create_client, Client
from PIL import Image

st.set_page_config(page_title="AI Theo Dõi Mức Độ Căng Thẳng", page_icon="🧠", layout="wide")

# ====================== KẾT NỐI SUPABASE ======================
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

user_id = st.session_state.user.id

# ====================== XỬ LÝ PROFILE (TẠO MỚI + SỬA) ======================
def load_profile():
    response = supabase.table("profiles").select("*").eq("id", user_id).execute()
    return response.data[0] if response.data else None

# Luôn load profile mới nhất mỗi lần rerun
if "profile" not in st.session_state or st.session_state.get("refresh_profile", False):
    st.session_state.profile = load_profile()
    if "refresh_profile" in st.session_state:
        del st.session_state.refresh_profile

profile = st.session_state.profile

# Hiển thị form tạo mới hoặc sửa
if profile is None or st.session_state.get("edit_profile", False):
    mode = "Sửa thông tin cá nhân" if profile else "Nhập thông tin cá nhân lần đầu"
    st.subheader(f"👤 {mode}")

    full_name = st.text_input("Họ và tên đầy đủ", 
                              value=profile.get("full_name", "") if profile else "")
    
    # Xử lý ngày sinh an toàn
    if profile and profile.get("birth_date"):
        try:
            default_date = datetime.fromisoformat(str(profile["birth_date"]).replace("Z", "+00:00")).date()
        except:
            default_date = datetime(2012, 1, 1).date()
    else:
        default_date = datetime(2012, 1, 1).date()
    
    birth_date = st.date_input("Ngày sinh", value=default_date)
    
    class_name = st.text_input("Lớp của bạn", 
                               value=profile.get("class_name", "") if profile else "", 
                               placeholder="Ví dụ: 6A1, 7B3...")
    
    role_options = ["Học sinh", "Giáo viên chủ nhiệm"]
    current_index = role_options.index(profile.get("role")) if profile and profile.get("role") in role_options else 0
    role = st.radio("Vai trò", role_options, index=current_index)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Lưu thông tin", type="primary", use_container_width=True):
            if not full_name.strip() or not class_name.strip():
                st.error("❌ Vui lòng nhập đầy đủ Họ tên và Lớp!")
            else:
                data = {
                    "id": user_id,
                    "full_name": full_name.strip(),
                    "birth_date": str(birth_date),
                    "class_name": class_name.strip().upper(),
                    "role": role
                }
                try:
                    if profile is None:
                        supabase.table("profiles").insert(data).execute()
                        st.success("✅ Thông tin đã được tạo thành công!")
                    else:
                        supabase.table("profiles").update(data).eq("id", user_id).execute()
                        st.success("✅ Thông tin đã được cập nhật!")
                    
                    # Reload profile mới nhất
                    st.session_state.profile = load_profile()
                    if "edit_profile" in st.session_state:
                        del st.session_state.edit_profile
                    st.session_state.refresh_profile = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

    with col2:
        if st.button("❌ Hủy", use_container_width=True):
            if "edit_profile" in st.session_state:
                del st.session_state.edit_profile
            st.rerun()
    
    st.stop()

# ====================== KHỞI TẠO SESSION_STATE ======================
if "latest_ai_advice" not in st.session_state:
    st.session_state.latest_ai_advice = None
if "image_analysis_result" not in st.session_state:
    st.session_state.image_analysis_result = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ====================== LƯU DỮ LIỆU NHẬT KÝ ======================
def load_user_data():
    try:
        response = supabase.table("journal_entries").select("*").eq("user_id", user_id).execute()
        return response.data if response.data else []
    except:
        return []

def save_user_data(entry):
    try:
        supabase.table("journal_entries").insert(entry).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi lưu Supabase: {e}")
        return False

if "class_data" not in st.session_state:
    st.session_state.class_data = load_user_data()

class_data = st.session_state.class_data

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("👤 Thông tin cá nhân")
    st.write(f"**Họ tên:** {profile['full_name']}")
    st.write(f"**Lớp:** {profile['class_name']}")
    st.write(f"**Vai trò:** {profile['role']}")
    
    if st.button("🔄 Sửa thông tin cá nhân", use_container_width=True):
        # Cho phép sửa profile
        st.session_state.edit_profile = True
        st.rerun()
    
    st.markdown("---")
    api_key = st.text_input("Gemini API Key", type="password", value="")
    model_name = "gemini-2.5-flash-lite"
    if api_key:
        genai.configure(api_key=api_key)
        st.success(f"✅ Đã kết nối {model_name}")

    st.markdown("---")
    st.markdown("**Tác giả:** Trần Quốc Thông  \n**Trường:** THCS và THPT Phú Quới")
    st.caption("Dự án theo dõi mức độ stress")

# ====================== APP CHÍNH ======================
current_class = profile["class_name"]
current_role = profile["role"]

st.caption(f"📍 Lớp: **{current_class}** — Vai trò: **{current_role}**")

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
                        "user_id": user_id,
                        "class_name": current_class,
                        "date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
                        "mood": mood,
                        "emotion": emotion,
                        "note": note,
                        "ai_advice": ai_advice
                    }
                    if save_user_data(entry):
                        st.session_state.class_data = load_user_data()
                        st.session_state.latest_ai_advice = ai_advice
                        st.success("✅ Đã lưu và phân tích thành công!")
                except Exception as e:
                    st.error(f"❌ Lỗi AI: {e}")

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
                "user_id": user_id,
                "class_name": current_class,
                "date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
                "mood": mood_from_image,
                "emotion": emotion_from_image,
                "note": f"📸 Phân tích từ ảnh khuôn mặt:\n\n{st.session_state.image_analysis_result}",
                "ai_advice": st.session_state.image_analysis_result
            }
            if save_user_data(entry):
                st.session_state.class_data = load_user_data()
                st.success("✅ Đã lưu vào nhật ký!")
                del st.session_state.image_analysis_result
                st.rerun()

# ==================== TAB 3: Thống kê cá nhân ====================
with tabs[2]:
    st.subheader("📊 Thống kê cá nhân")
    if class_data:
        df = pd.DataFrame(class_data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            st.plotly_chart(px.line(df, x='date', y='mood', markers=True, title="Mức stress theo thời gian"), use_container_width=True)
            st.dataframe(df[['date', 'mood', 'emotion', 'note']], use_container_width=True)
        
        st.markdown("---")
        if st.button("🗑️ Xóa toàn bộ nhật ký cá nhân", type="secondary"):
            if st.checkbox("Tôi chắc chắn muốn xóa HẾT dữ liệu của mình (không thể khôi phục)"):
                supabase.table("journal_entries").delete().eq("user_id", user_id).execute()
                st.session_state.class_data = []
                st.success("✅ Đã xóa toàn bộ nhật ký!")
                st.rerun()
    else:
        st.info("Chưa có dữ liệu.")

# ==================== TAB 4: Báo cáo Lớp (chỉ giáo viên) ====================
if current_role == "Giáo viên chủ nhiệm":
    with tabs[3]:
        st.subheader(f"📋 Báo cáo lớp {current_class} - Chi tiết đầy đủ")

        try:
            response = supabase.table("journal_entries") \
                .select("""
                    *,
                    profiles(full_name, birth_date)
                """) \
                .eq("class_name", current_class) \
                .order("date", desc=True) \
                .execute()

            if response.data:
                # Flatten dữ liệu nested từ Supabase
                data_list = []
                for row in response.data:
                    flat = row.copy()
                    profiles_data = flat.pop("profiles", {}) or {}
                    flat["full_name"] = profiles_data.get("full_name", "Không rõ tên")
                    flat["birth_date"] = profiles_data.get("birth_date")
                    data_list.append(flat)

                df = pd.DataFrame(data_list)

                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df['Ngày sinh'] = pd.to_datetime(df['birth_date'], errors='coerce').dt.strftime('%d/%m/%Y')
                    df['Ngày ghi'] = df['date'].dt.strftime('%d/%m/%Y %H:%M')

                    # Các cột hiển thị
                    display_cols = ['full_name', 'Ngày sinh', 'Ngày ghi', 'mood', 'emotion', 'note', 'ai_advice']
                    rename_cols = {
                        'full_name': 'Họ và tên',
                        'mood': 'Mức stress',
                        'emotion': 'Cảm xúc',
                        'note': 'Mô tả / Nhật ký',
                        'ai_advice': 'Phân tích từ AI'
                    }

                    df_display = df[display_cols].rename(columns=rename_cols)

                    st.metric("Stress trung bình lớp", f"{df['mood'].mean():.1f}/10" if len(df) > 0 else "0.0/10")

                    st.plotly_chart(
                        px.histogram(df, x='mood', title="Phân bố mức stress của lớp"), 
                        use_container_width=True
                    )

                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Mức stress": st.column_config.NumberColumn(format="%d/10"),
                            "Mô tả / Nhật ký": st.column_config.TextColumn(width="medium"),
                            "Phân tích từ AI": st.column_config.TextColumn(width="medium")
                        }
                    )

                    # Nút tải file
                    csv = df_display.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Tải báo cáo Excel/CSV",
                        data=csv,
                        file_name=f"Bao_cao_lop_{current_class}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Chưa có dữ liệu nào trong lớp này.")
            else:
                st.info("Chưa có dữ liệu lớp nào.")
        except Exception as e:
            st.error(f"Lỗi khi tải báo cáo: {e}")

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
                entry = {
                    "user_id": user_id,
                    "class_name": current_class,
                    "date": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
                    "mood": 5,
                    "emotion": "Từ chatbot",
                    "note": chat_text,
                    "ai_advice": "Đã lưu từ chatbot"
                }
                if save_user_data(entry):
                    st.session_state.class_data = load_user_data()
                    st.success("✅ Đã lưu vào nhật ký!")
st.caption("AI StressGuard • Tác giả: Trần Quốc Thông • Trường THCS & THPT Phú Quới • 2026")
