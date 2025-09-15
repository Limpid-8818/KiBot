import hashlib
import json
import os
import shutil
from typing import List, Dict, Any

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing_extensions import deprecated

from .embeddings import DashScopeEmbeddings
from infra.logger import logger


class RAGService:
    def __init__(self, docs_dir: str = "rag_docs"):
        self.docs_dir = docs_dir
        self.index_dir = os.path.join(docs_dir, "index")
        self.checksum_file = os.path.join(docs_dir, "document_checksums.json")  # 检查文档状态

        self.embeddings = DashScopeEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "，", " ", ""]
        )

        os.makedirs(self.docs_dir, exist_ok=True)
        self.document_checksums = self._load_checksums()
        self.vector_store = self._load_or_rebuild_vector_store()

    def _load_or_rebuild_vector_store(self) -> FAISS:
        current_docs = self._get_all_documents()

        # 如果索引不存在，直接创建
        if not os.path.exists(self.index_dir):
            return self._build_vector_store(current_docs)

        # 检查是否有文档变化
        if self._has_document_changes(current_docs):
            logger.info("RAG", "检测到文档变更，重新建立索引。")
            # 删除旧索引
            if os.path.exists(self.index_dir):
                shutil.rmtree(self.index_dir)
            # 重建新索引
            return self._build_vector_store(current_docs)

        # 索引存在且无变化，直接加载
        return FAISS.load_local(
            self.index_dir,
            self.embeddings,
            allow_dangerous_deserialization=True
        )

    def _build_vector_store(self, docs_list: List[str]) -> FAISS:
        """基于当前文档列表构建新索引"""
        if not docs_list:
            # 空文档时创建占位文档
            placeholder_doc = Document(
                page_content="",
                metadata={"source": "placeholder"}
            )
            return FAISS.from_documents([placeholder_doc], self.embeddings)

        # 加载所有文档
        loader = DirectoryLoader(
            self.docs_dir,
            glob="*.txt",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        documents = loader.load()

        # 分割文档并创建索引、保存校验和
        splits = self.text_splitter.split_documents(documents)
        vector_store = FAISS.from_documents(splits, self.embeddings)
        vector_store.save_local(self.index_dir)
        self._save_checksums()
        return vector_store

    def _has_document_changes(self, current_docs: List[str]) -> bool:
        """检查文档是否有变更"""
        # 检查已删除的文档
        for doc_name in self.document_checksums:
            if doc_name not in current_docs:
                return True

        # 检查新增或修改的文档
        for doc_name in current_docs:
            file_path = os.path.join(self.docs_dir, doc_name)
            current_checksum = self._calculate_checksum(file_path)

            # 新增文档
            if doc_name not in self.document_checksums:
                return True

            # 修改的文档
            if self.document_checksums[doc_name] != current_checksum:
                return True

        return False

    def _load_checksums(self) -> Dict[str, str]:
        if os.path.exists(self.checksum_file):
            with open(self.checksum_file, "r", encoding="utf-8") as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    return {}
        with open(self.checksum_file, "w", encoding="utf-8") as file:
            json.dump({}, file, ensure_ascii=False, indent=2)
        return {}

    def _save_checksums(self) -> None:
        checksums = {}
        current_docs = self._get_all_documents()

        # 为所有当前存在的文档计算新的校验和
        for doc_name in current_docs:
            file_path = os.path.join(self.docs_dir, doc_name)
            checksums[doc_name] = self._calculate_checksum(file_path)

        # 更新内存中的校验和
        self.document_checksums = checksums

        # 保存到文件
        with open(self.checksum_file, "w", encoding="utf-8") as file:
            json.dump(checksums, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _calculate_checksum(file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as file:
            while chunk := file.read(4096):
                hasher.update(chunk)
        return hasher.hexdigest()  # 计算MD5校验和

    def _get_all_documents(self) -> List[str]:
        """获取文档目录中所有的txt文件"""
        return [file for file in os.listdir(self.docs_dir)
                if file.endswith(".txt") and os.path.isfile(os.path.join(self.docs_dir, file))]

    @deprecated("Use _load_or_rebuild_vector_store() instead")
    def _load_vector_store(self) -> FAISS:
        if os.path.exists(f"{self.docs_dir}/index"):
            return FAISS.load_local(
                f"{self.docs_dir}/index",
                self.embeddings,
                allow_dangerous_deserialization=True
            )

        loader = DirectoryLoader(
            self.docs_dir,
            glob="*.txt",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        documents = loader.load()
        splits = self.text_splitter.split_documents(documents)

        vector_store = FAISS.from_documents(splits, self.embeddings)
        vector_store.save_local(f"{self.docs_dir}/index")
        return vector_store

    def add_document(self, content: str, filename: str) -> None:
        """新增文档"""
        if not filename.endswith(".txt"):
            filename = f"{filename}.txt"

        file_path = os.path.join(self.docs_dir, filename)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        self.check_and_update_documents()

    def delete_document(self, filename: str) -> bool:
        if not filename.endswith(".txt"):
            filename = f"{filename}.txt"

        file_path = os.path.join(self.docs_dir, filename)

        if os.path.exists(file_path):
            os.remove(file_path)
            self.check_and_update_documents()
            return True
        return False

    def check_and_update_documents(self) -> Dict[str, int]:
        """
        检查文档变化并增量更新向量存储
        返回变更统计: 新增、更新、删除的文档数量
        """
        current_docs = self._get_all_documents()
        previous_checksums = self.document_checksums.copy()

        # 计算变化统计
        changes = {
            "added": 0,
            "updated": 0,
            "removed": 0
        }

        # 检查删除的文档
        for doc_name in previous_checksums:
            if doc_name not in current_docs:
                changes["removed"] += 1

        # 检查新增和更新的文档
        for doc_name in current_docs:
            file_path = os.path.join(self.docs_dir, doc_name)
            current_checksum = self._calculate_checksum(file_path)

            if doc_name not in previous_checksums:
                changes["added"] += 1
            elif previous_checksums[doc_name] != current_checksum:
                changes["updated"] += 1

        # 如果有变更，重建索引
        if any(v > 0 for v in changes.values()):
            # 删除旧索引
            if os.path.exists(self.index_dir):
                shutil.rmtree(self.index_dir)
            # 构建新索引
            self.vector_store = self._build_vector_store(current_docs)
            # 更新校验和
            self._save_checksums()

        return changes

    def query(self, question: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """查询相关文档片段"""
        docs = self.vector_store.similarity_search(question, k=top_k)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            } for doc in docs
        ]


if __name__ == "__main__":
    rag_service = RAGService("../../rag_docs")

    # 测试查询功能
    test_queries = [
        "人工智能有哪些主要技术分支？",
        "什么是弱人工智能？",
        "人工智能在医疗健康领域有哪些应用？",
        "当前人工智能发展面临哪些挑战？",
        "什么是超人工智能？"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n----- 测试查询 {i}: {query} -----")
        try:
            results = rag_service.query(query, top_k=2)
            if results:
                print(f"✅ 找到 {len(results)} 条相关结果:")
                for j, result in enumerate(results, 1):
                    print(f"\n相关片段 {j}:\n{result['content'][:200]}...")  # 只显示前200字符
            else:
                print("❌ 未找到相关结果")
        except Exception as e:
            print(f"❌ 查询出错: {str(e)}")
