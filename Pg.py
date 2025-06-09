import numpy as np
from typing import Optional
from some_embedding_module import BedrockEmbedding  # Replace with actual import
from some_llm_module import BedrockConverse  # Replace with actual import
from some_pgvector_module import PGVectorStore  # Replace with actual import
from llama_index.indices.vector_store import VectorStoreIndex
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.schema import QueryBundle
from llama_index.response_synthesizers import get_response_synthesizer
from llama_index.postprocessor import SimilarityPostprocessor

class InMemorySemanticCache:
    def __init__(self, threshold=0.9):
        self.vectors = []
        self.questions = []
        self.responses = []
        self.threshold = threshold

    def cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def search(self, query_vector):
        if not self.vectors:
            return None
        sims = [self.cosine_similarity(query_vector, vec) for vec in self.vectors]
        max_sim = max(sims)
        if max_sim >= self.threshold:
            idx = sims.index(max_sim)
            return self.responses[idx]
        return None

    def add(self, query_vector, question, response):
        self.vectors.append(query_vector)
        self.questions.append(question)
        self.responses.append(response)

class PostgresVectorRetriever:
    def __init__(self, logger=None):
        settings = get_settings()
        self.logger = logger or get_application_logger()
        self.llm_model = settings.get("BEDROCK_MODEL_ID")
        self.region_name = settings.get("AWS_REGION")
        self.embedding_model = settings.get("EMBEDDING_MODEL")

        self.db_name = settings.get("POSTGRES_DB")
        self.db_host = settings.get("POSTGRES_HOST")
        self.db_port = settings.get_int("POSTGRES_PORT", 5432)
        self.db_user = settings.get("POSTGRES_USER")
        self.db_password = settings.get("POSTGRES_PASSWORD")
        self.table_name = settings.get("TABLE_NAME")
        self.embed_dim = settings.get_int("EMBED_DIM", 1024)
        self.debug_mode = settings.get_bool("DEBUG_MODE", True)

        self.llm = None
        self.embed_model = None
        self.vector_store = None
        self.index = None
        self.query_engine = None

        self.semantic_cache = InMemorySemanticCache()

        self.logger.info("PostgresVectorRetriever initialized")

    def create_llm(self):
        if self.llm is None:
            self.llm = BedrockConverse(
                model=self.llm_model,
                region_name=self.region_name,
                temperature=0.0,
                max_tokens=1024
            )
        return self.llm

    def create_embedding_model(self):
        if self.embed_model is None:
            self.embed_model = BedrockEmbedding(
                model=self.embedding_model,
                region_name=self.region_name,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
        return self.embed_model

    def get_schema_template(self):
        from llama_index.prompts import PromptTemplate
        template_str = (
            "Query: {query_str}\n\n"
            "Context: {context_str}\n\n"
            "Based on the context, provide a concise answer to the query.\n"
            "Provide only the information directly relevant to answering the query.\n"
            "Include ALL column names relevant to: {query_str}."
        )
        return PromptTemplate(template_str)

    def create_vector_store(self):
        if self.vector_store is None:
            self.vector_store = PGVectorStore.from_params(
                database=self.db_name,
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                table_name=self.table_name,
                embed_dim=self.embed_dim,
                debug=self.debug_mode,
                cache_ok=True,
                hybrid_search=True,
            )
        return self.vector_store

    def create_index(self):
        if self.index is None:
            vector_store = self.create_vector_store()
            self.create_llm()
            self.create_embedding_model()
            self.index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        return self.index

    def create_query_engine(self):
        if self.query_engine is None:
            index = self.create_index()
            template = self.get_schema_template()
            llm = self.create_llm()
            response_synthesizer = get_response_synthesizer(
                response_mode="tree_summarize",
                llm=llm,
                text_qa_template=template,
            )
            retriever = index.as_retriever(similarity_top_k=15)
            self.query_engine = RetrieverQueryEngine(
                retriever=retriever,
                response_synthesizer=response_synthesizer,
                node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=0.2)]
            )
        return self.query_engine

    def query(self, question: str, format_as_json=False) -> str:
        self.logger.info(f"Querying vector store with question: {question}")
        query_engine = self.create_query_engine()
        embed_model = self.create_embedding_model()

        question_vector = embed_model.get_query_embedding(question)
        cached_response = self.semantic_cache.search(question_vector)

        if cached_response:
            self.logger.info("Cache hit. Returning cached response.")
            return cached_response

        # Fallback to live query
        response = query_engine.query(question)
        response_text = str(response)

        self.semantic_cache.add(question_vector, question, response_text)
        self.logger.info("Query completed and cached successfully.")
        return response_text
