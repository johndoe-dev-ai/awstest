from llama_index.core.memory import ChatMemoryBuffer, VectorMemory, SimpleComposableMemory
from llama_index.embeddings.bedrock import BedrockEmbedding
from typing import List, Dict, Optional
import logging

class Logger:
    def get_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

class AgentMemory:
    """Class to handle agent memory with enhanced capabilities"""
    
    def __init__(self):
        self.logger = Logger().get_logger()
        self.logger.info("Initializing agent memory")
        self.embedding_model = 'amazon.titan-embed-text-v2:0'  # Fixed typo in model name
        self.region_name = "eu-west-1"
        self.chat_memory_buffer = ChatMemoryBuffer.from_defaults()
        # Initialize embeddings and vector memory at creation time
        self._embed_model = None
        self._vector_memory = None
        self._composable_memory = None

    def embeddings(self) -> BedrockEmbedding:
        """Initialize and return the embedding model"""
        if self._embed_model is None:
            self.logger.info("Initializing embedding model")
            self._embed_model = BedrockEmbedding(
                model_name=self.embedding_model,
                region_name=self.region_name
            )
        return self._embed_model

    def vector_memory(self) -> VectorMemory:
        """Initialize and return the vector memory"""
        if self._vector_memory is None:
            self.logger.info("Initializing vector memory")
            self._vector_memory = VectorMemory.from_defaults(
                embed_model=self.embeddings(),
                retrieve_kwargs={'similarity_top_k': 5},
            )
        return self._vector_memory

    def composable_memory(self) -> SimpleComposableMemory:
        """Initialize and return composable memory for the agent"""
        if self._composable_memory is None:
            self.logger.info("Initializing composable memory")
            self._composable_memory = SimpleComposableMemory(
                primary_memory=self.chat_memory_buffer,
                secondary_memory_sources=[self.vector_memory()]
            )
        return self._composable_memory

    def remove_last_n(self, n: int = 2) -> bool:
        """
        Remove last n messages from composable memory
        Args:
            n: Number of messages to remove (default 2 for user+assistant pair)
        Returns:
            bool: True if messages were removed, False otherwise
        """
        try:
            memory = self.composable_memory()
            current_messages = memory.get()["memory"]
            
            if len(current_messages) >= n:
                self.logger.info(f"Removing last {n} messages from memory")
                # Create new memory instance
                new_memory = SimpleComposableMemory(
                    primary_memory=self.chat_memory_buffer,
                    secondary_memory_sources=[self.vector_memory()]
                )
                
                # Re-add all messages except the last n
                for msg in current_messages[:-n]:
                    new_memory.put(msg)
                
                # Update the composable memory reference
                self._composable_memory = new_memory
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing messages: {str(e)}")
            return False

    def clear_memory(self) -> None:
        """Completely clear the agent's memory"""
        self.logger.info("Clearing all memory")
        self._composable_memory = None
        self.chat_memory_buffer = ChatMemoryBuffer.from_defaults()
        # Note: Vector memory persists as it's based on embeddings
