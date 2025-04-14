import time

import requests
import streamlit as st

# Constants for API endpoints
AUTH_API_URL = "http://localhost:8000/auth"
VECTOR_DB_API_URL = "http://localhost:8000/qdrant"
CHAT_API_URL = "http://localhost:8000/chatbot"

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_initialized" not in st.session_state:
    st.session_state.chat_initialized = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "all_chats" not in st.session_state:
    st.session_state.all_chats = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"


def register_user(name, email, password):
    response = requests.post(
        f"{AUTH_API_URL}/register",
        json={"name": name, "email": email, "password": password},
    )
    if response.status_code != 200:
        error_detail = response.json().get("detail", "Unknown error occurred")
        raise Exception(error_detail)
    return response.json()


def login_user(email, password):
    response = requests.post(
        f"{AUTH_API_URL}/login", json={"email": email, "password": password}
    )
    if response.status_code == 200:
        st.session_state.user = response.json()
        return True
    return False


def logout_user():
    st.session_state.user = None
    st.session_state.chat_initialized = False
    st.session_state.chat_history = []
    st.session_state.all_chats = []


def upload_file(file):
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    response = requests.post(
        f"{VECTOR_DB_API_URL}/document/upload",
        files=files,
        headers={"Authorization": f"Bearer {st.session_state.user['refresh_token']}"},
    )
    return response.json()


def search_documents(query):
    response = requests.get(
        f"{VECTOR_DB_API_URL}/search",
        params={"query": query},
        headers={"Authorization": f"Bearer {st.session_state.user['refresh_token']}"},
    )
    return response.json()


def initialize_chat():
    response = requests.post(
        f"{CHAT_API_URL}/chat/start",
        headers={"Authorization": f"Bearer {st.session_state.user['refresh_token']}"},
    )
    if response.status_code == 200:
        data = response.json()
        st.session_state.chat_initialized = True
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": data.get("content", "Hello! How can I help you today?"),
        })
        return data
    return None


def chat_with_bot(message):
    response = requests.post(
        f"{CHAT_API_URL}/chat",
        json={"message": message},
        headers={"Authorization": f"Bearer {st.session_state.user['refresh_token']}"},
    )
    if response.status_code == 200:
        data = response.json()
        st.session_state.chat_history.append({"role": "user", "content": message})
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": data.get("content", "I'm not sure how to respond to that."),
        })
        return data
    return {"content": "Error: Could not get a response from the chatbot"}


def get_all_chats():
    response = requests.get(
        f"{CHAT_API_URL}/allChat",
        headers={"Authorization": f"Bearer {st.session_state.user['refresh_token']}"},
    )
    if response.status_code == 200:
        st.session_state.all_chats = response.json().get("messages", [])
        return st.session_state.all_chats
    return []


# Sidebar navigation
def sidebar_menu():
    st.sidebar.title("Navigation")

    # Authentication section
    if not st.session_state.user:
        auth_option = st.sidebar.radio("Authentication", ["Login", "Register"])
        if auth_option == "Register":
            st.session_state.current_page = "register"
        else:
            st.session_state.current_page = "login"
    else:
        user_info = st.sidebar.container()
        user_info.write(
            f"Logged in as: {st.session_state.user.get('username', 'User')}"
        )

        # Main navigation
        nav_options = ["Home", "Document Upload", "Search Documents", "Chat with Bot"]
        selection = st.sidebar.radio("Go to", nav_options)

        if selection == "Home":
            st.session_state.current_page = "home"
        elif selection == "Document Upload":
            st.session_state.current_page = "upload"
        elif selection == "Search Documents":
            st.session_state.current_page = "search"
        elif selection == "Chat with Bot":
            st.session_state.current_page = "chat"
            # Refresh chat history when navigating to chat page
            if st.sidebar.button("Refresh Chat History"):
                get_all_chats()

        if st.sidebar.button("Logout"):
            logout_user()
            st.session_state.current_page = "login"
            st.rerun()


