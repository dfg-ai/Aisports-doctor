import os
import re
import traceback
from pathlib import Path

try:
    from langchain_community.document_loaders import PyPDFLoader
except ImportError as e:
    print(f"导入PyPDFLoader失败: {e}")
    print("尝试使用pypdf直接加载...")
    try:
        from pypdf import PdfReader
        has_pypdf = True
    except ImportError as e2:
        print(f"导入pypdf失败: {e2}")
        has_pypdf = False

class DataCleaner:
    def __init__(self, input_dir="./sports_data", output_dir="./cleaned_data"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        print(f"输入目录: {self.input_dir}")
        print(f"输出目录: {self.output_dir}")

    def clean_text(self, text):
        """核心清洗逻辑"""
        # 1. 替换连续的换行符和空格
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        
        # 2. 去除页码噪音 (如: "- 12 -", "Page 5 of 20")
        text = re.sub(r'\n- \d+ -\n', '', text)
        text = re.sub(r'Page \d+ of \d+', '', text)
        
        # 3. 修复中文中间的异常空格 (如: "运 动 康 复" -> "运动康复")
        text = re.sub(r'([\u4e00-\u9fa5]) ([\u4e00-\u9fa5])', r'\1\2', text)
        
        # 4. 去除无关的特殊符号，但保留标点
        text = re.sub(r'[^\w\s\u4e00-\u9fa5，。！？；：（）《》"".,!?;:()]', '', text)
        
        return text.strip()

    def process_all(self):
        print("开始清洗原始文档...")
        
        # 检查输入目录是否存在
        if not self.input_dir.exists():
            print(f"错误: 输入目录 {self.input_dir} 不存在")
            return
        
        # 列出目录中的所有文件
        files = list(self.input_dir.glob("*"))
        print(f"找到 {len(files)} 个文件")
        for file in files:
            print(f"  - {file.name}")
        
        for file_path in self.input_dir.glob("*"):
            if file_path.suffix.lower() in ['.pdf', '.txt']:
                print(f"正在清洗: {file_path.name}")
                
                try:
                    # 加载内容
                    if file_path.suffix == '.pdf':
                        try:
                            # 尝试使用PyPDFLoader
                            loader = PyPDFLoader(str(file_path))
                            docs = loader.load()
                            content = "\n".join([doc.page_content for doc in docs])
                            print(f"  使用PyPDFLoader成功加载，页数: {len(docs)}")
                        except Exception as e:
                            print(f"  PyPDFLoader加载失败: {e}")
                            # 尝试使用pypdf作为备选
                            if has_pypdf:
                                print("  尝试使用pypdf加载...")
                                reader = PdfReader(str(file_path))
                                content = "\n".join([page.extract_text() for page in reader.pages])
                                print(f"  使用pypdf成功加载，页数: {len(reader.pages)}")
                            else:
                                print("  无法加载PDF文件，跳过")
                                continue
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        print(f"  成功加载文本文件，长度: {len(content)}")

                    # 执行清洗
                    cleaned_content = self.clean_text(content)
                    print(f"  清洗后长度: {len(cleaned_content)}")

                    # 保存
                    output_path = self.output_dir / f"{file_path.stem}.txt"
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)
                    print(f"  保存成功: {output_path}")
                    
                except Exception as e:
                    print(f"  处理失败: {e}")
                    print(traceback.format_exc())
        
        # 检查输出目录
        output_files = list(self.output_dir.glob("*"))
        print(f"清洗完成！处理后的文件保存在: {self.output_dir}")
        print(f"生成的文件数: {len(output_files)}")
        for file in output_files:
            print(f"  - {file.name}")

if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.process_all()
