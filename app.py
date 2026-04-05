import streamlit as st
import sys
import logging
from rag_backend import MultiKBSystem
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StreamlitApp')

try:
    st.set_page_config(page_title="数字运动康复师", page_icon="🏃", layout="wide")
    
    # 不使用缓存，直接初始化
    def init_system():
        try:
            logger.info("初始化MultiKBSystem...")
            # 使用绝对路径确保正确找到知识库
            from pathlib import Path
            base_dir = Path(__file__).parent
            medical_kb_path = base_dir / "medical_kb"
            logger.info(f"使用知识库路径: {medical_kb_path}")
            
            # 手动检查文件
            kb_info_path = medical_kb_path / "kb_info.json"
            logger.info(f"手动检查kb_info.json: {kb_info_path.exists()}")
            if kb_info_path.exists():
                import json
                with open(kb_info_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"手动读取内容: {content}")
                    data = json.loads(content)
                    logger.info(f"手动解析结果: {data}")
            
            system = MultiKBSystem(storage_path=str(medical_kb_path))
            logger.info(f"MultiKBSystem初始化成功，知识库数量: {len(system.kb_info)}")
            logger.info(f"知识库详情: {system.kb_info}")
            return system
        except Exception as e:
            logger.error(f"初始化MultiKBSystem失败: {e}")
            st.error(f"系统初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    logger.info("开始加载应用...")
    rag = init_system()
    logger.info("应用加载完成")
    # 显示知识库信息
    logger.info(f"最终rag.kb_info: {rag.kb_info}")
    logger.info(f"最终知识库数量: {len(rag.kb_info)}")
    # 在界面上显示知识库信息
    st.sidebar.markdown(f"### 📚 知识库状态")
    st.sidebar.markdown(f"**知识库数量**: {len(rag.kb_info)}")
    if rag.kb_info:
        st.sidebar.markdown("**可用知识库**:")
        for kb_id, kb_info in rag.kb_info.items():
            st.sidebar.markdown(f"- {kb_info['name']}")
    else:
        st.sidebar.markdown("**暂无知识库**")

    # --- 侧边栏 ---
    with st.sidebar:
        st.title("🏥 康复知识库")
        
        # 调试按钮
        if st.button("🔍 查看知识库状态"):
            st.markdown("### 📚 知识库详细状态")
            st.markdown(f"**知识库数量**: {len(rag.kb_info)}")
            st.markdown(f"**kb_info内容**: {rag.kb_info}")
            
            # 检查文件是否存在
            from pathlib import Path
            base_dir = Path(__file__).parent
            medical_kb_path = base_dir / "medical_kb"
            kb_info_path = medical_kb_path / "kb_info.json"
            st.markdown(f"**kb_info.json路径**: {kb_info_path}")
            st.markdown(f"**kb_info.json存在**: {kb_info_path.exists()}")
            
            if kb_info_path.exists():
                import json
                with open(kb_info_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    st.markdown(f"**文件内容**: {content}")
        
        files = st.file_uploader("上传运动医学指南 (PDF/TXT)", accept_multiple_files=True)
        if st.button("🔨 建立索引"):
            if files:
                for f in files:
                    with st.spinner(f"正在处理 {f.name}..."):
                        try:
                            rag.add_file(f)
                            logger.info(f"处理文件成功: {f.name}")
                        except Exception as e:
                            logger.error(f"处理文件失败: {e}")
                            st.error(f"处理文件失败: {e}")
                st.success("索引构建完成！")
            else:
                st.warning("请先选择文件")
    
        st.divider()
        st.subheader("快捷问诊场景")
        if st.button("🏃 跑步后膝盖外侧痛"):
            st.session_state.temp_input = "我昨天跑完半马，膝盖外侧有明显的刺痛感，上下楼梯尤为严重。"
        if st.button("🏸 杀球后肩膀酸疼"):
            st.session_state.temp_input = "打完羽毛球后，肩膀后侧胀痛，手臂抬起来费劲。"

    # --- 主界面 ---
    st.title("🏃 数字运动康复师")
    st.info("💡 提示：为了给您精准建议，请描述：疼痛位置、痛感性质、触发场景。")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 显示历史
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # 输入框逻辑
    user_input = st.chat_input("描述你的运动损伤经历...")
    if "temp_input" in st.session_state:
        user_input = st.session_state.pop("temp_input")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("康复师正在分析症状并查阅指南..."):
                try:
                    logger.info(f"当前rag对象: {rag}")
                    logger.info(f"rag.kb_info: {rag.kb_info}")
                    logger.info(f"rag.kb_info长度: {len(rag.kb_info)}")
                    kb_ids = list(rag.kb_info.keys())
                    logger.info(f"生成的kb_ids: {kb_ids}")
                    logger.info(f"开始处理问题，知识库数量: {len(kb_ids)}")
                    ans, docs, _, eval_info = rag.ask(user_input, kb_ids)
                    logger.info(f"回答生成成功")
                    st.markdown(ans)
                    
                    if docs:
                        with st.expander("查看康复依据"):
                            for d in docs:
                                st.write(f"📝 {d.metadata.get('source')}: {d.page_content[:150]}...")
                except Exception as e:
                    logger.error(f"处理问题失败: {e}")
                    st.error(f"处理问题失败: {e}")
                    import traceback
                    traceback.print_exc()
                    ans = f"处理问题时出错: {e}"
    
        st.session_state.messages.append({"role": "assistant", "content": ans})
except Exception as e:
    logger.error(f"应用启动失败: {e}")
    st.error(f"应用启动失败: {e}")
    import traceback
    traceback.print_exc()
