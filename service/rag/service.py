import os
from typing import List, Dict, Any

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .embeddings import DashScopeEmbeddings


class RAGService:
    def __init__(self, docs_dir: str = "rag_docs"):
        self.docs_dir = docs_dir
        self.embeddings = DashScopeEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "，", " ", ""]
        )
        self.vector_store = self._load_vector_store()

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
        os.makedirs(self.docs_dir, exist_ok=True)

        with open(f"{self.docs_dir}/{filename}.txt", "w", encoding="utf-8") as f:
            f.write(content)

        document = self.text_splitter.create_documents([content])[0]
        self.vector_store.add_documents([document])
        self.vector_store.save_local(f"{self.docs_dir}/index")

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
