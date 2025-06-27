import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import os

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

# 3. Function to query for relevant Terraform files
def query_terraform(changed_code: str, n_results: int = 5, distance_threshold: float = 0.8):
    print(f"Searching for code similar to:\n---\n{changed_code}\n---")
    results = collection.query(
        query_texts=[changed_code],
        n_results=n_results,
        include=['documents', 'distances', 'metadatas']
    )

    print("\n--- Relevant Terraform Files ---")
    found_relevant = False
    if results and results['documents']:
        for i in range(len(results['documents'][0])):
            doc = results['documents'][0][i]
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            file_path = metadata.get('file_path', 'N/A')

            if distance <= distance_threshold:
                found_relevant = True
                print(f"\nFile: {file_path}")
                print(f"Distance: {distance:.4f}")
                print("Content:\n")
                print(doc)
                print("----------------------------------")
    
    if not found_relevant:
        print("No relevant files found within the specified distance threshold.")

if __name__ == "__main__":
    # Example usage: Simulate a change in a Terraform variable
    example_changed_code = """
variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
  default     = "my-new-test-bucket"
}
"""
    query_terraform(example_changed_code)

    # Another example: Simulate a change in an S3 bucket resource
    example_changed_code_2 = """
resource "aws_s3_bucket" "my_app_bucket" {
  bucket = "production-app-data"
  acl    = "private"

  tags = {
    Environment = "Production"
    Project     = "MyApp"
  }
}
"""
    query_terraform(example_changed_code_2)

    # New example: Simulate a change in a Lambda function
    example_changed_code_3 = """
resource "aws_lambda_function" "my_lambda" {
  function_name = "my-example-lambda-updated"
  handler       = "index.handler"
  runtime       = "nodejs20.x"
  timeout       = 60
}
"""
    query_terraform(example_changed_code_3)