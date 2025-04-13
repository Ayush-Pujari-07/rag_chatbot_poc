from enum import Enum
from typing import Any

from pydantic import BaseModel
from qdrant_client import models


class DocumentTypes(Enum, str):
    REPOSITORY_DOCUMENT = "Repository Document"
    PROJECT_DOCUMENT = "Project Document"


class UserId(BaseModel):
    user_id: str


class DocumentProcessingStatus(Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    DONE = "Done"
    FAILED = "Failed"


class Document(BaseModel):
    id: str
    source: str
    title: str
    excerpt: str
    excerpt_page_number: int
    dense_vector: list[float] | Any | None = None
    sparse_vector: models.SparseVector | Any | None = None
    metadata: dict[str, Any] | None = None
