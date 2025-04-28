import os
from llama_index.embeddings.bedrock import BedrockEmbedding
from llama_index.core import Settings
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy import make_url
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.readers.s3 import S3Reader
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.ingestion.pipeline import DocstoreStrategy

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
            prefix=self.prefix,
            aws_access_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_access_secret=os.getenv("AWS_SECRET_ACCESS_KEY"),
            required_exts=['.md'],
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

        print("Building vector index with deduplication using docstore...")

        # Initialize a simple document store
        docstore = SimpleDocumentStore()

        # Create ingestion pipeline with document management
        pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(chunk_size=512, chunk_overlap=20),
                Settings.embed_model,
            ],
            vector_store=vector_store,
            docstore=docstore,
            docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE
        )

        if os.path.exists("docstore.json"):
            # Load existing docstore from disk
            print("Loading existing docstore from disk...")
            # pipeline.docstore.load_from_disk("docstore.json")
            pipeline.load("docstore.json")

        # Run ingestion pipeline
        pipeline.run(documents=documents, show_progress=True)

        # pipeline.docstore.save_to_disk("docstore.json")
        pipeline.persist("docstore.json")

        # Create index from vector store (for querying if needed)
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store, storage_context=storage_ctx)

        print("Index built and persisted to PostgreSQL with deduplication")
        return index

    def query(self, index, question: str):
        print(f"Querying index with: {question}")
        query_engine = index.as_query_engine()
        response = query_engine.query(question)
        return response

def main():
    bucket = "bedrock-350474408512-us-east-1"
    prefix = "markdown/"
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:yourpassword@localhost:5432/vector_db1")

    indexer = MarkdownS3ToPGVectorIndexer(bucket, prefix, db_url)
    index = indexer.build_index()
    # response = indexer.query(index, "How many customers are there?")
    # print("Query response:", response)

if __name__ == "__main__":
    main()