# Page functions
def register_page():
    st.title("Register")
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    # Password requirements hint
    st.caption(
        "Password must contain at least one lowercase letter, one uppercase letter, one digit, and one special symbol (!@#$%^&*)"
    )

    if st.button("Register"):
        if name and email and password:
            try:
                result = register_user(name, email, password)
                st.success(result.get("message", "Registration successful!"))
                time.sleep(2)
                st.session_state.current_page = "login"
                st.rerun()
            except Exception as e:
                st.error(f"Registration failed: {str(e)}")
        else:
            st.error("Please fill all required fields")


def login_page():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if email and password:
            if login_user(email, password):
                st.success("Login successful!")
                time.sleep(1)
                st.session_state.current_page = "home"
                st.rerun()
            else:
                st.error("Login failed. Please check your credentials.")
        else:
            st.error("Please enter both email and password")


def home_page():
    st.title("Document Management and RAG Chatbot")
    st.write("Welcome to the RAG Chatbot Application!")
    st.write("This application allows you to:")
    st.markdown("""
    - Upload PDF documents
    - Search through your documents
    - Chat with an AI assistant that uses your documents as context
    """)
    st.write("Use the sidebar menu to navigate through the application.")


def upload_page():
    st.title("Document Upload")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file:
        st.write(f"File selected: {uploaded_file.name}")
        if st.button("Upload Document"):
            with st.spinner("Uploading and processing document..."):
                upload_result = upload_file(uploaded_file)
                if "message" in upload_result:
                    st.success(upload_result["message"])
                else:
                    st.error("Failed to upload file")


def search_page():
    st.title("Search Documents")
    search_query = st.text_input("Enter search query")
    if search_query:
        if st.button("Search"):
            with st.spinner("Searching documents..."):
                search_results = search_documents(search_query)
                if search_results and len(search_results) > 0:
                    st.subheader("Search Results:")
                    for i, doc in enumerate(search_results):
                        with st.expander(
                            f"Result {i + 1}: {doc.get('title', 'Untitled')}"
                        ):
                            st.write(f"**Source:** {doc.get('source', 'Unknown')}")
                            st.write(
                                f"**Page:** {doc.get('excerpt_page_number', 'N/A')}"
                            )
                            st.write("**Excerpt:**")
                            st.write(doc.get("excerpt", "No content available"))
                else:
                    st.info("No results found. Please try a different query.")


def chat_page():
    st.title("Chat with AI Assistant")

    # Display chat history in the sidebar if available
    if st.session_state.user and len(st.session_state.all_chats) > 0:
        with st.sidebar.expander("Chat History", expanded=False):
            for i, chat in enumerate(st.session_state.all_chats):
                if i % 2 == 0:  # Even indices are user messages
                    st.sidebar.write(f"**You:** {chat.get('content', '')[:30]}...")
                else:  # Odd indices are assistant messages
                    st.sidebar.write(f"**Bot:** {chat.get('content', '')[:30]}...")
                st.sidebar.divider()

    # Initialize chat if not already done
    if st.session_state.user and not st.session_state.chat_initialized:
        with st.spinner("Initializing chat..."):
            initialize_chat()

    # Display chat messages with st.chat_message
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(message["content"])

    # Chat input using st.chat_input instead of text_input + button
    if user_message := st.chat_input("Type your message here..."):
        with st.spinner("Getting response..."):
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_message)

            # Get bot response
            response_data = chat_with_bot(user_message)

            # Display bot response
            with st.chat_message("assistant"):
                st.markdown(
                    response_data.get("content", "I'm not sure how to respond to that.")
                )

            st.rerun()


# Main app logic
def main():
    sidebar_menu()

    if st.session_state.current_page == "register":
        register_page()
    elif st.session_state.current_page == "login":
        login_page()
    elif st.session_state.current_page == "home":
        home_page()
    elif st.session_state.current_page == "upload":
        upload_page()
    elif st.session_state.current_page == "search":
        search_page()
    elif st.session_state.current_page == "chat":
        chat_page()


if __name__ == "__main__":
    main()
