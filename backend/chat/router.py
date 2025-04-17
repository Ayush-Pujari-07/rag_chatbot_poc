from auth import dependencies as auth_deps
from auth.schemas import ValidateRefreshTokenResponse
from chat.chat import Chat
from chat.schemas import AllChatMessage, ChatMessageOut
from db import get_db
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from logger import logger

router = APIRouter()


# On event startup
@router.on_event("startup")
async def create_index():
    db = get_db()
    await db.chat_messages.create_index([("user_id", 1)])


@router.post("/chat/start")
async def create_chat(
    user_id: ValidateRefreshTokenResponse = Depends(auth_deps.valid_refresh_token),
    db=Depends(get_db),
) -> ChatMessageOut:
    try:
        chat = Chat(user_id=user_id.user_id, db=db)
        return await chat.initialize_task_chat()

    except Exception as e:
        logger.error(f"Error creating chat: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while creating the chat.",
        ) from e


@router.post("/chat")
async def add_message_to_chat(
    request: Request,
    message: str = Body(..., embed=True),
    user_id: ValidateRefreshTokenResponse = Depends(auth_deps.valid_refresh_token),
    db=Depends(get_db),
) -> ChatMessageOut:
    try:
        chat = Chat(user_id=user_id.user_id, db=db)
        return await chat.task_chat(user_message=message)

    except Exception as e:
        logger.error(f"Error adding message to chat: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while adding the message to the chat.",
        ) from e


@router.get("/allChat")
async def get_all_chat(
    user_id: ValidateRefreshTokenResponse = Depends(auth_deps.valid_refresh_token),
    db=Depends(get_db),
) -> AllChatMessage:
    try:
        chat = Chat(user_id=user_id.user_id, db=db)
        return await chat.get_all_messages()

    except Exception as e:
        logger.error(f"Error fetching all chats: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching all chats.",
        ) from e
