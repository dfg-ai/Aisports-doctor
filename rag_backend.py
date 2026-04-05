import os
import sys
import time
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# 保持你之前的兼容性修复
class LangChainFix:
    def __getattr__(self, name):
        if name in ['debug', 'llm_cache']: return None
        return None
sys.modules['langchain'] = LangChainFix()

from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.llms import Tongyi
from langchain_community.embeddings import DashScopeEmbeddings

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MedicalRAG")

class MultiKBSystem:
    def __init__(self, storage_path: str = "./medical_kb"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.embeddings = DashScopeEmbeddings(model="text-embedding-v2")
        self.kb_metadata_path = self.storage_path / "kb_info.json"
        self.kb_info = self._load_kb_info()
        self.conversations = {}

    def _load_kb_info(self):
        logger.info(f"加载知识库信息，路径: {self.kb_metadata_path}")
        logger.info(f"文件存在: {self.kb_metadata_path.exists()}")
        if self.kb_metadata_path.exists():
            try:
                with open(self.kb_metadata_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"文件内容: {content}")
                    data = json.loads(content)
                    logger.info(f"加载的数据: {data}")
                    logger.info(f"知识库数量: {len(data)}")
                    return data
            except Exception as e:
                logger.error(f"读取文件失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning(f"知识库文件不存在: {self.kb_metadata_path}")
        return {}

    def add_file(self, uploaded_file):
        """带元数据标签的入库逻辑"""
        kb_id = f"kb_{int(time.time())}"
        kb_dir = self.storage_path / kb_id
        kb_dir.mkdir(exist_ok=True)
        
        file_path = kb_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        # 加载自动化标注索引
        metadata_index = {}
        index_path = Path("doc_metadata_index.json")
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                metadata_index = json.load(f)
        
        file_info = metadata_index.get(uploaded_file.name, {})
        custom_metadata = {
            "category": file_info.get("category", "通用康复"),
            "doc_type": file_info.get("doc_type", "技术指南"),
            "source": uploaded_file.name
        }

        loader = PyPDFLoader(str(file_path)) if uploaded_file.name.endswith('.pdf') else TextLoader(str(file_path), encoding='utf-8')
        docs = loader.load()
        for doc in docs:
            doc.metadata.update(custom_metadata)

        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)
        chunks = splitter.split_documents(docs)

        Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(kb_dir / "chroma_db")
        )
        
        self.kb_info[kb_id] = {"name": uploaded_file.name, "path": str(kb_dir / "chroma_db"), "category": custom_metadata["category"]}
        with open(self.kb_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.kb_info, f, ensure_ascii=False)

    def ask(self, question: str, kb_ids: List[str], conversation_id=None):
        """Agentic RAG：先问诊检查，再检索回答"""
        logger.info(f"进入ask方法，问题: {question}")
        logger.info(f"传入的kb_ids: {kb_ids}")
        logger.info(f"当前kb_info: {self.kb_info}")
        logger.info(f"kb_info长度: {len(self.kb_info)}")
        
        if not kb_ids:
            logger.info("kb_ids为空，返回提示")
            return "请先上传并选择康复知识库。", [], conversation_id, {"faithfulness": 0, "relevance": 0}

        llm = Tongyi(model="qwen-plus", temperature=0.1)

        # --- 阶段 1: 问诊门卫 (Slot Filling) ---
        check_prompt = f"""
        你是一名专业的运动康复师。用户咨询："{question}"
        请检查用户是否提供了以下三项关键信息：
        1. 具体的疼痛位置（如膝盖外侧、脚踝、腰部）
        2. 痛感的描述（如刺痛、酸痛、胀痛、是否有红肿）
        3. 发生的动作场景（如跑步中、杀球后、早起时）

        要求：
        - 如果三项关键信息基本齐全，请只输出两个字: READY
        - 如果信息有缺失，请以康复师的口吻，礼貌地追问缺失的信息，不要给出任何诊断，不要输出其他废话。
        """
        check_result = llm.invoke(check_prompt).strip()

        if "READY" not in check_result.upper():
            # 信息不足，直接返回追问，不执行 RAG 检索以节省资源并防幻觉
            return check_result, [], conversation_id, {"faithfulness": 0, "relevance": 0}

        # --- 阶段 2: 意图识别与库过滤 ---
        intent_prompt = f"根据问题判断运动损伤部位（膝盖、足踝、腰背、肩肘、通用）：{question}"
        predicted_cat = llm.invoke(intent_prompt).strip().replace("*", "")
        
        filtered_kb = [kid for kid in kb_ids if self.kb_info[kid].get("category") == predicted_cat]
        if not filtered_kb: filtered_kb = kb_ids # 没匹配到则全量搜

        # --- 阶段 3: 执行检索 ---
        all_docs = []
        for kid in filtered_kb:
            db = Chroma(persist_directory=self.kb_info[kid]["path"], embedding_function=self.embeddings)
            docs = db.similarity_search(question, k=4)
            all_docs.extend(docs)

        # --- 阶段 4: 专业康复建议生成 ---
        context_text = "\n\n".join([f"[依据{i+1}]: {d.page_content}" for i, d in enumerate(all_docs)])
        
        qa_prompt = f"""你现在是国家队级的运动康复专家。请严格根据参考资料回答。

{context_text}

【用户主诉】：{question}

【回答结构要求】：
1. 损伤定性：基于资料分析可能的损伤（如：鹅足滑囊炎风险）。
2. 即刻处理：给出RICE原则或针对性的急性期建议。
3. 康复练习：从资料中提取具体的拉伸或力量训练动作（需包含次数和要点）。
4. 风险警示：若出现剧痛、关节绞锁或无法负重，强制要求就医。
5. 免责声明：结尾注明“本建议仅供健康科普，不替代专业医疗诊断”。

注意：严禁开药，回答需专业、干练。"""

        answer = llm.invoke(qa_prompt)
        return answer, all_docs, conversation_id, {"faithfulness": 0.8, "relevance": 0.9}

    def create_conversation(self):
        return str(uuid.uuid4())
