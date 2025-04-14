# RAG Chatbot PoC

This project is a **Proof of Concept (PoC)** for a chatbot application that leverages **FastAPI**, **MongoDB**, **Redis**, and **Qdrant** to create a document-aware conversational assistant. The chatbot uses **retrieval-augmented generation (RAG)** to answer user queries based on uploaded documents.

## Features

- **User Authentication**: Secure user registration and login using JWT-based authentication.
- **Document Upload**: Upload PDF documents to build a knowledge base.
- **Vector Search**: Perform semantic searches on uploaded documents using Qdrant.
- **AI-Powered Chat**: Interact with an AI assistant that uses document context for accurate responses.
- **Streamlit Frontend**: A user-friendly interface for interacting with the chatbot and managing documents.

## Prerequisites

- **Python**: Version 3.10 or higher.
- **MongoDB**: For storing user and chat data.
- **Redis**: For caching and session management.
- **Qdrant**: For vector database operations.
- **OpenAI API Key**: For generating embeddings and AI responses.

## Architecture

The project is structured into the following components:

- **Backend**:
  - **FastAPI**: Provides RESTful APIs for authentication, document management, and chat functionalities.
  - **Qdrant**: Handles vector-based document storage and semantic search.
  - **MongoDB**: Stores user data, chat history, and metadata.
  - **Redis**: Manages caching and session data.
- **Frontend**:
  - **Streamlit**: A web-based interface for user interaction.
- **AI Integration**:
  - **OpenAI API**: Generates embeddings for vector search and powers the chatbot's responses.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Ayush-Pujari-07/rag_chatbot_poc.git
   cd rag_chatbot_poc
   ```

2. **Set Up a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install uv
   uv pip install -e .
   ```

4. **Configure Environment Variables**:
   - Copy the example `.env` file:
     ```bash
     cp .env.example .env
     ```
   - Update `.env` with your MongoDB URI, Redis host, Qdrant settings, and OpenAI API key.

## Running the Application

1. **Start the Backend**:
   ```bash
   python -m backend.main
   ```

2. **Run the Frontend**:
   ```bash
   streamlit run app.py
   ```

3. **Access the Application**:
   - Backend API: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
   - Frontend: [http://localhost:8501](http://localhost:8501)

## Usage

### 1. User Authentication
- **Register**: Create an account using the Streamlit interface.
- **Login**: Log in to access document upload, search, and chat features.

### 2. Document Upload
- Navigate to the **Document Upload** page.
- Upload PDF files (max size: 10MB).
- The documents are processed and stored in Qdrant for vector-based search.

### 3. Search Documents
- Use the **Search Documents** page to query your uploaded documents.
- Enter a natural language query to retrieve relevant document excerpts.

### 4. Chat with AI
- Go to the **Chat with Bot** page.
- Ask questions about your documents, and the AI will provide context-aware responses.

## Project Structure

```
rag_chatbot_poc/
├── backend/
│   ├── auth/               # Authentication and user management
│   ├── chat/               # Chatbot logic and schemas
│   ├── config.py           # Application configuration
│   ├── db/                 # MongoDB connection setup
│   ├── logger.py           # Logging configuration
│   ├── main.py             # FastAPI application entry point
│   ├── vector_db/          # Qdrant integration and vector search
├── app.py                  # Streamlit frontend
├── pyproject.toml          # Project dependencies and configuration
├── .env.example            # Example environment variables
├── README.md               # Project documentation
```

## Notes

- Ensure MongoDB, Redis, and Qdrant are running before starting the application.
- Logs are stored in the `logs/` directory and are automatically cleaned up after 4 days.

## Future Enhancements

- **Advanced Search Filters**: Add support for filtering by metadata.
- **Multi-File Upload**: Enable uploading multiple documents at once.
- **Improved AI Responses**: Enhance the chatbot's system prompts for better accuracy.
