import os
os.environ["HF_HUB_OFFLINE"] = "0"

import hcl2
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from sentence_transformers import SentenceTransformer
import json
import re

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
                hcl_data = hcl2.load(f)
                relative_path = os.path.relpath(file_path, ".")

                for block_type, blocks in hcl_data.items():
                    if not isinstance(blocks, list):
                        continue

                    for block in blocks:
                        # terraform block has a different structure and no name
                        if block_type == 'terraform':
                            document = f"terraform {json.dumps(block, indent=2)}"
                            documents.append(document)
                            metadatas.append({
                                "file_path": relative_path,
                                "block_type": "terraform"
                            })
                            ids.append(f"doc_{doc_id_counter}")
                            doc_id_counter += 1
                            continue

                        # Most other blocks are dictionaries with a single key which is the name
                        # or type of the block
                        for key, value in block.items():
                            document = ""
                            item_type = None
                            item_name = ""
                            config = {}

                            # resource and data blocks have two levels of keys (type and name)
                            if block_type in ['resource', 'data']:
                                item_type = key
                                if value:
                                    item_name, config = list(value.items())[0]
                                else:
                                    item_name, config = "", {}
                                document = f'{block_type} "{item_type}" "{item_name}" {json.dumps(config, indent=2)}'
                            # module, variable, output, etc. have one level of key (name)
                            else:
                                item_name = key
                                config = value
                                document = f'{block_type} "{item_name}" {json.dumps(config, indent=2)}'

                            # Add the main block document
                            metadata = {
                                "file_path": relative_path,
                                "block_type": block_type,
                                "item_name": item_name,
                            }
                            if item_type:
                                metadata["item_type"] = item_type
                            
                            documents.append(document)
                            metadatas.append(metadata)
                            ids.append(f"doc_{doc_id_counter}")
                            doc_id_counter += 1

                            # Create additional documents for references for ALL block types
                            if isinstance(config, dict):
                                for _, val in config.items():
                                    if isinstance(val, str) and "." in val:
                                        references = re.findall(r'\${([\w\._-]+)}', val)
                                        for ref in references:
                                            documents.append(ref)
                                            ref_metadata = {
                                                "file_path": relative_path,
                                                "reference": ref,
                                                "referencing_block_type": block_type,
                                                "referencing_item_name": item_name,
                                                "full_content": document
                                            }
                                            if item_type:
                                                ref_metadata["referencing_item_type"] = item_type
                                            
                                            metadatas.append(ref_metadata)
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
        print(f"Successfully embedded {len(documents)} Terraform document(s).")
    else:
        print("No Terraform files found to embed.")

if __name__ == "__main__":
    main()