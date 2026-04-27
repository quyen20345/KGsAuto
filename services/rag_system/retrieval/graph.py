"""Graph retrieval"""

from typing import List, Dict, Any

from services.rag_system.storage import GraphStore


class GraphRetriever:
    """Retrieve relevant entities and relationships from knowledge graph"""

    def __init__(self, config):
        self.config = config

    def retrieve(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        if top_k is None:
            top_k = self.config.top_k_graph

        store = GraphStore(self.config)
        facts: List[Dict[str, Any]] = []

        keywords = self._extract_keywords(query)
        entities = []
        seen_ids = set()

        for keyword in keywords:
            results = store.search_entities(keyword, limit=3)
            for entity in results:
                if entity['id'] not in seen_ids:
                    entities.append(entity)
                    seen_ids.add(entity['id'])

        for entity in entities[:3]:
            entity_id = entity['id']
            entity_name = entity['name']

            details = store.get_entity_details(entity_id)
            if details:
                labels_str = ', '.join(details['labels'])
                properties = details.get('properties', {})
                descriptions = properties.get('description', []) or []
                description_text = descriptions[0] if descriptions else None
                fact_text = description_text or f"{entity_name} là {labels_str}"
                facts.append(
                    {
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "fact_type": "property",
                        "fact_text": fact_text,
                        "score": 0.9 if query.lower() in entity_name.lower() else 0.8,
                        "metadata": properties,
                    }
                )

                chunk_ids = properties.get('chunk_id', []) or []
                if chunk_ids:
                    facts[-1]["metadata"]["source_chunk_ids"] = chunk_ids

            rels = store.get_relationships(entity_id, depth=1, limit=5)
            for rel in rels:
                facts.append(
                    {
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "fact_type": "relation",
                        "fact_text": f"{rel['source']} {rel['relation']} {rel['target']}",
                        "score": 0.7,
                        "metadata": rel.get('rel_props', {}),
                    }
                )

        facts.sort(key=lambda x: x['score'], reverse=True)
        return facts[:top_k]

    def _extract_keywords(self, query: str) -> List[str]:
        stop_words = {'là', 'của', 'các', 'có', 'được', 'này', 'đó', 'cho', 'và', 'với'}
        words = query.lower().split()
        return [w for w in words if len(w) > 2 and w not in stop_words]
