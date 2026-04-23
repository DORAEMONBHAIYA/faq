import faiss
import numpy as np

class FAISSStore:
    def __init__(self, dim=None):
        self.index = None
        self.dim = dim
        self.metadata = []

    def _init_index(self, dim):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)

    def add(self, embeddings, chunks):
        if not embeddings:
            return
            
        emb_array = np.array(embeddings).astype("float32")
        
        # Auto-initialize dimension on first add
        if self.index is None:
            self._init_index(emb_array.shape[1])
            
        self.index.add(emb_array)
        self.metadata.extend(chunks)

    def search(self, query_embedding, top_k=5):
        if self.index is None:
            return []
            
        query_array = np.array([query_embedding]).astype("float32")
        D, I = self.index.search(query_array, top_k)
        
        # Filter out invalid indices
        valid_results = []
        for i in I[0]:
            if i != -1 and i < len(self.metadata):
                valid_results.append(self.metadata[i])
        return valid_results
