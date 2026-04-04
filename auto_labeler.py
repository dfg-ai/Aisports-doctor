import json
import os
from pathlib import Path
from langchain_community.llms import Tongyi

# 设置 API Key (如果环境变量没设)
# os.environ["DASHSCOPE_API_KEY"] = "你的KEY"

class AutoLabeler:
    def __init__(self, data_dir="./cleaned_data"):
        self.data_dir = Path(data_dir)
        self.llm = Tongyi(model="qwen-plus", temperature=0)
        self.index_file = Path("doc_metadata_index.json")

    def get_metadata_from_llm(self, file_name, content_sample):
        """调用 LLM 进行自动化标注"""
        prompt = f"""
        请分析以下运动康复文档的内容片段，并给出其元数据分类。
        文档名称：{file_name}
        文档片段：{content_sample[:1000]}...
        
        请严格按 JSON 格式输出，包含以下字段：
        1. category: 从 (膝盖, 足踝, 腰背, 肩肘, 颈椎, 通用) 中选一个最匹配的。
        2. doc_type: 从 (康复方案, 技术指南, 科普文章, 案例分析) 中选一个。
        3. priority: 1-5 的整数，权威教材设为 1，科普设为 5。
        
        只输出 JSON，不要任何解释。
        """
        try:
            response = self.llm.invoke(prompt)
            # 提取 JSON 字符串
            json_str = response.strip().replace("```json", "").replace("```", "")
            return json.loads(json_str)
        except Exception as e:
            print(f"标注文件 {file_name} 出错: {e}")
            return {"category": "通用", "doc_type": "未分类", "priority": 3}

    def run(self):
        print("开始自动化标注...")
        metadata_index = {}
        
        # 遍历清洗后的文本文件
        for file_path in self.data_dir.glob("*.txt"):
            print(f"正在分析: {file_path.name}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 获取标注
            label = self.get_metadata_from_llm(file_path.name, content)
            
            # 这里存的是原始的文件名 (比如 PDF 名)，方便后端匹配
            original_name = file_path.stem + ".pdf" 
            metadata_index[original_name] = label

        # 保存索引文件
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(metadata_index, f, ensure_ascii=False, indent=2)
        
        print(f"标注完成！索引文件已生成: {self.index_file}")

if __name__ == "__main__":
    labeler = AutoLabeler()
    labeler.run()
