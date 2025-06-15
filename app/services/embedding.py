from sentence_transformers import SentenceTransformer
from threading import Lock

class EmbeddingService:
    _instance = None
    _lock = Lock()
    model: SentenceTransformer

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(EmbeddingService, cls).__new__(cls)
                    cls._instance.model = SentenceTransformer('mixedbread-ai/mxbai-embed-large-v1')
        return cls._instance

    def get_embedding(self, text):
        """
        Returns the embedding for a single string or a list of strings.
        
        Args:
            text (Union[str, List[str]]): The input text or list of texts to embed
            
        Returns:
            List[float]: The embedding vector(s) as a list of floats
        """
        return self.model.encode(text, show_progress_bar=False).tolist()