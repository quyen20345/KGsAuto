import uuid
from sentence_transformers import SentenceTransformer
from qdrant_client import models, QdrantClient

class entity_db:
    """
    target of vectordb to store entities, after finding these semantic clusters to canonicalize them into one.
    """
    def __init__(self, collection_name: str="entity_store", encode_model: str="all-MiniLM-L6-v2", device: str="gpu"):
        self.collection_name = collection_name
        self.encode_model = SentenceTransformer(encode_model, device) # use cpu if your divice doesn't have gpu.
        self.qdrant_client = QdrantClient("http://localhost:6333")
        if not self.qdrant_client.collection_exists(collection_name): self._init_entity_collection()
        
    def _init_entity_collection(self):
        """
        Initializes the collection with specified configuration.
        this method is called if the collection doesn't already exist.
        """
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.encode_model.get_sentence_embedding_dimension(), # vector size is defined by used model
                distance=models.Distance.COSINE
            )
        )
    
    def upsert_entity(self, entities):
        """
        upserts entities into db.
        """
        points = []
        for entity in entities:
            text_embed = entity + " dieu chinh entity de lam vector dai dien"
            vector = self.encode_model.encode(text_embed)
            payload = {
                
            }
            point_id = " "
            point = models.PointStruct(
                id=point_id, vector=vector, payload=payload
            )
            points.append(point)
        self.qdrant_client.upsert( # upload_points da loi thoi
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )  
    
    def search_entity(self):
        pass
    
    def delete_entity(self):
        pass 
    
    def get_all_entities(self):
        pass