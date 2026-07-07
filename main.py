import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

from scripts import annotate_proteins
from scripts import run_pathway_enrichment
from scripts import run_string_ppi

def main():
    parser = argparse.ArgumentParser(description="ProteoMind-AI Multi-Agent Pipeline")
    parser.add_argument("--input_dir", type=str, help="Path to input directory containing upregulated/downregulated CSVs.")
    parser.add_argument("--output_dir", type=str, help="Path to output directory.")
    parser.add_argument("--plugins_dir", type=str, help="Path to Gemini science plugins directory.")
    args = parser.parse_args()

    # Load environment variables from .env if present
    load_dotenv()

    # Resolve Paths
    base_dir = Path(__file__).resolve().parent
    
    input_dir = args.input_dir or os.environ.get("PROTEOMIND_INPUT_DIR") or str(base_dir / "input")
    output_dir = args.output_dir or os.environ.get("PROTEOMIND_OUTPUT_DIR") or str(base_dir / "output")
    plugins_dir = args.plugins_dir or os.environ.get("SCIENCE_PLUGINS_DIR") or os.path.expanduser("~/.gemini/config/plugins/science")
    
    print("=========================================")
    print(" ProteoMind-AI Multi-Agent Pipeline")
    print("=========================================")
    print(f"Input Directory  : {input_dir}")
    print(f"Output Directory : {output_dir}")
    print(f"Plugins Directory: {plugins_dir}")
    print("=========================================\n")

    if not os.path.exists(input_dir):
        print(f"Error: Input directory {input_dir} does not exist.")
        print("Please ensure it contains 'upregulated_proteins.csv' and 'downregulated_proteins.csv'")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Annotate Proteins
    print("\n--- Agent 1: Protein Annotation (UniProt) ---")
    annotate_proteins.run(input_dir, output_dir)
    print("Annotation completed.\n")

    # Step 2: Pathway Enrichment (Reactome & HPA)
    print("--- Agent 2: Pathway & Localization Enrichment ---")
    run_pathway_enrichment.run(output_dir, plugins_dir)
    print("Enrichment completed.\n")

    # Step 3: Protein-Protein Interaction Network (STRING)
    print("--- Agent 3: PPI Network Analysis ---")
    run_string_ppi.run(output_dir, plugins_dir)
    print("PPI Network Analysis completed.\n")

    print("=========================================")
    print(" Pipeline Execution Finished Successfully!")
    print(f" Check the output directory: {output_dir}")
    print("=========================================")

if __name__ == "__main__":
    main()
