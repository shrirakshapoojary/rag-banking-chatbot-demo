# -----------------------------
# IMPORTS
# -----------------------------
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import mysql.connector
from dotenv import load_dotenv
import os

# -----------------------------
# LOAD ENV VARIABLES
# -----------------------------
load_dotenv()

# -----------------------------
# MYSQL CONFIG
# -----------------------------
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# -----------------------------
# DATABASE FUNCTIONS
# -----------------------------
def get_balance(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT balance FROM customers WHERE name=%s", (name,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return f"Your balance is {result[0]} rupees"
    return "User not found"


def get_transactions(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.amount, t.type
        FROM transactions t
        JOIN customers c ON t.customer_id = c.id
        WHERE c.name = %s
    """, (name,))

    results = cursor.fetchall()
    conn.close()

    if results:
        return "\n".join([f"{t[1]}: {t[0]}" for t in results])
    return "No transactions found"

# -----------------------------
# LOGIN FUNCTION
# -----------------------------
def login():
    name = input("Enter your name: ")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM customers WHERE name=%s", (name,))
    result = cursor.fetchone()

    conn.close()

    if result:
        print(f"✅ Welcome {name}")
        return name
    else:
        print("❌ User not found. Try again.")
        return None

# -----------------------------
# LOAD FAQ DATA (RAG)
# -----------------------------
loader = TextLoader("bank_faq.txt")
documents = loader.load()

text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=10)
docs = text_splitter.split_documents(documents)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = FAISS.from_documents(docs, embeddings)
retriever = db.as_retriever()

# -----------------------------
# CHATBOT LOGIC
# -----------------------------
def chatbot(query, current_user):
    query = query.lower()

    # PERSONAL QUERIES → MYSQL
    if "balance" in query:
        return get_balance(current_user)

    elif "transaction" in query:
        return get_transactions(current_user)

    # GENERAL QUERIES → RAG
    docs = retriever.invoke(query)

    if not docs:
        return "Sorry, I don't know."

    return docs[0].page_content

# -----------------------------
# RUN APPLICATION
# -----------------------------
print("🏦 Banking Chatbot with Login")

# LOGIN LOOP
current_user = None
while not current_user:
    current_user = login()

# CHAT LOOP
while True:
    query = input("You: ")

    if query.lower() == "exit":
        print("👋 Thank you for using Banking Chatbot")
        break

    answer = chatbot(query, current_user)
    print("Bot:", answer)