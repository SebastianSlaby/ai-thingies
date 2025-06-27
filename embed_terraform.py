import os
os.environ["HF_HUB_OFFLINE"] = "1"

import hcl2
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from sentence_transformers import SentenceTransformer
import json

# 1. Setup the embedding function using the specified model
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# 2. Initialize ChromaDB client and manage the collection
client = chromadb.PersistentClient(path="chroma_terraform_db")

# Delete the old collection if it exists, to ensure a fresh start
try:
    client.delete_collection(name="terraform_embeddings")
    print("Old collection 'terraform_embeddings' deleted.")
except Exception as e:
    # This is expected if the collection doesn't exist yet
    print("Old collection not found, proceeding to create a new one.")
    pass

# Create a new collection with the correct embedding function
collection = client.get_or_create_collection(
    name="terraform_embeddings",
    embedding_function=sentence_transformer_ef
)

# 3. Function to find all Terraform files
def find_tf_files(directory):
    tf_files = []
    for root, _, files in os.walk(directory):
        # Skip the examples directory
        if "/examples" in root:
            continue
        for file in files:
            if file.endswith(".tf"):
                tf_files.append(os.path.join(root, file))
    return tf_files

# 4. Main processing logic
def main():
    terraform_directory = "terraform"
    tf_files = find_tf_files(terraform_directory)
    
    documents = []
    metadatas = []
    ids = []
    doc_id_counter = 0

    for file_path in tf_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                # Use a simplified approach to create chunks without deep parsing
                # This is more robust for files with mixed content or syntax errors
                content = f.read()
                # Create a single document for the whole file for simplicity
                # A more advanced version could split by resource, etc.
                
                relative_path = os.path.relpath(file_path, ".")

                documents.append(content)
                metadatas.append({"file_path": relative_path})
                ids.append(f"doc_{doc_id_counter}")
                doc_id_counter += 1

            except Exception as e:
                print(f"Could not process file {file_path}: {e}")

    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully embedded {len(documents)} Terraform file(s).")
    else:
        print("No Terraform files found to embed.")

if __name__ == "__main__":
    main()