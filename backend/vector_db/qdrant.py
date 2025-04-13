import io
import uuid
from datetime import datetime, timezone
from typing import Any

import pdfplumber
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models
from scipy.sparse._matrix import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.config import settings
from backend.logger import logger
from backend.vector_db.schemas import Document, DocumentTypes, UserId
from backend.vector_db.service import RecursiveCharacterTextSplitter


class RagError(Exception):
    """Base exception for RAG operations"""


class BaseUtils:
    retrieval_method = "BASE CLASS"

    async def fetch_raw_responses(
        self, query: str, k: int = 5, query_filter: Any | None = None
    ):
        raise NotImplementedError("This method should be implemented by subclasses.")

    @staticmethod
    def process_raw_response(doc: Any):
        raise NotImplementedError("This method should be implemented by subclasses.")


# TODO: Add functionality for updating the existing collection
class QdrantUtils(BaseUtils):
    def __init__(self, url, api_key):
        self.retrieval_method = "QDRANT"
        self.url = url
        self.api_key = api_key
        self.qdrant_client = AsyncQdrantClient(url=url, api_key=api_key)
        self.openai_client = AsyncOpenAI(api_key=str(settings.OPENAI_API_KEY))

    async def delete_collection(self, collection_name: str) -> bool:
        try:
            await self.qdrant_client.delete_collection(collection_name=collection_name)
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False

    async def create_collection(
        self,
        collection_name: str,
        distance_strategy: str = "COSINE",
    ) -> bool:
        try:
            if not await self.qdrant_client.collection_exists(collection_name):
                hnsw_config = models.HnswConfigDiff(
                    m=16,
                    ef_construct=100,
                    full_scan_threshold=10000,
                    max_indexing_threads=0,
                    on_disk=False,
                )
                dense_vector_params = models.VectorParams(
                    size=1536,
                    distance=getattr(models.Distance, distance_strategy),
                )
                sparse_vector_params = models.SparseVectorParams(
                    index=models.SparseIndexParams(
                        on_disk=False,
                    )
                )
                await self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config={
                        "dense_vector": dense_vector_params,
                    },
                    sparse_vectors_config={
                        "sparse_vector": sparse_vector_params,
                    },
                    hnsw_config=hnsw_config,
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return False

    async def update_repository_doc_metadata(
        self,
        repository_update_request: dict[str, Any],
        user_id: UserId,
        collection_name: str = settings.QDRANT_COLLECTION_NAME,
    ) -> bool:
        try:
            qdrant_res = await self.qdrant_client.scroll(
                collection_name=f"{collection_name}",
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.document_id",
                            match=models.MatchValue(
                                value=str(repository_update_request["document_id"])
                            ),
                        ),
                        models.FieldCondition(
                            key="metadata.user_id",
                            match=models.MatchValue(value=user_id.user_id),
                        ),
                        models.FieldCondition(
                            key="metadata.document_type",
                            match=models.MatchValue(
                                value=DocumentTypes.REPOSITORY_DOCUMENT.value
                            ),
                        ),
                    ]
                ),
                with_payload=True,
                with_vectors=False,
            )
            # TODO: Need to check a better way to update metadata
            existing_metadata_to_be_updated = qdrant_res[0][0].payload["metadata"]  # type: ignore
            existing_metadata_to_be_updated.update({
                "title": repository_update_request["metadata"].get("title", ""),
                "location": repository_update_request["metadata"].get("location", ""),
                "type": repository_update_request["metadata"].get("type", ""),
                "activity": repository_update_request["metadata"].get("activity", ""),
                "sub_activity": repository_update_request["metadata"].get(
                    "sub_activity", ""
                ),
                "uploader_name": repository_update_request["uploader_name"],
                "uploader_id": str(repository_update_request["uploader_id"]),
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            })
            await self.qdrant_client.set_payload(
                collection_name=f"{collection_name}",
                points=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.document_id",
                            match=models.MatchValue(
                                value=str(repository_update_request["document_id"])
                            ),
                        ),
                        models.FieldCondition(
                            key="metadata.user_id",
                            match=models.MatchValue(value=user_id.user_id),
                        ),
                        models.FieldCondition(
                            key="metadata.document_type",
                            match=models.MatchValue(
                                value=DocumentTypes.REPOSITORY_DOCUMENT.value
                            ),
                        ),
                    ]
                ),
                payload={"metadata": existing_metadata_to_be_updated},
            )
            return True
        except Exception as e:
            logger.error(f"Error updating metadata in qdrant: {e}")
            return False

    async def add_document_to_collection(
        self, collection_name: str, documents: list[Document]
    ) -> bool:
        try:
            if isinstance(documents, list):
                points = [
                    models.PointStruct(
                        id=str(document.id),
                        vector={
                            "sparse_vector": document.sparse_vector
                            if document.sparse_vector
                            else models.SparseVector(indices=[], values=[]),
                            "dense_vector": document.dense_vector
                            if document.dense_vector
                            else [],
                        },
                        payload={
                            "source": document.source,
                            "excerpt": document.excerpt,
                            "excerpt_page_number": document.excerpt_page_number,
                            "title": document.title,
                            "metadata": document.metadata,
                        },
                    )
                    for document in documents
                ]

                await self.qdrant_client.upsert(
                    collection_name=collection_name, points=points
                )
                return True
            logger.error("Documents should be a list of Document instances.")
            return False
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False

    async def document_ingestion(
        self,
        collection_name: str,
        filename: str,
        file_content: bytes,
        metadata: dict,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] = ["\n"],
    ):
        buf = io.BytesIO(file_content)

        # Process the PDF
        pdf_data = pdfplumber.open(buf)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=separators
        )
        documents = []
        for page in pdf_data.pages:
            page_text = page.extract_text()
            chunks = text_splitter.split_text(page_text)
            for chunk in chunks:
                documents.append({
                    "source": filename,
                    "title": filename,
                    "excerpt": chunk,
                    "excerpt_page_number": page.page_number,
                    "metadata": metadata,
                })
        final_data = await self.create_point(documents)

        if not await self.qdrant_client.collection_exists(collection_name):
            await self.create_collection(collection_name=collection_name)

        if final_data:
            await self.add_document_to_collection(
                collection_name=collection_name, documents=final_data
            )
        logger.info(f"File {filename} uploaded.")

    async def search_documents(
        self,
        collection_name: str,
        query: str,
        k: int = 5,
        query_filter: models.Filter | None = None,
    ) -> list[models.ScoredPoint]:
        try:
            response = await self.qdrant_client.query_points(
                collection_name=collection_name,
                prefetch=[
                    models.Prefetch(
                        query=await self.create_sparse_vector([query]),
                        using="sparse_vector",
                        limit=k,
                    ),
                    models.Prefetch(
                        query=await self.create_embedding(query),
                        using="dense_vector",
                        limit=k,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.DBSF),
                query_filter=query_filter,
                score_threshold=0.7,
            )
            return response.points
        except Exception as e:
            logger.error(f"Error searching documents with Qdrant: {e}")
            return []

    async def create_point(self, data: list[dict[str, Any]]) -> list[Document] | None:
        try:
            documents = []
            for item in data:
                if item["excerpt"]:
                    dense_vector = await self.create_embedding(item["excerpt"])
                    sparse_vector = await self.create_sparse_vector([item["excerpt"]])

                    document = Document(
                        id=str(uuid.uuid4()),
                        title=item["title"],
                        source=item["source"],
                        excerpt=item["excerpt"],
                        excerpt_page_number=int(item["excerpt_page_number"]),
                        dense_vector=dense_vector,
                        sparse_vector=sparse_vector,
                        metadata=item.get("metadata"),
                    )
                    documents.append(document)
            return documents
        except Exception as e:
            logger.error(f"Error creating point: {e}")
            return None

    async def create_embedding(self, query: str) -> list[float]:
        try:
            embedding = await self.openai_client.embeddings.create(
                input=query, model="text-embedding-3-small"
            )
            return embedding.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return []

    async def create_sparse_vector(
        self, corpus: list[str]
    ) -> models.SparseVector | None:
        try:
            vectorizer = TfidfVectorizer(
                lowercase=True,
                max_features=10000,
                stop_words="english",
            )
            sparse_matrix: spmatrix = vectorizer.fit_transform(corpus)
            indices = sparse_matrix.indices.tolist()  # type: ignore
            values = sparse_matrix.data.tolist()  # type: ignore
            return models.SparseVector(indices=indices, values=values)
        except Exception as e:
            logger.error(f"Error creating sparse vector: {e}")
            return None

    async def delete_document_from_collection(
        self,
        doc_id: str,
        user_id: UserId,
        collection_name: str = settings.QDRANT_COLLECTION_NAME,
    ) -> None:
        try:
            await self.qdrant_client.delete(
                collection_name=collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.document_id",
                            match=models.MatchValue(value=doc_id),
                        ),
                        models.FieldCondition(
                            key="metadata.user_id",
                            match=models.MatchValue(value=user_id.user_id),
                        ),
                    ]
                ),
            )
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Failed to delete document: {e!s}")
