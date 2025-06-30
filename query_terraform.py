import os
os.environ["HF_HUB_OFFLINE"] = "0"

import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from sentence_transformers import SentenceTransformer

# 1. Setup the embedding function using the specified model
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# 2. Initialize ChromaDB client and get the collection
client = chromadb.PersistentClient(path="chroma_terraform_db")
collection = client.get_or_create_collection(
    name="terraform_embeddings",
    embedding_function=sentence_transformer_ef
)

import re

def parse_resource(hcl_code):
    match = re.search(r'resource\s+"([^"]+)"\s+"([^"]+)"', hcl_code)
    if match:
        return match.group(1), match.group(2)
    return None, None

# 3. Function to query for relevant Terraform files
def query_terraform(changed_code: str, n_results: int = 5, distance_threshold: float = 0.6):
    print(f"Searching for code similar to:\n---\n{changed_code}\n---")

    query_texts = [changed_code]

    # Try to parse resource type and name to find references
    item_type, item_name = parse_resource(changed_code)
    if item_type and item_name:
        reference_string = f'{item_type}.{item_name}'
        print(f"Also searching for references to: {reference_string}")
        query_texts.append(reference_string)

    results = collection.query(
        query_texts=query_texts,
        n_results=n_results,
        include=['documents', 'distances', 'metadatas']
    )

    print("\n--- Relevant Terraform Files ---")
    found_relevant = False
    processed_docs = set()

    if results and results['documents']:
        for i in range(len(results['documents'])):
            for j in range(len(results['documents'][i])):
                doc = results['documents'][i][j]
                metadata = results['metadatas'][i][j]
                distance = results['distances'][i][j]
                file_path = metadata.get('file_path', 'N/A')

                if doc in processed_docs:
                    continue

                if distance <= distance_threshold:
                    found_relevant = True
                    print(f"\nFile: {file_path}")
                    print(f"Distance: {distance:.4f}")
                    print("Content:\n")
                    print(doc)
                    print("----------------------------------")
                    processed_docs.add(doc)
    
    if not found_relevant:
        print("No relevant files found within the specified distance threshold.")

if __name__ == "__main__":
    # Example usage: Simulate a change in a Lambda function
    example_changed_code = """
resource "aws_lambda_function" "another_lambda" {
  function_name = "another-example-lambda-updated"
  handler       = "index.handler"
  runtime       = "python3.9"
  filename      = "another_lambda_payload.zip"
}
"""
    query_terraform(example_changed_code)