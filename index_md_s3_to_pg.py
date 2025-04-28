import os
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.core import Settings
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy import make_url
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.readers.s3 import S3Reader

class MarkdownS3ToPGVectorIndexer:
    def __init__(self, 
                 bucket: str,
                 prefix: str,
                 db_url: str,
                 bedrock_model: str = "amazon.titan-embed-text-v2:0",
                 aws_region: str = "us-east-1"):
        self.bucket = bucket
        self.prefix = prefix
        self.db_url = make_url(db_url)
        self.bedrock_model = bedrock_model
        self.aws_region = aws_region

    def _load_documents(self):
        print(f"Loading documents from S3 bucket '{self.bucket}'...")
        reader = S3Reader(
                bucket=self.bucket,
                prefix=self.prefix,  # Optional: to filter by prefix
                aws_access_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_access_secret=os.getenv("AWS_SECRET_ACCESS_KEY"),
                required_exts=['.md'],  # Specify that you want to read markdown files
        )
        
        
        documents = reader.load_data()
        print(f"Loaded {len(documents)} documents from S3")
        return documents

    def _initialize_bedrock_embedding(self):
        print("Initializing Bedrock embedding model...")
        embed_model = BedrockEmbedding(
            model_name=self.bedrock_model,
            region_name=self.aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        Settings.embed_model = embed_model

    def _create_vector_store(self):
        print("Creating PGVectorStore instance...")
        return PGVectorStore.from_params(
            database=self.db_url.database,
            host=self.db_url.host,
            port=self.db_url.port,
            user=self.db_url.username,
            password=self.db_url.password,
            table_name="markdown_vectors",
            embed_dim=1024,
        )

    def build_index(self):
        self._initialize_bedrock_embedding()
        documents = self._load_documents()
        vector_store = self._create_vector_store()
        storage_ctx = StorageContext.from_defaults(vector_store=vector_store)
        print("Building vector index...")
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_ctx,
            show_progress=True,
        )
        print("Index built and persisted to PostgreSQL")
        return index

    def query(self, index, question: str):
        print(f"Querying index with: {question}")
        query_engine = index.as_query_engine()
        response = query_engine.query(question)
        return response

def main():
    bucket = "bedrock-350474408512-us-east-1"
    prefix = "markdown/"
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:yourpassword@localhost:5432/vector_db")

    indexer = MarkdownS3ToPGVectorIndexer(bucket, prefix, db_url)
    index = indexer.build_index()
    response = indexer.query(index, "How many customers are there?")
    print("Query response:", response)

if __name__ == "__main__":
    main()
