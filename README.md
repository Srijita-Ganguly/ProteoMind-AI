# ProteoMind-AI

ProteoMind-AI is a multi-agent pipeline designed to automate proteomics data analysis. The pipeline performs biological annotation, pathway enrichment, and protein-protein interaction (PPI) network analysis on lists of upregulated and downregulated proteins.

## Features

This tool uses a pipeline of agents to process your data:
1. **Agent 1 (Annotation)**: Annotates proteins with UniProt metadata (names, functions, subcellular locations, GO terms).
2. **Agent 2 (Enrichment)**: Runs Reactome pathway enrichment and retrieves tissue/subcellular localization data from the Human Protein Atlas (HPA).
3. **Agent 3 (PPI Network)**: Constructs and analyzes protein-protein interaction networks using the STRING database.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (for running the underlying science plugins)

## Installation

1. Clone this repository.
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables by copying the example file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to point `SCIENCE_PLUGINS_DIR` to the location of the `science` plugin tools if they are not in the default location (`~/.gemini/config/plugins/science`).

## Usage

Place your input data in the `input/` directory. The pipeline expects two files:
- `input/upregulated_proteins.csv`
- `input/downregulated_proteins.csv`

Both files must contain a `Gene` column.

Run the entire multi-agent pipeline with a single command:

```bash
python main.py
```

### Command-line Arguments (Optional)

You can override the default paths via command-line arguments:

```bash
python main.py --input_dir /path/to/my/inputs --output_dir /path/to/my/outputs --plugins_dir /path/to/science/plugins
```

## Output

The pipeline generates several enriched CSV files and Markdown summaries in the `output/` directory:
- `*_annotated.csv`: Proteins mapped to UniProt features.
- `*_enriched.csv`: Proteins enriched with HPA expression data.
- `*_ppi_network.csv`: Interacting proteins with STRING network scores.
- `significant_reactome_pathways.csv`: Significantly enriched pathways.
- `pathway_enrichment_summary.md`: Summary of enrichment analysis.
- `string_network_summary.md`: Summary of PPI network hubs and interactions.
