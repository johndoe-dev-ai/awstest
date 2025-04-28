from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.llms.bedrock_converse import BedrockConverse
from llama_index.core import Settings
from llama_index.embeddings.bedrock import BedrockEmbedding
import os
import logging
# Enable logging
logging.basicConfig(level=logging.ERROR)

llm = BedrockConverse(
    model="us.anthropic.claude-3-sonnet-20240229-v1:0",  # Replace with your desired model ID
    region_name="us-east-1"  # Replace with your AWS region
)
Settings.llm = llm

embed_model = BedrockEmbedding(
            model_name="amazon.titan-embed-text-v2:0",
            region_name="us-east-1",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
Settings.embed_model = embed_model
# Initialize the vector store
vector_store = PGVectorStore.from_params(
    database="vector_db1",
    host="localhost",
    port=5432,
    user="postgres",
    password="yourpassword",
    table_name="markdown_vectors",
    embed_dim=1024,  # Replace with your embedding dimension,
    debug=True  # Enable debug mode for detailed logging
)
#print(f"Vector store initialized.{vector_store}")
# Create the index from the existing vector store
index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

# Create a query engine from the index
query_engine = index.as_query_engine()

question = "Tell me about the customers who placed orders?"

prompt = f"You are an expert. You need to provide the table_name, columns present in these tables and joining conditions if any for the question {question}. You need to provide the answer in json format. The json should have the following keys: table_name, columns, join_conditions. The values for these keys should be a string. The json should be formatted properly and should not have any extra spaces or new lines. The json should be valid and parsable."

# Perform a query
response = query_engine.query(prompt)

# Output the response
print(response)
