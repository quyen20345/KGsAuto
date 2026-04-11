from pydantic import BaseModel


class QueryModel(BaseModel):
    cypher: str
