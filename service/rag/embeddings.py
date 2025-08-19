from dashscope import TextEmbedding
from langchain_core.embeddings import Embeddings

from infra.config.settings import settings


class DashScopeEmbeddings(Embeddings):
    def __init__(self):
        self.model = settings.EMBEDDINGS_MODEL
        self.api_key = settings.EMBEDDINGS_API_KEY

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        batch_size = 10

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = TextEmbedding.call(
                    api_key=self.api_key,
                    model=self.model,
                    input=batch
                )
                if response.status_code == 200:
                    embeddings.extend([record['embedding'] for record in response.output['embeddings']])
                else:
                    raise Exception(f"嵌入模型调用失败: {response.message}")
            except Exception as e:
                raise Exception(f"生成文档嵌入时出错: {str(e)}")
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        try:
            response = TextEmbedding.call(
                api_key=self.api_key,
                model=self.model,
                input=[text]
            )
            if response.status_code == 200:
                return response.output['embeddings'][0]['embedding']
            else:
                raise Exception(f"嵌入模型调用失败: {response.message}")
        except Exception as e:
            raise Exception(f"生成查询嵌入时出错: {str(e)}")
