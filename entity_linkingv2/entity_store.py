import uuid
from typing import Optional
 
from sentence_transformers import SentenceTransformer
from qdrant_client import models, QdrantClient


class EntityDB:
    """
    Vector store for KG entities backed by Qdrant.
    """
 
    def __init__(
        self,
        collection_name: str = "entity_store",
        encode_model:    str = "all-MiniLM-L6-v2",
        device:          str = "cpu",
    ):
        self.collection_name = collection_name
        self.encode_model    = SentenceTransformer(encode_model, device=device)
        self.qdrant_client   = QdrantClient("http://localhost:6333")
        if not self.qdrant_client.collection_exists(collection_name):
            self._init_entity_collection()
            
    # Collection init.
    def _init_entity_collection(self):
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.encode_model.get_sentence_embedding_dimension(),
                distance=models.Distance.COSINE,
            ),
        )
        
    # id helper.
    def _make_point_id(self, entity_id: str) -> str:
        """
        UUID5 from entity_id — same entity always gets the same point ID,
        making upsert idempotent across runs.
        """
        return str(uuid.uuid5(uuid.NAMESPACE_URL, entity_id))
    
    
    # Embedding
    def _build_text_for_embedding(self, entity: dict) -> str:
        """Concatenate salient fields into a single searchable string."""
        labels      = entity.get("labels", [])
        props       = entity.get("properties", {})
        name        = props.get("name", "")
        aliases     = props.get("aliases", [])
        description = props.get("description", "")
 
        parts = [name]
        if labels:
            parts.append(f"({', '.join(labels)})")
        if aliases:
            parts.append(f"aka {', '.join(aliases)}")
        if description:
            parts.append(f"- {description}")
        return " ".join(filter(None, parts))
    
    
    # Write
    def upsert_entities(self, entities: list[dict]) -> int:
        """
        Upsert entities into Qdrant.
        Generates a fresh embedding for each entity.
        Returns the number of points upserted.
        """
        points = []
        for entity in entities:
            entity_id = entity.get("id") or entity.get("entity_id", "")
            if not entity_id:
                continue
 
            text   = self._build_text_for_embedding(entity)
            vector = self.encode_model.encode(text).tolist()
 
            payload = {
                "entity_id":  entity_id,
                "labels":     entity.get("labels", []),
                "properties": entity.get("properties", {}),
                "merged_ids": entity.get("merged_ids", []),
            }
            points.append(
                models.PointStruct(
                    id=self._make_point_id(entity_id),
                    vector=vector,
                    payload=payload,
                )
            )
 
        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
        return len(points)
    
    
    def delete_entities(self, entity_ids: list[str]):
        """Batch-delete entities by their entity_id strings."""
        point_ids = [self._make_point_id(eid) for eid in entity_ids]
        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=point_ids),
        )
        
        
    # Read
    def search_similar(
        self,
        seed_entity:     dict,
        limit:           int            = 10,
        score_threshold: float          = 0.5,
        label_filter:    Optional[str]  = None,
    ) -> list[dict]:
        """
        Search for entities similar to seed_entity by vector cosine similarity.
 
        Args:
            label_filter: If provided, restrict results to entities that contain
                          this label in their 'labels' array. Pass the primary
                          label string (e.g. "PERSON"). None = no filter.
 
        Returns:
            List of candidate payloads (with '_score' field appended),
            sorted by descending similarity, excluding the seed itself.
        """
        text   = self._build_text_for_embedding(seed_entity)
        vector = self.encode_model.encode(text).tolist()
        seed_point_id = self._make_point_id(seed_entity.get("entity_id", "")
                                            or seed_entity.get("id", ""))
 
        # Build optional Qdrant filter for label
        query_filter = None
        if label_filter:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="labels",
                        match=models.MatchAny(any=[label_filter]),
                    )
                ]
            )
 
        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit + 1,        # +1 to account for self being returned
            score_threshold=score_threshold,
            query_filter=query_filter,
        ).points
 
        candidates = []
        for hit in results:
            if hit.id == seed_point_id:
                continue
            payload = dict(hit.payload)
            payload["_score"] = hit.score
            candidates.append(payload)
 
        return candidates[:limit]
    
    
    def iter_entities(self, batch_size: int = 256):
        """
        Iterate over all entities using Qdrant scroll (efficient pagination).
        Yields one entity payload at a time.
        """
        offset = None
        while True:
            points, next_offset = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                if payload.get("entity_id"):
                    yield payload
 
            if next_offset is None:
                break
            offset = next_offset
            
            
    def get_entity_by_id(self, entity_id: str) -> dict | None:
        """Fetch a single entity payload by its entity_id."""
        point_id = self._make_point_id(entity_id)
        try:
            points = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True,
            )
            if points:
                return points[0].payload
        except Exception:
            pass
        return None
 
    def get_all_entity_ids(self) -> list[str]:
        """Return all entity_ids in the collection."""
        return [
            e["entity_id"]
            for e in self.iter_entities(batch_size=256)
            if e.get("entity_id")
        ]
 
    def count(self) -> int:
        """Return total number of entities in collection."""
        return self.qdrant_client.count(self.collection_name).count
    
    
    def drop_collection(self):
        """Drop the entire collection. Use with caution."""
        if self.qdrant_client.collection_exists(self.collection_name):
            self.qdrant_client.delete_collection(self.collection_name)