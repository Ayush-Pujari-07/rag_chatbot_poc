# RAG Chatbot POC

This project is a Proof of Concept (POC) for a Retrieval-Augmented Generation (RAG) chatbot. The chatbot leverages retrieval techniques to enhance responses with relevant context from a knowledge base.

## Features

- **User Authentication**: Secure user registration and login using JWT-based authentication.
- **Document Upload**: Upload PDF documents to build a knowledge base.
- **Vector Search**: Perform semantic searches on uploaded documents using Qdrant.
- **AI-Powered Chat**: Interact with an AI assistant that uses document context for accurate responses.
- **Streamlit Frontend**: A user-friendly interface for interacting with the chatbot and managing documents.

## Prerequisites

- **Python**: Version 3.12 or higher.
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

## Project Flow

1. **User Query**: The user submits a question via the Streamlit chatbot interface.
2. **Authentication**: The backend validates the user's session using refresh token authentication.
3. **Document Upload**: Users upload PDF documents via the frontend, which are processed and stored in the Qdrant vector database.
4. **Retrieval**: The backend retrieves relevant documents or context from the Qdrant vector database using hybrid search (dense and sparse vectors).
5. **Augmentation**: The retrieved context is combined with the user's query to provide additional information for the AI model.
6. **Generation**: The combined input is sent to OpenAI's LLM (Large Language Model) to generate a response.
7. **Response**: The chatbot returns the generated answer to the user, which is displayed in the Streamlit interface.

## Code Structure

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
│   ├── requirements.txt    # Backend dependencies
├── frontend/
│   ├── app.py              # Streamlit frontend
│   ├── requirements.txt    # Frontend dependencies
│   ├── Dockerfile          # Dockerfile for frontend
├── docker-compose.yaml     # Docker Compose configuration
├── pyproject.toml          # Project dependencies and configuration
├── .env.example            # Example environment variables
├── README.md               # Project documentation
```

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
   - Backend:
     ```bash
     pip install -r backend/requirements.txt
     ```
   - Frontend:
     ```bash
     pip install -r frontend/requirements.txt
     ```

4. **Configure Environment Variables**:
   - Copy the example `.env` file:
     ```bash
     cp .env.example .env
     ```
   - Update `.env` with your MongoDB URI, Redis host, Qdrant settings, and OpenAI API key.

## Running the Application Locally

1. **Start the Backend Server**:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Start the Frontend**:
   ```bash
   cd ../frontend
   streamlit run app.py
   ```

3. **Access the Chatbot**:
   - Open your browser and navigate to the provided local URL for the frontend (e.g., `http://localhost:8501`).

## Running with Docker

1. **Build and Start Services**:
   ```bash
   docker-compose up --build
   ```

2. **Access the Chatbot**:
   - Frontend: `http://localhost:8501`
   - Backend: `http://localhost:8000`

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

## Notes

- Ensure MongoDB, Redis, and Qdrant are running before starting the application.
- Logs are stored in the `logs/` directory and are automatically cleaned up after 4 days.
- Ensure you have the required API keys for any external LLM services.
- Configuration files may be present for customizing retrieval or model parameters.

## Future Enhancements

- **Advanced Search Filters**: Add support for filtering by metadata.
- **Multi-File Upload**: Enable uploading multiple documents at once.
- **Improved AI Responses**: Enhance the chatbot's system prompts for better accuracy.

# License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.