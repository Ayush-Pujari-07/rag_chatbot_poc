import time

import requests
import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.colored_header import colored_header

# Constants for API endpoints
AUTH_API_URL = "http://localhost:8000/auth"
VECTOR_DB_API_URL = "http://localhost:8000/qdrant"
CHAT_API_URL = "http://localhost:8000/chatbot"

# Set page configuration
st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide",
)

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
    st.session_state.current_page = (
        "login" if not st.session_state.get("user") else "home"
    )
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "displayed_message_ids" not in st.session_state:
    st.session_state.displayed_message_ids = set()
if "messages" not in st.session_state:
    st.session_state.messages = []


def set_cookie_in_header(refresh_token):
    from http.cookies import SimpleCookie  # type: ignore

    cookies = SimpleCookie()
    cookies["refreshToken"] = refresh_token
    cookie_header = cookies.output(header="", sep=";").strip()
    return {"Cookie": cookie_header}


def register_user(name, email, password):
    response = requests.post(
        f"{AUTH_API_URL}/register",
        json={"name": name, "email": email, "password": password},
    )
    print(response.status_code)
    print(response.json())
    if response.status_code != 201:
        error_detail = response.json().get("details", "Unknown error occurred")
        raise Exception(error_detail)
    return response.json()


def login_user(email, password):
    response = requests.post(
        f"{AUTH_API_URL}/login", json={"email": email, "password": password}
    )
    if response.status_code == 200:
        tokens = response.json()
        st.session_state.refresh_token = tokens.get("refresh_token")
        st.session_state.access_token = tokens.get("access_token")
        st.session_state.user = {"username": email.split("@")[0]}  # Simple user info
        return True
    return False


def logout_user():
    st.session_state.user = None
    st.session_state.chat_initialized = False
    st.session_state.chat_history = []
    st.session_state.all_chats = []
    st.session_state.refresh_token = None
    st.session_state.access_token = None
    st.session_state.displayed_message_ids = set()
    st.session_state.messages = []
    st.session_state.current_page = "login"


def upload_file(file):
    """
    Upload a file to the vector database with improved error handling and response parsing
    """
    try:
        headers = set_cookie_in_header(st.session_state.refresh_token)
        # Ensure file is PDF and under size limit (e.g., 10MB)
        if file.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError("File size exceeds 10MB limit")

        files = {"file": (file.name, file.getvalue(), "application/pdf")}

        response = requests.post(
            f"{VECTOR_DB_API_URL}/document/upload",
            files=files,
            headers=headers,
            timeout=30,  # Set timeout for large files
        )

        response.raise_for_status()
        return {
            "success": True,
            "message": response.json().get("message", "Document uploaded successfully"),
            "document_id": response.json().get("document_id"),
            "status_code": response.status_code,
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Upload failed: {str(e)}",
            "status_code": getattr(e.response, "status_code", 500),
        }
    except ValueError as e:
        return {"success": False, "message": str(e), "status_code": 400}


def search_documents(query):
    headers = set_cookie_in_header(st.session_state.refresh_token)
    response = requests.post(
        f"{VECTOR_DB_API_URL}/search",
        json={"query": query},
        headers=headers,
    )
    return response.json()


def start_chat(refresh_token):
    try:
        headers = set_cookie_in_header(refresh_token)
        response = requests.post(f"{CHAT_API_URL}/chat/start", headers=headers)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        st.error(f"Start chat request failed: {e}")
        return None


def add_message_to_chat(refresh_token, message):
    try:
        headers = set_cookie_in_header(refresh_token)
        data = {"message": message}
        response = requests.post(f"{CHAT_API_URL}/chat", headers=headers, json=data)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        st.error(f"Add message request failed: {e}")
        return None


def get_all_chat(refresh_token):
    try:
        headers = set_cookie_in_header(refresh_token)
        response = requests.get(f"{CHAT_API_URL}/allChat", headers=headers)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        st.error(f"Get all chat request failed: {e}")
        return None


