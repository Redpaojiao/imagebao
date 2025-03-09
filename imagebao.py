import streamlit as st
from PIL import Image
import io
import hashlib
import zipfile

# 新增函数：格式化文件大小
def format_size(size_bytes):
    """将字节数转换为易读的文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024*1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024*1024):.1f} MB"

# 界面配置
st.set_page_config(page_title="图片压缩宝", page_icon="🖼️", layout="wide")
st.title("🎨 图片压缩宝")
st.caption("支持JPG/PNG/WEBP格式 | 最大尺寸4000px | 批量处理")

# 会话状态初始化
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = {}

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 参数设置")
    quality = st.slider("压缩质量 (%)", 1, 100, 50, help="数值越小文件体积越小")
    keep_original_size = st.checkbox("保持原尺寸", help="如果勾选，图片将不会被缩放")
    if not keep_original_size:
        max_size = st.number_input("最大边长 (px)", 100, 4000, 1920)
    output_format = st.selectbox("输出格式", ["JPEG", "PNG", "WEBP"])

# 文件上传区
uploaded_files = st.file_uploader("上传图片", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)

if uploaded_files:
    cols = st.columns(2)
    progress_bar = st.progress(0)

    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            # 获取原始文件大小
            original_size_bytes = uploaded_file.size  # 新增
            original_size = format_size(original_size_bytes)  # 新增

            # 原始图片处理
            original_img = Image.open(uploaded_file)
            original_width, original_height = original_img.size

            # 尺寸缩放
            if keep_original_size:
                resized_img = original_img
                new_size = (original_width, original_height)
            else:
                scale = min(max_size/original_width, max_size/original_height)
                new_size = (int(original_width*scale), int(original_height*scale))
                resized_img = original_img.resize(new_size, Image.Resampling.LANCZOS)

            # 格式转换预处理
            if output_format == "JPEG" and resized_img.mode != "RGB":
                resized_img = resized_img.convert("RGB")

            # 保存图片
            buffer = io.BytesIO()
            save_params = {'quality': quality, 'optimize': True}
            if output_format == "PNG":
                save_params['compress_level'] = 9 - int(quality/11.25)
            resized_img.save(buffer, format=output_format, **save_params)

            # 计算压缩后大小和效率
            compressed_size_bytes = len(buffer.getvalue())  # 新增
            compressed_size = format_size(compressed_size_bytes)  # 新增
            compression_ratio = (original_size_bytes - compressed_size_bytes) / original_size_bytes * 100  # 新增
            ratio_text = (f"✅ 节省 {compression_ratio:.1f}%" if compression_ratio > 0
                         else f"⚠️ 增加 {-compression_ratio:.1f}%")  # 新增

            # 生成文件名
            ext = "jpg" if output_format == "JPEG" else output_format.lower()
            file_hash = hashlib.md5(buffer.getvalue()).hexdigest()[:8]
            filename = f"compressed_{file_hash}.{ext}"

            # 存储处理结果
            st.session_state.processed_images[filename] = buffer.getvalue()

            # 显示对比
            with cols[idx%2]:
                st.subheader(f"#{idx+1} {uploaded_file.name}")
                col1, col2 = st.columns(2)

                # 原始图片列
                with col1:
                    st.image(
                        original_img,
                        caption="原始图片",
                        use_container_width=True
                    )
                    st.caption(
                        f"尺寸: {original_width}x{original_height} | "  # 修改
                        f"格式: {original_img.format} | "
                        f"大小: {original_size}"
                    )

                # 压缩图片列
                with col2:
                    st.image(
                        buffer,
                        caption=f"压缩版本 ({quality}%)",
                        use_container_width=True
                    )
                    st.caption(
                        f"新尺寸: {new_size[0]}x{new_size[1]} | "  # 修改
                        f"格式: {output_format} | "
                        f"大小: {compressed_size}\n"
                        f"{ratio_text}"  # 新增压缩效率
                    )
                    st.download_button(
                        label="⬇️ 下载",
                        data=buffer.getvalue(),
                        file_name=filename,
                        mime=f"image/{'jpeg' if output_format == 'JPEG' else output_format.lower()}",
                        key=f"dl_{idx}"
                    )

            progress_bar.progress((idx+1)/len(uploaded_files))

        except Exception as e:
            st.error(f"处理失败: {str(e)}")

    # 批量下载功能
    if st.session_state.processed_images:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for name, data in st.session_state.processed_images.items():
                zip_file.writestr(name, data)

        st.download_button(
            label="📦 打包下载全部",
            data=zip_buffer.getvalue(),
            file_name="压缩后图片.zip",
            mime="application/zip"
        )
