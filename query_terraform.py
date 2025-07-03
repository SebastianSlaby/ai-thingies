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

    all_relevant_docs = {}

    # Query for the changed code itself
    changed_code_results = collection.query(
        query_texts=[changed_code],
        n_results=1,
        include=['documents', 'distances', 'metadatas']
    )

    if changed_code_results and changed_code_results['documents'] and changed_code_results['documents'][0]:
        doc = changed_code_results['documents'][0][0]
        metadata = changed_code_results['metadatas'][0][0]
        distance = changed_code_results['distances'][0][0]
        if distance < 0.1: # Very low distance for an almost exact match
            all_relevant_docs[doc] = {'metadata': metadata, 'distance': distance}


    # Query for references
    item_type, item_name = parse_resource(changed_code)
    if item_type and item_name:
        reference_string = f'{item_type}.{item_name}'
        print(f"Also searching for references to: {reference_string}")

        reference_results = collection.query(
            query_texts=[reference_string],
            n_results=n_results,
            include=['documents', 'distances', 'metadatas']
        )

        if reference_results and reference_results['documents']:
            for i in range(len(reference_results['documents'][0])):
                doc = reference_results['documents'][0][i]
                metadata = reference_results['metadatas'][0][i]
                distance = reference_results['distances'][0][i]

                if distance <= distance_threshold:
                    all_relevant_docs[doc] = {'metadata': metadata, 'distance': distance}

    print("\n--- Relevant Terraform Files ---")
    found_relevant = False

    # Sort the results by distance
    sorted_docs = sorted(all_relevant_docs.items(), key=lambda item: item[1]['distance'])

    if sorted_docs:
        for doc, info in sorted_docs:
            found_relevant = True
            metadata = info['metadata']
            file_path = metadata.get('file_path', 'N/A')
            distance = info['distance']
            
            print(f"\nFile: {file_path}")
            print(f"Distance: {distance:.4f}")

            # If the document is a reference, print the full content of the referencing block
            if 'reference' in metadata:
                print(f"Reference: {metadata['reference']}")
                print("Full Content of Referencing Block:\n")
                print(metadata.get('full_content', 'N/A'))
            else:
                print("Content:\n")
                print(doc)
            
            print("----------------------------------")
    
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