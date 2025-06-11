import boto3 
import pickle 
import io 
import numpy as np 
from typing import List, Optional 
from numpy.linalg import norm 
import logging 
import threading import time

class InMemorySemanticCache: 
 def init(self, threshold=0.9): 
    self.vectors: List[np.ndarray] = [] self.questions: List[str] = [] self.responses: List[str] = [] self.threshold = threshold

def add(self, question_vector: np.ndarray, question: str, response: str):
    self.vectors.append(question_vector)
    self.questions.append(question)
    self.responses.append(response)

def search(self, question_vector: np.ndarray) -> Optional[str]:
    if not self.vectors:
        return None

    sims = [self._cosine_similarity(question_vector, vec) for vec in self.vectors]
    best_idx = int(np.argmax(sims))
    best_sim = sims[best_idx]

    if best_sim >= self.threshold:
        return self.responses[best_idx]
    return None

def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (norm(a) * norm(b) + 1e-8))

def save_to_s3(self, bucket_name: str, object_key: str, region: str = "ap-south-1"):
    s3 = boto3.client("s3", region_name=region)
    cache_data = {
        "vectors": [v.tolist() for v in self.vectors],
        "questions": self.questions,
        "responses": self.responses
    }
    byte_stream = io.BytesIO()
    pickle.dump(cache_data, byte_stream)
    byte_stream.seek(0)
    s3.upload_fileobj(byte_stream, Bucket=bucket_name, Key=object_key)

def load_from_s3(self, bucket_name: str, object_key: str, region: str = "ap-south-1"):
    s3 = boto3.client("s3", region_name=region)
    byte_stream = io.BytesIO()
    s3.download_fileobj(Bucket=bucket_name, Key=object_key, Fileobj=byte_stream)
    byte_stream.seek(0)
    cache_data = pickle.load(byte_stream)
    self.vectors = [np.array(v, dtype=np.float32) for v in cache_data["vectors"]]
    self.questions = cache_data["questions"]
    self.responses = cache_data["responses"]

class PgRetriever: def init(self, vector_store, embed_model, s3_bucket: str, s3_key: str, region: str = "ap-south-1"): self.vector_store = vector_store self.embed_model = embed_model self.semantic_cache = InMemorySemanticCache() self.s3_bucket = s3_bucket self.s3_key = s3_key self.region = region self.logger = logging.getLogger("PgRetriever") self._load_cache() self._start_periodic_s3_save()

def _load_cache(self):
    try:
        self.semantic_cache.load_from_s3(self.s3_bucket, self.s3_key, self.region)
        self.logger.info("Semantic cache loaded from S3.")
    except Exception as e:
        self.logger.warning(f"Could not load cache from S3: {e}")

def _save_cache(self):
    try:
        self.semantic_cache.save_to_s3(self.s3_bucket, self.s3_key, self.region)
        self.logger.info("Semantic cache saved to S3.")
    except Exception as e:
        self.logger.error(f"Could not save cache to S3: {e}")

def _start_periodic_s3_save(self):
    def save_loop():
        while True:
            time.sleep(3600)  # 1 hour
            self._save_cache()

    thread = threading.Thread(target=save_loop, daemon=True)
    thread.start()

def retrieve(self, question: str):
    question_vector = self.embed_model.get_query_embedding(question)

    cached_response = self.semantic_cache.search(question_vector)
    if cached_response:
        self.logger.info("Cache hit")
        return cached_response

    self.logger.info("Cache miss. Querying vector store.")
    response = self.vector_store.similarity_search(question)

    self.semantic_cache.add(question_vector, question, response)
    return response

