import asyncio
import traceback
from datetime import datetime, timezone
from typing import List, Union

from bson.objectid import ObjectId
from chat.schemas import AllChatMessage, ChatMessage, ChatMessageOut, ChatRole
from config import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages.base import BaseMessage
from langchain_openai.chat_models import ChatOpenAI
from logger import logger
from vector_db.qdrant import QdrantUtils

GPT4 = "gpt-4o"


class Chat:
    def __init__(self, user_id: str, db):
        self.db = db
        self.user_id = ObjectId(user_id)
        self.qdrant_client = QdrantUtils(
            url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY
        )
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

            # TODO: Improve the System prompt for better response.
            system_prompt = (
                "You are a specialized AI Conversational Assistant focused on health insurance plans and eligibility requirements. "
                "Greet the user by their name and ask for their question.\n\n"
                "User_name: {user_name}\n"
                "Knowledge_cutoff: 2023-10-01\n"
                f"Current date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
                "### Your Primary Role:\n"
                "- Provide detailed information about supported insurance plans.\n"
                "- Assess eligibility requirements for all plan types.\n"
                "- Determine how medical conditions affect coverage.\n"
                "- Clarify users' medical history through conversation.\n"
                "- Explain plan types, coverage, and codes.\n"
                "- Outline 5-year medical history requirements.\n\n"
                "### Response Protocol:\n"
                "1. ALWAYS check the provided `knowledge-base` context before answering.\n"
                "2. Use the context and message history to craft accurate responses.\n"
                "3. If information is unavailable, respond: 'I don't have enough information to answer this question accurately.'\n"
                "4. For questions outside plan coverage and eligibility, respond: 'I can only answer questions about supported insurance plans and their eligibility requirements.'\n"
                "5. When discussing ineligibility, list ALL specific plans affected.\n"
                "6. Provide plan-specific details when available in the context.\n\n"
                "### Disqualifying Conditions (5-year history):\n"
                "- Cancer, heart disease, heart attacks, bypass surgery, strokes.\n"
                "- Autoimmune disorders (e.g., Lupus, MS).\n"
                "- Blood disorders (e.g., Anemia, AIDS, HIV, Hemophilia).\n"
                "- Organ failure, transplants, or dialysis.\n"
                "- Current pregnancy.\n"
                "- Hospitalization history.\n"
                "- Respiratory disorders (e.g., Emphysema, COPD).\n"
                "- Musculoskeletal disorders.\n"
                "- Substance abuse or dependency.\n"
                "- Type 1 Diabetes.\n"
                "- Major surgeries (past or planned).\n\n"
                "### `knowledge-base` Context:\n"
            ).format(user_name=user_name[0]["name"])

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

    async def format_query_for_vector_search(
        self,
        query: str,
    ) -> BaseMessage:
        # Improved System Prompt for Vector Search
        system_prompt = """You are tasked with formatting user queries for semantic vector search in Qdrant DB.
        Follow these guidelines to ensure the query is optimized for accurate vector similarity matching:

        ### Guidelines:
        1. Retain all medical terms and conditions exactly as stated in the query.
        2. Preserve specific plan names, numbers, and identifiers without modification.
        3. Maintain temporal references (e.g., "current", "past 5 years") as they appear in the query.
        4. Avoid adding or inferring information not explicitly present in the original query.
        5. Ensure the output is concise, clear, and suitable for vector similarity search.

        ### Example:
        **Input:**
        "Can someone with a history of heart disease in the last 3 years get America's Choice 2500 Gold plan?"

        **Output:**
        "heart disease medical history 3 years eligibility America's Choice 2500 Gold plan"
        """
        return await self.chat_model.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=query)],
        )

    async def task_chat(
        self,
        user_message: str,
    ) -> ChatMessageOut:
        try:
            # Add user message and get conversation history
            await self.add_user_message(content=user_message)
            message_history = await self.get_message_history()

            # Format query and perform vector search
            formatted_query = await self.format_query_for_vector_search(user_message)
            documents = await self.qdrant_client.search_documents(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query=str(formatted_query.content),
            )

            # Process retrieved documents
            if not documents:
                logger.warning(
                    f"No relevant documents found for query: {formatted_query.content}"
                )

            context = []
            for idx, doc in enumerate(documents):
                if not doc.payload:
                    continue
                context.append(
                    f"[{idx + 1}] title: {doc.payload.get('title', 'No title')} "
                    f"content: {doc.payload.get('excerpt', 'No content')}"
                )

            # Update system message with new context
            if context:
                system_message = next(
                    (msg for msg in message_history if isinstance(msg, SystemMessage)),
                    None,
                )
                if system_message:
                    updated_content = (
                        str(system_message.content) + "\n".join(context) + "\n"
                    )
                    message_history[0] = SystemMessage(content=updated_content)

            # Log relevant information for debugging
            logger.info({
                "user_message": user_message,
                "formatted_query": formatted_query.content,
                "context_count": len(context),
                "message_history_length": len(message_history),
                "message_history": message_history,
            })

            # Generate and process completion
            message = await self.process_completion(message_history)

            return ChatMessageOut(
                id=str(message["_id"]),
                role=message["role"],
                content=message["content"],
                created_at=message["created_at"],
                updated_at=message["updated_at"],
            )

        except Exception as e:
            logger.error(f"Error in task_chat: {str(e)}\n{traceback.format_exc()}")
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
