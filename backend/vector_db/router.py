from auth.dependencies import valid_refresh_token
from auth.schemas import ValidateRefreshTokenResponse
from config import settings
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from logger import logger
from vector_db.qdrant import QdrantUtils
from vector_db.schemas import DocumentTypes, UserId

router = APIRouter()
qdrant_client = QdrantUtils(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


@router.post("/collection/create")
async def create_collection(
    user: ValidateRefreshTokenResponse = Depends(valid_refresh_token),
    collection_name: str = Body(..., embed=True),
    distance_strategy: str = Body(default="COSINE", embed=True),
) -> JSONResponse:
    try:
        result = await qdrant_client.create_collection(
            collection_name=collection_name, distance_strategy=distance_strategy
        )
        if result:
            return JSONResponse(
                content={
                    "message": f"Collection {collection_name} created successfully"
                },
                status_code=201,
            )
        return JSONResponse(
            content={"message": f"Collection {collection_name} already exists"},
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create collection: {str(e)}"
        )


@router.delete("/collection/{collection_name}")
async def delete_collection(
    collection_name: str,
    user: ValidateRefreshTokenResponse = Depends(valid_refresh_token),
) -> JSONResponse:
    try:
        result = await qdrant_client.delete_collection(collection_name=collection_name)
        if result:
            return JSONResponse(
                content={
                    "message": f"Collection {collection_name} deleted successfully"
                },
                status_code=200,
            )
        return JSONResponse(
            content={"message": f"Failed to delete collection {collection_name}"},
            status_code=400,
        )
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete collection: {str(e)}"
        )


@router.post("/document/upload")
async def upload_document(
    collection_name: str = Body(default=settings.QDRANT_COLLECTION_NAME),
    document_type: DocumentTypes = Body(default=DocumentTypes.PROJECT_DOCUMENT),
    file: UploadFile = File(...),
    user: ValidateRefreshTokenResponse = Depends(valid_refresh_token),
) -> JSONResponse:
    try:
        if not str(file.filename).endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        file_content = await file.read()
        metadata = {
            "document_id": str(file.filename),
            "user_id": user.user_id,
            "document_type": document_type.value,
            "file_name": file.filename,
        }

        await qdrant_client.document_ingestion(
            collection_name=collection_name,
            filename=str(file.filename) if file.filename else "",
            file_content=file_content,
            metadata=metadata,
        )

        return JSONResponse(
            content={"message": f"Document {file.filename} uploaded successfully"},
            status_code=201,
        )
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to upload document: {str(e)}"
        )


@router.delete("/document/{document_id}")
async def delete_document(
    document_id: str,
    user: ValidateRefreshTokenResponse = Depends(valid_refresh_token),
    collection_name: str = settings.QDRANT_COLLECTION_NAME,
) -> JSONResponse:
    try:
        await qdrant_client.delete_document_from_collection(
            doc_id=document_id,
            user_id=UserId(user_id=user.user_id),
            collection_name=collection_name,
        )
        return JSONResponse(
            content={"message": f"Document {document_id} deleted successfully"},
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete document: {str(e)}"
        )


# TODO: Update the function to perform proper search on the file (To Test the search), This is to test the Query search accuracy
@router.post("/search")
async def search_documents(
    query: str = Body(..., embed=True),
    k: int = Body(default=5, embed=True),
    collection_name: str = Body(default=settings.QDRANT_COLLECTION_NAME, embed=True),
    user: ValidateRefreshTokenResponse = Depends(valid_refresh_token),
) -> JSONResponse:
    try:
        results = await qdrant_client.search_documents(
            collection_name=collection_name, query=query, k=k
        )
        return JSONResponse(
            content={"results": [result.dict() for result in results]}, status_code=200
        )
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search documents: {str(e)}"
        )
