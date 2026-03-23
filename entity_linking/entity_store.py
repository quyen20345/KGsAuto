import uuid
from sentence_transformers import SentenceTransformer
from qdrant_client import models, QdrantClient


class EntityDB:
    """
    Vector store for KG entities.
    Simple responsibilities: store, search similar, delete.
    """
    def __init__(self, collection_name: str = "entity_store", encode_model: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self.collection_name = collection_name
        self.encode_model = SentenceTransformer(encode_model, device=device)
        self.qdrant_client = QdrantClient("http://localhost:6333")
        if not self.qdrant_client.collection_exists(collection_name):
            self._init_entity_collection()

    def _init_entity_collection(self):
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.encode_model.get_sentence_embedding_dimension(),
                distance=models.Distance.COSINE,
            ),
        )

    def _make_point_id(self, entity_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, entity_id))

    def _build_text_for_embedding(self, entity: dict) -> str:
        labels = entity.get("labels", [])
        props = entity.get("properties", {})
        name = props.get("name", "")
        aliases = props.get("aliases", [])
        description = props.get("description", "")

        parts = [name]
        if labels:
            parts.append(f"({', '.join(labels)})")
        if aliases:
            parts.append(f"aka {', '.join(aliases)}")
        if description:
            parts.append(f"- {description}")
        return " ".join(parts)

    def upsert_entities(self, entities: list[dict]) -> int:
        points = []
        for entity in entities:
            entity_id = entity.get("id", "")
            if not entity_id:
                continue
            text_embed = self._build_text_for_embedding(entity)
            vector = self.encode_model.encode(text_embed).tolist()
            payload = {
                "entity_id": entity_id,
                "labels": entity.get("labels", []),
                "properties": entity.get("properties", {}),
                "merged_ids": entity.get("merged_ids", []),
            }
            point_id = self._make_point_id(entity_id)
            points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))

        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
        return len(points)

    def search_similar(self, seed_entity: dict, limit: int = 10, score_threshold: float = 0.5) -> list[dict]:
        """Search for entities similar to seed. No filtering — LLM decides."""
        text_embed = self._build_text_for_embedding(seed_entity)
        vector = self.encode_model.encode(text_embed).tolist()
        seed_point_id = self._make_point_id(seed_entity.get("id", ""))

        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit + 1,
            score_threshold=score_threshold,
        ).points

        candidates = []
        for hit in results:
            if hit.id == seed_point_id:
                continue
            candidate = hit.payload
            candidate["_score"] = hit.score
            candidates.append(candidate)
        return candidates[:limit]

    def delete_entities(self, entity_ids: list[str]):
        point_ids = [self._make_point_id(eid) for eid in entity_ids]
        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=point_ids),
        )
        
    def iter_entities(self, batch_size):
        offset = None
        while True:
            points, next_offset = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            for point in points:
                payload = point.payload or {}
                if payload.get("entity_id"):
                    yield payload 
                    
            if next_offset is None:
                break
            
            offset = next_offset
            
    def get_all_entity_ids(self) -> list[str]:
        entity_ids = []
        for entity in self.iter_entities(batch_size=256):
            entity_ids.append(entity.get("entity_id", ""))
        return entity_ids

    # def get_all_entity_ids(self) -> list[str]:
    #     entity_ids = []
    #     offset = None
    #     while True:
    #         points, next_offset = self.qdrant_client.scroll(
    #             collection_name=self.collection_name,
    #             limit=100,
    #             offset=offset,
    #             with_payload=True,
    #             with_vectors=False,
    #         )
    #         for point in points:
    #             entity_ids.append(point.payload.get("entity_id", ""))
    #         if next_offset is None:
    #             break
    #         offset = next_offset
    #     return entity_ids

    def get_entity_by_id(self, entity_id: str) -> dict | None:
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

    def drop_collection(self):
        if self.qdrant_client.collection_exists(self.collection_name):
            self.qdrant_client.delete_collection(self.collection_name)
