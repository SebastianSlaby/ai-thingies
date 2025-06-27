from chromadb import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer
import chromadb

class SentenceTransformerEmbedding(EmbeddingFunction):
    def __init__(self, model_name="sentence-transformers/all-mpnet-base-v2"):
        self.model = SentenceTransformer(model_name)
    
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self.model.encode(input).tolist()
        return embeddings


chroma_client = chromadb.PersistentClient(path="./chroma_db")
# embedding_model = SentenceTransformerEmbedding(model_name="microsoft/codebert-base")
embedding_model = SentenceTransformerEmbedding()


collection = chroma_client.get_or_create_collection(
    name="doc_analysis",
    embedding_function=embedding_model
    # metadata={"hnsw:space": "cosine"}  # Optimized similarity metric
)

# Using code snippets as documents since we're using a code-based model
documents = [
    "def factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)",
    "class Car:\n    def __init__(self, make, model):\n        self.make = make\n        self.model = model",
    "import pandas as pd\ndf = pd.DataFrame()",
    "// A simple for loop in C++\nfor(int i=0; i<10; i++) { }",
]

collection.add(
    documents=documents,
    metadatas=[{"source": "python"}, {"source": "python"}, {"source": "python"}, {"source": "cpp"}],
    ids=["doc1", "doc2", "doc3", "doc4"]
)

query = "python class definition"
results = collection.query(
    query_texts=[query],
    n_results=2,
    where={"source": "python"}  # Metadata filter
)

print("Top matches:")
for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0])):
    print(f"{i+1}. {doc} (Distance: {dist:.4f})")