def display_chat_messages(messages):
    for message in messages["all_messages"]:
        if message["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(message["content"])


def load_chat_messages(refresh_token):
    get_all_chat_response = get_all_chat(refresh_token)
    if get_all_chat_response and get_all_chat_response.status_code == 200:
        return get_all_chat_response.json()
    return []  # Ensure a list is returned


# Sidebar navigation
def sidebar_menu():
    with st.sidebar:
        st.image(
            "https://www.svgrepo.com/show/384674/ai-artificial-intelligence-bot-brain-machine.svg",
            width=100,
        )
        colored_header(
            "RAG Chatbot",
            description="Document-aware AI Assistant",
            color_name="blue-70",
        )

        add_vertical_space(1)

        # Authentication section
        if not st.session_state.user:
            auth_option = st.radio("Authentication", ["Login", "Register"])
            if auth_option == "Register":
                st.session_state.current_page = "register"
            else:
                st.session_state.current_page = "login"
        else:
            with st.container():
                st.info(
                    f"👤 Logged in as: **{st.session_state.user.get('username', 'User')}**"
                )

            add_vertical_space(1)

            # Main navigation
            nav_options = [
                "Home",
                "Document Upload",
                "Search Documents",
                "Chat with Bot",
            ]
            selection = st.radio("Navigation", nav_options)

            if selection == "Home":
                st.session_state.current_page = "home"
            elif selection == "Document Upload":
                st.session_state.current_page = "upload"
            elif selection == "Search Documents":
                st.session_state.current_page = "search"
            elif selection == "Chat with Bot":
                st.session_state.current_page = "chat"

            add_vertical_space(1)

            # Chat history refresh
            if st.session_state.current_page == "chat":
                if st.button("🔄 Refresh Chat", use_container_width=True):
                    st.session_state.messages = load_chat_messages(
                        st.session_state.refresh_token
                    )
                    st.rerun()

            add_vertical_space(2)

            # Logout button
            if st.button("🚪 Logout", use_container_width=True, type="primary"):
                logout_user()
                st.rerun()


# Page functions
def register_page():
    st.title("Create Your Account")

    col1, col2 = st.columns([1, 1])

    with col1:
        name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")

        # Password requirements hint
        st.caption(
            "Password must contain at least one lowercase letter, one uppercase letter, one digit, and one special symbol (!@#$%^&*)"
        )

        if st.button("Register", type="primary", use_container_width=True):
            if name and email and password:
                with st.spinner("Creating your account..."):
                    try:
                        result = register_user(name, email, password)
                        st.success(result.get("email", "Registration successful!"))
                        time.sleep(1)
                        st.session_state.current_page = "login"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Registration failed: {str(e)}")
            else:
                st.error("Please fill all required fields")

    with col2:
        st.markdown("""
        ### Welcome to RAG Chatbot

        Thank you for joining our platform. With your account, you'll be able to:

        - 📄 Upload your own documents
        - 🔍 Search through your document collection
        - 💬 Chat with an AI that understands your documents

        Already have an account? [Login instead](#Login)
        """)


def login_page():
    st.title("Welcome Back")

    col1, col2 = st.columns([1, 1])

    with col1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login", type="primary", use_container_width=True):
            if email and password:
                with st.spinner("Logging in..."):
                    if login_user(email, password):
                        st.success("Login successful!")
                        time.sleep(0.5)
                        st.session_state.current_page = "home"
                        st.rerun()
                    else:
                        st.error("Login failed. Please check your credentials.")
            else:
                st.error("Please enter both email and password")

    with col2:
        st.markdown("""
        ### Document-Aware AI Assistant

        Access your personalized AI chatbot that can:

        - Answer questions using your documents as context
        - Retrieve specific information from your document collection
        - Help you analyze your document content

        Don't have an account? [Register now](#Register)
        """)


def home_page():
    st.title("Document Management and RAG Chatbot")

    # Welcome card
    with st.container():
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"""
            # 👋 Welcome, {st.session_state.user.get("username", "User")}!

            This application allows you to leverage AI to interact with your documents.
            """)
        with col2:
            st.image(
                "https://www.svgrepo.com/show/384674/ai-artificial-intelligence-bot-brain-machine.svg",
                width=150,
            )

    st.divider()

    # Features
    st.subheader("Key Features")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 📄 Document Upload
        Upload your PDF documents to add them to your knowledge base.
        """)
        if st.button("Go to Upload", use_container_width=True):
            st.session_state.current_page = "upload"
            st.rerun()

    with col2:
        st.markdown("""
        ### 🔍 Document Search
        Search through all your uploaded documents with natural language.
        """)
        if st.button("Go to Search", use_container_width=True):
            st.session_state.current_page = "search"
            st.rerun()

    with col3:
        st.markdown("""
        ### 🤖 Chat with AI
        Interact with an AI assistant that has access to your documents.
        """)
        if st.button("Start Chatting", use_container_width=True):
            st.session_state.current_page = "chat"
            st.rerun()


def upload_page():
    st.title("Document Upload")

    # Custom CSS for upload area
    st.markdown(
        """
        <style>
        .upload-container {
            border: 2px dashed #cccccc;
            border-radius: 5px;
            padding: 20px;
            text-align: center;
            background-color: #f8f9fa;
        }
        .success-message {
            color: #28a745;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .error-message {
            color: #dc3545;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("""
    ### 📄 Upload Your Documents
    Upload PDF documents to enhance the AI's knowledge base. The documents will be processed
    and made available for searching and referencing during chat conversations.

    **Supported format:** PDF files (max 10MB)
    """)

    with st.container():
        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Drop your PDF file here or click to browse",
                type="pdf",
                accept_multiple_files=False,
                help="Maximum file size: 10MB",
            )

        with col2:
            st.markdown("""
            #### Guidelines:
            - PDF format only
            - Max size: 10MB
            - Text should be extractable
            - One file at a time
            """)

    if uploaded_file:
        st.markdown("---")
        col1, col2 = st.columns([3, 1])

        with col1:
            st.info(
                f"📎 Selected file: **{uploaded_file.name}** ({round(uploaded_file.size / 1024 / 1024, 2)}MB)"
            )

        with col2:
            if st.button(
                "📤 Upload Document", type="primary", use_container_width=True
            ):
                with st.spinner("Processing document..."):
                    result = upload_file(uploaded_file)

                    if result["success"]:
                        st.success(result["message"])
                        st.balloons()
                        # Add success details
                        st.markdown(f"""
                        ✅ Document processed successfully!
                        - Document ID: `{result.get("document_id", "N/A")}`
                        - Status: `{result.get("status_code", 200)}`
                        """)
                    else:
                        st.error(result["message"])
                        st.markdown(f"""
                        ❌ Upload failed (Status: `{result.get("status_code", "N/A")}`)
                        Please try again or contact support if the issue persists.
                        """)


def search_page():
    st.title("Search Documents")
    st.markdown(
        "Search through your document collection with natural language queries."
    )

    search_query = st.text_input(
        "Enter your search query", placeholder="What would you like to search for?"
    )

    if st.button("Search", type="primary", disabled=not search_query):
        if search_query:
            with st.spinner("Searching documents..."):
                search_results = search_documents(search_query)
                if search_results and len(search_results) > 0:
                    st.success(f"Found {len(search_results['results'])} results")
                    print(search_results)

                    for i, doc in enumerate(search_results["results"]):
                        st.markdown("---")
                        doc = doc.get("payload", {})
                        if doc:
                            with st.expander(
                                f"Result {i + 1}: {doc.get('title', 'Untitled')}"
                            ):
                                st.markdown(
                                    f"**Source:** {doc.get('source', 'Unknown')}"
                                )
                                st.markdown(
                                    f"**Page:** {doc.get('excerpt_page_number', 'N/A')}"
                                )
                                st.markdown("**Excerpt:**")
                                st.markdown(
                                    f"{doc.get('excerpt', 'No content available')}"
                                )
                else:
                    st.info("No results found. Please try a different query.")


def chat_page():
    st.title("Chat with AI Assistant")
    st.markdown("Ask questions about your documents and get AI-powered responses.")

    if "refresh_token" not in st.session_state or not st.session_state.refresh_token:
        st.error("Please log in to access the chat page.")
        return

    # Initialize chat if not already done
    if not st.session_state.chat_initialized:
        with st.status("Initializing chat...") as status:
            start_chat_response = start_chat(st.session_state.refresh_token)
            if start_chat_response and start_chat_response.status_code == 200:
                st.session_state.chat_initialized = True
                st.session_state.messages = load_chat_messages(
                    st.session_state.refresh_token
                )
                status.update(
                    label="Chat initialized successfully!",
                    state="complete",
                    expanded=False,
                )
            else:
                status.update(label="Failed to initialize chat", state="error")

    # Display messages
    if st.session_state.messages:
        display_chat_messages(st.session_state.messages)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(
                "Hello! I'm your document-aware AI assistant. How can I help you today?"
            )

    # Chat input
    if chat_message := st.chat_input("Ask me anything about your documents..."):
        # Add user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(chat_message)

        st.session_state.messages["all_messages"].append({
            "role": "user",
            "content": chat_message,
        })  # type: ignore

        # Get AI response
        with st.spinner("Thinking..."):
            add_message_response = add_message_to_chat(
                st.session_state.refresh_token, chat_message
            )
            if add_message_response and add_message_response.status_code == 200:
                assistant_message = add_message_response.json().get("content", "")
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(assistant_message)
                st.session_state.messages["all_messages"].append({
                    "role": "assistant",
                    "content": assistant_message,
                })  # type: ignore
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.error(
                        "I'm sorry, I couldn't process your request. Please try again later."
                    )


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
