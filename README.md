# rag_chatbot_poc

This project is a proof of concept for a chatbot application using FastAPI and MongoDB. It demonstrates how to build a simple chatbot that can respond to user queries based on the users data in the **Vector DB**.

## Prerequisites

- Python 3.10 or higher
- MongoDB instance (local or cloud)
- Redis instance (local or cloud)
- Qdrant instance (local or cloud)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Ayush-Pujari-07/rag_chatbot_poc.git
   cd rag_chatbot_poc
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install UV
   ```bash
   pip install uv
   ```

4. Install dependencies:
   ```bash
   uv pip install -e .
   ```

5. Configure environment variables:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Update the `.env` file with your MongoDB URI, Redis host, and JWT settings.

## Running the Application

1. Start the FastAPI server:
   ```bash
   python -m backend.main
   ```

2. Access the API documentation:
   - Open your browser and navigate to [http://localhost:8000/docs](http://localhost:8000/docs) for the Swagger UI.

## Project Structure

- `backend/`: Contains the main application code.
  - `auth/`: Handles authentication and user management.
  - `db/`: Database connection setup.
  - `logger.py`: Logging configuration.
  - `main.py`: Entry point for the FastAPI application.
- `.env`: Environment variables configuration.
- `pyproject.toml`: Project dependencies and configuration.
- `README.md`: Project documentation.

## Notes

- Ensure MongoDB and Redis are running before starting the application.
- Logs are stored in the `logs/` directory and are cleaned up automatically after 4 days.
