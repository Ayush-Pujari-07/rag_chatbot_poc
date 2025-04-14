import os
import traceback
import uuid
from typing import Any

import pymupdf
import pymupdf4llm
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models
from scipy.sparse._matrix import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.config import settings
from backend.logger import logger
from backend.vector_db.schemas import Document, UserId


class RagError(Exception):
    """Base exception for RAG operations"""


# TODO: Add functionality for updating the existing collection
class QdrantUtils:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
        self.qdrant_client = AsyncQdrantClient(url=url, api_key=api_key)
        self.openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
        except Exception:
            logger.error(f"Error creating collection: {traceback.format_exc()}")
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
    ):
        print(f"File name: {filename}")
        print(f"Metadata: {metadata}")

        # Open the PDF document from the byte stream
        doc = pymupdf.open(stream=file_content, filetype="pdf")

        # Process the PDF
        pdf_data = pymupdf4llm.to_markdown(doc, page_chunks=True, extract_words=True)
        documents = []
        for page in pdf_data:
            documents.append({
                "source": filename,
                "title": filename,
                "excerpt": " ".join([word[4] for word in page["words"]]),  # type: ignore
                "excerpt_page_number": page["metadata"]["page"],  # type: ignore
                "metadata": metadata,
            })
        print(f"Documents: {documents}")

        final_data = await self.create_point(documents)

        if not await self.qdrant_client.collection_exists(collection_name):
            await self.create_collection(collection_name=collection_name)

        if final_data:
            await self.add_document_to_collection(
                collection_name=collection_name, documents=final_data
            )
        logger.info(f"File {filename} uploaded.")

    # TODO: Check with adding diffrent filters
    async def search_documents(
        self,
        collection_name: str,
        query: str,
        k: int = 5,
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
                search_params=models.SearchParams(exact=True, hnsw_ef=128),
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
                input=query, model="text-embedding-3-small", dimensions=1536
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
