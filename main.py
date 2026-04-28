import streamlit as st
import random
import os
import time
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip
import shutil
st.set_page_config(page_title="AI Video Bulk Composer", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
div[data-testid="column"]:last-child {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    padding-top: 5px;
}
button[kind="secondary"] {
    color: #ff4b4b !important;
    border: 1px solid #ff4b4b !important;
    padding: 1px 8px !important;
    font-size: 14px !important;
    min-height: 1.6rem !important;
}
</style>
""", unsafe_allow_html=True)
if 'final_files' not in st.session_state:
    st.session_state.final_files = []
def cleanup_folders():
    """Xóa và khởi tạo lại các thư mục tạm"""
    for folder in ["temp", "exports"]:
        if os.path.exists(folder):
            shutil.rmtree(folder) # Xóa sạch thư mục và file bên trong
        os.makedirs(folder)
# --- HÀM LOGIC GHÉP VIDEO ---
def process_video_rendering(video_paths, output_name, quality_option="1080p", audio_path=None):
    clips = []
    final_clip = None
    bgm = None
    try:
        w = 1440 if quality_option == "2K" else 1080
        br = "15000k" if quality_option == "2K" else "8000k"

        for path in video_paths:
            clip = VideoFileClip(path).resize(width=w).without_audio()
            clips.append(clip)
        
        final_clip = concatenate_videoclips(clips, method="compose")
        
        if audio_path and os.path.exists(audio_path):
            bgm = AudioFileClip(audio_path)
            # Loop audio nếu nhạc ngắn hơn video
            if bgm.duration < final_clip.duration:
                # Option: dùng fx.all.loop hoặc đơn giản là cắt nếu dài hơn
                pass 
            
            # Cắt nhạc nếu dài hơn video
            bgm = bgm.subclip(0, min(bgm.duration, final_clip.duration))
            final_clip = final_clip.set_audio(bgm)
        
        final_clip.write_videofile(
            output_name, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac", 
            bitrate=br,
            preset="medium"
        )
        
        # Đóng toàn bộ clip để giải phóng RAM/File
        final_clip.close()
        if audio_path: bgm.close()
        for c in clips:
            c.close()
            
        return output_name
    except Exception as e:
        st.error(f"Lỗi Render {output_name}: {e}")
        return None
    finally:
        # Đảm bảo dù lỗi hay không cũng giải phóng RAM
        if final_clip: final_clip.close()
        if bgm: bgm.close()
        for c in clips: c.close()
    
# --- KHỞI TẠO STATE ---
if 'video_slots' not in st.session_state:
    st.session_state.video_slots = ['Cảnh 1', 'Cảnh 2']

st.title("🎬 AI Video Bulk Composer")

# --- SIDEBAR: CẤU HÌNH ---
st.sidebar.header("⚙️ Cấu hình dự án")
quality = st.sidebar.selectbox("Chất lượng video:", ["1080p", "2K"])
num_outputs = st.sidebar.number_input("Số lượng video:", min_value=1, max_value=50, value=1)
st.sidebar.divider()
st.sidebar.subheader("🎵 Âm thanh")
# Cho phép tải lên nhiều file nhạc để chọn ngẫu nhiên
audio_files = st.sidebar.file_uploader("Tải nhạc (.mp3, .wav)", type=["mp3", "wav"], accept_multiple_files=True)
st.sidebar.divider()
new_slot_name = st.sidebar.text_input("Tên cảnh mới:", placeholder="Ví dụ: Cảnh ăn uống")

col1_sidebar, col2_sidebar = st.sidebar.columns([1, 1])
with col1_sidebar:
    if st.button("➕", use_container_width=True):
        if new_slot_name and new_slot_name not in st.session_state.video_slots:
            st.session_state.video_slots.append(new_slot_name)
            st.rerun()
        elif not new_slot_name:
            st.session_state.video_slots.append(f"Cảnh {len(st.session_state.video_slots) + 1}")
            st.rerun()

with col2_sidebar:
    if st.button("🗑️", use_container_width=True):
        st.session_state.video_slots = ['Cảnh 1', 'Cảnh 2']
        st.rerun()

# --- GIAO DIỆN CHÍNH ---
uploaded_data = {}
for idx, slot_name in enumerate(st.session_state.video_slots):
    with st.container(border=True):
        col_content, col_delete = st.columns([0.95, 0.05])
        with col_content:
            st.markdown(f"**📍 {slot_name}**")
        with col_delete:
            if st.button("❌", key=f"del_{idx}", use_container_width=True):
                st.session_state.video_slots.pop(idx)
                st.rerun()
        
        files = st.file_uploader(f"Tải video cho {slot_name}", type=["mp4", "mov"], accept_multiple_files=True, key=f"uploader_{slot_name}_{idx}")
        uploaded_data[slot_name] = files

# --- NÚT XỬ LÝ HÀNG LOẠT ---
st.divider()
if st.button(f"🚀 XUẤT {num_outputs} VIDEO HÀNG LOẠT", use_container_width=True, type="primary"):
    incomplete = [s for s in st.session_state.video_slots if not uploaded_data[s]]
    
    if incomplete:
        st.error(f"Vui lòng thêm video vào các ô còn trống.")
    else:
        if not os.path.exists("exports"): os.makedirs("exports")
        if not os.path.exists("temp"): os.makedirs("temp")
        cleanup_folders()
        st.session_state.final_files = [] 
        
        for i in range(num_outputs):
            with st.status(f"🏗️ Đang xử lý Video #{i+1}/{num_outputs}...", expanded=True) as status:
                selected_audio_path = None
                if audio_files:
                    chosen_audio = random.choice(audio_files)
                    selected_audio_path = os.path.join("temp", f"audio_{int(time.time())}_{chosen_audio.name}")
                    with open(selected_audio_path, "wb") as f:
                        f.write(chosen_audio.getbuffer())
                shuffled_slots = list(st.session_state.video_slots)
                random.shuffle(shuffled_slots)
                
                current_selection_paths = []
                video_temp_dir = os.path.join("temp", f"batch_v_{i}_{int(time.time())}")
                if not os.path.exists(video_temp_dir): os.makedirs(video_temp_dir)
                
                for slot_name in shuffled_slots:
                    chosen = random.choice(uploaded_data[slot_name])
                    temp_path = os.path.join(video_temp_dir, f"{slot_name}_{chosen.name}")
                    with open(temp_path, "wb") as f:
                        f.write(chosen.getbuffer())
                    current_selection_paths.append(temp_path)

                out_name = f"exports/final_v{i+1}_{int(time.time())}.mp4"
                result = process_video_rendering(current_selection_paths, out_name, quality, audio_path=selected_audio_path)
                
                if result:
                    st.session_state.final_files.append(result) # Lưu vào state thay vì biến tạm
                    status.update(label=f"✅ Video #{i+1} Hoàn tất!", state="complete")

if st.session_state.final_files:
    st.divider()
    col_title, col_clear = st.columns([0.8, 0.2])
    with col_title:
        st.subheader(f"🎉 Đã xuất thành công {len(st.session_state.final_files)} video")
    with col_clear:
        if st.button("Xóa danh sách 🗑️"):
            cleanup_folders()
            st.session_state.final_files = []
            st.rerun()
            
    for index, file_path in enumerate(st.session_state.final_files):
        if os.path.exists(file_path): # Kiểm tra file còn tồn tại không
            with st.container(border=True):
                col_v, col_d = st.columns([0.8, 0.2])
                filename = os.path.basename(file_path)
                with col_v:
                    st.text(f"🎬 {filename}")
                with col_d:
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="Tải về", 
                            data=f, 
                            file_name=filename, 
                            key=f"btn_dl_{index}_{filename}" 
                        )