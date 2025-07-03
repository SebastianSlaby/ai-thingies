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

def parse_block_identifier(hcl_code):
    # Try to match resource/data blocks: block_type "item_type" "item_name" {
    match_two_level = re.search(r'^(resource|data)\s+"([^"]+)"\s+"([^"]+)"\s*\{', hcl_code, re.MULTILINE)
    if match_two_level:
        block_type = match_two_level.group(1)
        item_type = match_two_level.group(2)
        item_name = match_two_level.group(3)
        return f"{block_type}.{item_type}.{item_name}"

    # Try to match module/variable/output/locals/provider blocks: block_type "item_name" {
    match_one_level = re.search(r'^(module|variable|output|locals|provider)\s+"([^"]+)"\s*\{', hcl_code, re.MULTILINE)
    if match_one_level:
        block_type = match_one_level.group(1)
        item_name = match_one_level.group(2)
        return f"{block_type}.{item_name}"

    return None

# 3. Function to query for relevant Terraform files
def query_terraform(changed_code: str, n_results: int = 5, distance_threshold: float = 0.6, current_depth: int = 0, processed_docs: set = None):
    if processed_docs is None:
        processed_docs = set()

    if current_depth > 2:
        return {}

    print(f"Searching for code similar to:\n---\n{changed_code}\n---")

    all_relevant_docs = {}

    if current_depth == 0:
        # Search for the exact changed_code
        exact_match_results = collection.query(
            query_texts=[changed_code],
            n_results=1, # We only care about the top result
            include=['documents', 'distances', 'metadatas']
        )

        if exact_match_results and exact_match_results['documents'] and exact_match_results['documents'][0]:
            doc = exact_match_results['documents'][0][0]
            metadata = exact_match_results['metadatas'][0][0]
            distance = exact_match_results['distances'][0][0]

            # Verify that the returned document is indeed the changed_code itself
            if doc.strip() == changed_code.strip():
                all_relevant_docs[doc] = {'metadata': metadata, 'distance': distance, 'depth': current_depth}
                processed_docs.add(doc)
            else:
                # If the exact changed_code is not the top result, or not found,
                # then we cannot proceed with impact analysis from this starting point.
                print("Error: The provided changed_code could not be precisely identified in the database.")
                return {}
        else:
            # If no results are returned for the changed_code, then we cannot proceed.
            print("Error: No results found for the provided changed_code in the database.")
            return {}

    # Query for references (this block runs for all depths, including depth 0 after initial match)
    resource_identifier = parse_block_identifier(changed_code)
    if resource_identifier:
        print(f"Also searching for references to: {resource_identifier}")

        reference_results = collection.query(
            query_texts=[resource_identifier],
            n_results=n_results,
            include=['documents', 'distances', 'metadatas']
        )

        if reference_results and reference_results['documents']:
            for i in range(len(reference_results['documents'][0])):
                doc = reference_results['documents'][0][i]
                metadata = reference_results['metadatas'][0][i]
                distance = reference_results['distances'][0][i]

                if distance <= distance_threshold and doc not in processed_docs and 'reference' in metadata:
                    # Add the full content of the referencing block
                    referencing_block_content = metadata.get('full_content', doc) # Use doc as fallback if full_content is missing
                    if referencing_block_content not in processed_docs:
                        all_relevant_docs[referencing_block_content] = {'metadata': metadata, 'distance': distance, 'depth': current_depth}
                        processed_docs.add(referencing_block_content)

                        # Recursively search for references in the referencing block
                        indirect_results = query_terraform(
                            changed_code=referencing_block_content,
                            n_results=n_results,
                            distance_threshold=distance_threshold,
                            current_depth=current_depth + 1,
                            processed_docs=processed_docs
                        )
                        all_relevant_docs.update(indirect_results)

    return all_relevant_docs


def main():
    # Example usage: Simulate a change in a Lambda function
    example_changed_code = """
resource "aws_lambda_function" "another_lambda" {
  "function_name": "another-example-lambda",
  "handler": "index.handler",
  "runtime": "python3.9",
  "filename": "another_lambda_payload.zip"
}
"""
    all_relevant_docs = query_terraform(example_changed_code)

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
            depth = info['depth']
            
            print(f"\nFile: {file_path}")
            print(f"Distance: {distance:.4f}")
            print(f"Depth: {depth}")

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
    main()