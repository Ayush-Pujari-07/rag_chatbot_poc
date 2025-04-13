import asyncio
import traceback
from datetime import datetime, timezone
from typing import List, Union

from bson.objectid import ObjectId
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai.chat_models import ChatOpenAI

from backend.chat.schemas import AllChatMessage, ChatMessage, ChatMessageOut, ChatRole
from backend.config import settings
from backend.logger import logger

GPT4 = "gpt-4o-mini"


class Chat:
    def __init__(self, user_id: str, db):
        self.db = db
        self.user_id = ObjectId(user_id)
        self.messages: List[ChatMessage] = []
        self.chat_model = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=GPT4)

    async def get_messages(self):
        async with self.db.chat_messages.find({"user_id": self.user_id}) as cursor:
            return await cursor.sort("created_at", 1).to_list(length=None)

    async def initialize_task_chat(
        self,
    ) -> ChatMessageOut:
        try:
            user_name_task = self.db.users.find_one({"_id": self.user_id}, {"name": 1})
            # user_data_task = self.db.user_data.find_one(
            #     {"user_id": self.user_id}, {"pdf_data": 1}
            # )

            user_name = await asyncio.gather(user_name_task)

            system_prompt = (
                "You are a conversational AI assistant for Personal Assistance. You are designed to help user {user_name} who's data is '{user_data}' with their goals. You are capable of providing personalized advice and support on a variety of topics. You are also capable of providing information on various programs and products. You are designed to be a helpful and supportive resource for users in their journey. Dont give reply to anything thats not in the user data."
            ).format(user_name=user_name[0]["name"], user_data="")

            message = await self.add_system_message(
                content=system_prompt,
                commit=True,
            )

            message_history = await self.get_message_history()

            completion = await self.chat_model.ainvoke(message_history)
            message = await self.add_assistant_message(
                content=str(completion.content), commit=True
            )

            return ChatMessageOut(
                id=str(message["_id"]),
                role=message["role"],
                content=message["content"],
                created_at=message["created_at"],
                updated_at=message["updated_at"],
            )
        except Exception:
            logger.error(f"Error: {traceback.format_exc()}")
            raise

    async def add_message(
        self,
        role: str,
        content: str,
        commit: bool = False,
    ):
        try:
            datetime_now = datetime.now(timezone.utc)
            message = {
                "user_id": self.user_id,
                "role": role,
                "content": content,
                "created_at": datetime_now,
                "updated_at": datetime_now,
            }

            result = await self.db.chat_messages.insert_one(message)
            message["_id"] = result.inserted_id

            if commit:
                await self.db.chat_messages.update_one(
                    {"_id": message["_id"]}, {"$set": message}
                )

            self.messages.append(
                ChatMessage(
                    id=str(message["_id"]),
                    user_id=str(message["user_id"]),
                    role=message["role"],
                    content=message["content"],
                    created_at=message["created_at"],
                    updated_at=message["updated_at"],
                )
            )
            return message

        except Exception:
            logger.error(f"Error adding message: {traceback.format_exc()}")
            raise

    async def add_system_message(self, content: str, commit: bool = True):
        return await self.add_message(role="system", content=content, commit=commit)

    async def add_user_message(self, content: str, commit: bool = True):
        return await self.add_message(role="user", content=content, commit=commit)

    async def add_assistant_message(self, content: str, commit: bool = True):
        return await self.add_message(role="assistant", content=content, commit=commit)

    async def get_all_messages_roles(self):
        messages = (
            await self.db.chat_messages.find({
                "user_id": self.user_id,
                "role": {"$in": [ChatRole.ASSISTANT, ChatRole.USER, ChatRole.SYSTEM]},
            })
            .sort("created_at", 1)
            .to_list(length=None)
        )

        return messages

    async def get_message_history(self):
        message_history: List[Union[HumanMessage, AIMessage, SystemMessage]] = []
        messages = await self.get_all_messages_roles()
        for message in messages:
            if message["role"] == "user":
                message_history.append(HumanMessage(content=message["content"]))
            elif message["role"] == "assistant":
                message_history.append(AIMessage(content=message["content"]))
            elif message["role"] == "system":
                message_history.append(SystemMessage(content=message["content"]))
        return message_history

    async def task_chat(
        self,
        user_message: str,
    ) -> ChatMessageOut:
        try:
            await self.add_user_message(content=user_message)
            message_history = await self.get_message_history()
            message = await self.process_completion(message_history)

            return ChatMessageOut(
                id=str(message["_id"]),
                role=message["role"],
                content=message["content"],
                created_at=message["created_at"],
                updated_at=message["updated_at"],
            )

        except Exception:
            logger.error(f"Error: {traceback.format_exc()}")
            raise

    async def process_completion(self, message_history):
        try:
            completion = await asyncio.wait_for(
                self.chat_model.ainvoke(message_history), timeout=30
            )
            return await self.add_assistant_message(
                content=str(completion.content), commit=True
            )
        except asyncio.TimeoutError:
            logger.error("OpenAI API call timed out")
            raise
        except Exception:
            logger.error(f"Error processing completion: {traceback.format_exc()}")
            raise

    async def get_all_messages(self) -> AllChatMessage:
        messages = (
            await self.db.chat_messages.find({
                "user_id": self.user_id,
                "role": {"$in": [ChatRole.ASSISTANT, ChatRole.USER]},
            })
            .sort("created_at", 1)
            .to_list(length=None)
        )
        return AllChatMessage(
            all_messages=[
                ChatMessageOut(
                    id=str(message["_id"]),
                    role=message["role"],
                    content=message["content"],
                    created_at=message["created_at"],
                    updated_at=message["updated_at"],
                )
                for message in messages
                if message["role"] in [ChatRole.ASSISTANT, ChatRole.USER]
            ]
        )
