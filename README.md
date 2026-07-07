<img width="1774" height="887" alt="Thumbnail" src="https://github.com/user-attachments/assets/703145ac-c4df-4b6e-b929-2e499c40afd4" />

# ProteoMind-AI
Antigravity-based agentic platform for automated interpretation of proteomics-derived gene symbols using multiple databases.
## Introduction

Proteomics has become one of the most powerful approaches for understanding disease mechanisms by measuring protein abundance across biological samples. Differentially expressed proteins often provide insight into disease progression, potential biomarkers, and therapeutic targets. However, converting a list of significant proteins into meaningful biological knowledge requires integrating information from multiple biological databases, each providing different aspects of protein function and interaction.

Researchers commonly need to annotate proteins, identify enriched biological pathways, investigate tissue-specific expression, determine subcellular localization, and construct protein-protein interaction (PPI) networks before drawing biological conclusions. These tasks are typically performed using multiple independent tools and manual database queries, making the workflow time-consuming, repetitive, and difficult to reproduce.

---

## Problem Statement

Following differential expression analysis, researchers are often left with lists of significantly upregulated and downregulated proteins. Although identifying these proteins is an essential first step, interpreting their biological significance requires integrating information from several independent resources, including:

- UniProt for protein annotation
- Reactome for pathway enrichment
- Human Protein Atlas for tissue-specific and spatial protein expression
- STRING for protein-protein interaction networks

Performing these analyses manually for dozens or hundreds of proteins is labor-intensive and introduces unnecessary repetition, while switching between multiple databases can reduce reproducibility and increase the likelihood of errors.

---

## Why Use AI Agents?

The biological interpretation workflow naturally consists of several independent but connected tasks. Each task has a distinct objective and relies on different scientific knowledge sources. This makes the problem well suited to a multi-agent architecture.

Instead of creating one large application responsible for every analysis step, ProteoMind-AI decomposes the workflow into specialized agents, each responsible for a single stage of the biological interpretation process.

Each agent:

- Performs one clearly defined scientific task.
- Receives structured input from the previous stage.
- Produces standardized output for the next stage.
- Uses specialized scientific database skills where appropriate.
- Can be independently maintained, extended, or replaced.

This modular design improves maintainability, reproducibility, and scalability while reducing complexity.

---

## Solution

ProteoMind-AI is a multi-agent workflow that automates the biological interpretation of significant proteomics results.

Starting from lists of upregulated and downregulated proteins, the pipeline sequentially:

1. Annotates proteins using UniProt.
2. Performs pathway enrichment using Reactome.
3. Retrieves tissue expression and spatial localization from the Human Protein Atlas.
4. Constructs high-confidence protein-protein interaction networks using STRING.
5. Produces standardized CSV files and biological summary reports for downstream interpretation.

Rather than replacing established biological databases, ProteoMind-AI orchestrates them into a single reproducible workflow using specialized AI agents.

---

## Project Journey

The development of ProteoMind-AI followed the typical workflow of a proteomics interpretation study.

1. The workflow input are the significant proteins were separated into upregulated and downregulated groups from the differentially expressed proteins were identified from quantitative proteomics analysis.
2. A modular multi-agent workflow was designed so that each agent focused on one biological analysis task.
3. Existing scientific database skills available within the Antigravity ecosystem were integrated instead of developing custom database clients.
4. Each agent generated standardized intermediate outputs, allowing downstream analyses to remain reproducible and independent.
5. The final workflow produces annotated proteins, enriched pathways, tissue localization information, and protein-protein interaction networks suitable for biological interpretation.

<img width="1536" height="1024" alt="wokflow" src="https://github.com/user-attachments/assets/eb8c7352-dd24-4fa9-a799-430cb5a5cde2" />

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

# Applications

ProteoMind-AI is designed as a biological interpretation workflow for proteomics and functional genomics studies. Although it was developed using a differential proteomics use case, the workflow is applicable to any curated list of human gene symbols.

The workflow does **not** require the input to specifically contain both upregulated and downregulated proteins. Any curated list of human gene symbols can be supplied for annotation, pathway enrichment, and interaction analysis.

---

# Limitations

ProteoMind-AI is intended for downstream biological interpretation rather than statistical analysis.

Current limitations include:

- The workflow expects **human gene symbols** (HGNC-approved symbols) as the primary identifiers. Other identifier types (such as Ensembl IDs, RefSeq IDs, or custom protein identifiers) are not directly supported unless they are first mapped to gene symbols.
- The workflow does not perform differential expression analysis, fold-change calculation, or statistical hypothesis testing. These analyses should be completed before using ProteoMind-AI.
- The quality of annotations depends on the information available in the external biological databases (UniProt, Reactome, Human Protein Atlas, and STRING).
- Proteins or genes that cannot be mapped by the underlying databases may produce incomplete annotations.
- Protein-protein interaction results depend on the confidence scores and available evidence within the STRING database.
- The current workflow has been designed and validated for **Homo sapiens** datasets.
- ProteoMind-AI focuses on annotation and biological interpretation and does not perform predictive modeling, machine learning, or network inference beyond the information provided by the referenced databases.

Despite these limitations, the modular multi-agent architecture allows additional databases, identifier mapping utilities, statistical modules, or organism-specific workflows to be integrated in future versions.

---

## Acknowledgements

This project was developed as part of the **AI Agents: Intensive Vibe Coding Capstone Project**, organized by **Kaggle × Google**. The competition challenged participants to design and build practical AI agent systems using modern agentic workflows and vibe coding principles.

Competition page:

[AI Agents: Intensive Vibe Coding Capstone Project](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project?utm_source=chatgpt.com)

The complete multi-agent workflow, project architecture, and implementation were generated using **Google Antigravity**, guided through iterative user-defined prompts, workflow specifications, and project requirements. This project demonstrates prompt-driven agentic software engineering for constructing a modular bioinformatics pipeline for the biological interpretation of proteomics datasets.

The workflow integrates publicly available biological knowledge resources, including:

- UniProt
- Reactome
- Human Protein Atlas
- STRING

The developers and maintainers of these databases for providing high-quality biological annotations and interaction data that enable reproducible downstream analysis are gratefully acknowledged. 
