import os
import re
import subprocess
import argparse
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Embedding and ChromaDB Classes (reused) ---
class SentenceTransformerEmbedding(EmbeddingFunction):
    def __init__(self, model_name="sentence-transformers/all-mpnet-base-v2"):
        self.model = SentenceTransformer(model_name)
    
    def __call__(self, input: Documents) -> Embeddings:
        return self.model.encode(input).tolist()

# --- Terraform Analysis Functions ---

def find_resources_in_file(file_path):
    """Extracts resource and variable names from a single Terraform file."""
    resources = set()
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find resources, data, modules
        for match in re.finditer(r'(resource|data|module)\s+"([^"]+)"\s+"([^"]+)"', content):
            resource_type, resource_name = match.groups()[1], match.groups()[2]
            resources.add(f'{resource_type}.{resource_name}')

        # Find variables
        for match in re.finditer(r'variable\s+"([^"]+)"', content):
            resources.add(f'var.{match.groups()[0]}')

        # Find outputs
        for match in re.finditer(r'output\s+"([^"]+)"', content):
            resources.add(f'output.{match.groups()[0]}')
            
    except FileNotFoundError:
        logging.error(f"Changed file not found: {file_path}")
        return None
    return resources

def run_terraform_graph(terraform_dir):
    """Runs terraform init and graph, returns the graph output."""
    try:
        logging.info(f"Running 'terraform init' in {terraform_dir}...")
        subprocess.run(["terraform", "init", "-no-color"], cwd=terraform_dir, check=True, capture_output=True, text=True)
        
        logging.info(f"Running 'terraform graph' in {terraform_dir}...")
        result = subprocess.run(["terraform", "graph", "-no-color"], cwd=terraform_dir, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Terraform command failed in {terraform_dir}: {e.stderr}")
        return None
    except FileNotFoundError:
        logging.error("'terraform' command not found. Please ensure Terraform is installed and in your PATH.")
        return None

def find_dependent_resources(graph_output, changed_resources):
    """Parses graph output to find resources that depend on the changed resources."""
    dependents = set()
    graph_dependency_names = {f'[root] {res}' for res in changed_resources}

    for line in graph_output.splitlines():
        match = re.match(r'\s*"([^"]+)" -> "([^"]+)"', line)
        if match:
            source, dest = match.groups()
            if dest in graph_dependency_names:
                # Clean the source name: remove [root] and any (expand) suffixes
                clean_source = source.replace("[root] ", "").strip()
                clean_source = re.sub(r'\s*\(expand\)', '', clean_source)
                dependents.add(clean_source)
    return dependents

def map_resources_to_files(terraform_dir):
    """Creates a map of all resources to the files they are defined in."""
    resource_map = {}
    examples_path = os.path.join(terraform_dir, 'examples')
    for root, _, files in os.walk(terraform_dir):
        if root.startswith(examples_path):
            continue
        for file in files:
            if file.endswith(".tf"):
                file_path = os.path.join(root, file)
                resources_in_file = find_resources_in_file(file_path)
                for resource in resources_in_file:
                    resource_map[resource] = file_path
    return resource_map

# --- Semantic Search Function ---
def find_semantic_files(changed_file_path, n_results):
    """Finds semantically similar files using ChromaDB."""
    try:
        with open(changed_file_path, 'r') as f:
            query_text = f.read()

        chroma_client = chromadb.PersistentClient(path="./chroma_terraform_db")
        embedding_model = SentenceTransformerEmbedding()
        collection = chroma_client.get_collection(name="terraform_embeddings", embedding_function=embedding_model)

        results = collection.query(query_texts=[query_text], n_results=n_results)
        
        if not results or not results.get('metadatas') or not results['metadatas'][0]:
            return set()

        return {meta['source_file'] for meta in results['metadatas'][0]}
    except Exception as e:
        logging.error(f"Semantic search failed: {e}")
        return set()

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Analyze the impact of a Terraform file change.")
    parser.add_argument("changed_file", help="The path to the changed Terraform file.")
    parser.add_argument("--n_results", type=int, default=10, help="The number of semantic results to retrieve.")
    args = parser.parse_args()

    terraform_root = "./terraform"

    # 1. Find resources in the changed file
    logging.info(f"Analyzing changed file: {args.changed_file}")
    changed_resources = find_resources_in_file(args.changed_file)
    if changed_resources is None:
        return
    logging.info(f"Found resources in changed file: {changed_resources}")

    # 2. Get dependency graph
    graph_output = run_terraform_graph(terraform_root)
    if not graph_output:
        return

    # 3. Find dependent resources from graph
    dependent_resources = find_dependent_resources(graph_output, changed_resources)
    logging.info(f"Found dependent resources: {dependent_resources}")

    # 4. Map all resources in the project to their files
    logging.info("Mapping all resources to files...")
    full_resource_map = map_resources_to_files(terraform_root)

    # 5. Find files containing the dependent resources
    dependency_files = {full_resource_map.get(res) for res in dependent_resources if full_resource_map.get(res)}

    # 6. Get semantically similar files
    logging.info("Performing semantic search...")
    semantic_files = find_semantic_files(args.changed_file, args.n_results)

    # 7. Combine and present results
    all_relevant_files = dependency_files.union(semantic_files)
    all_relevant_files.add(args.changed_file) # Always include the source file

    print("\n--- Impact Analysis Results ---")
    print(f"Found {len(all_relevant_files)} relevant file(s) for the change in \"{args.changed_file}\":")
    for file_path in sorted(list(all_relevant_files)):
        print(f"- {file_path}")

if __name__ == "__main__":
    main()
