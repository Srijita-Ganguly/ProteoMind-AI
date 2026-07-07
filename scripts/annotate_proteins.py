import os
import pandas as pd
import requests
import json
import time

def process_genes(input_csv, output_csv):
    print(f"Processing {input_csv}...")
    df = pd.read_csv(input_csv)
    if 'Gene' not in df.columns:
        print("No 'Gene' column found.")
        return df, 0, 0, 0
    
    genes = df['Gene'].dropna().unique().tolist()
    total_processed = len(genes)
    
    # Chunking genes to avoid URL length limits
    chunk_size = 100
    annotated_data = []
    
    base_url = "https://rest.uniprot.org/uniprotkb/search"
    fields = "accession,protein_name,gene_names,organism_name,cc_function,cc_subcellular_location,protein_families,cc_disease,go_p,go_f,go_c,length"
    
    for i in range(0, len(genes), chunk_size):
        chunk = genes[i:i+chunk_size]
        query_genes = " OR ".join([f"gene_exact:{g}" for g in chunk])
        query = f"({query_genes}) AND (taxonomy_id:9606) AND (reviewed:true)"
        
        params = {
            "query": query,
            "fields": fields,
            "format": "tsv",
            "size": 500
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            if len(lines) > 1:
                header = lines[0].split('\t')
                for line in lines[1:]:
                    annotated_data.append(dict(zip(header, line.split('\t'))))
            
            time.sleep(1) # Be nice to the API
        except Exception as e:
            print(f"Error querying Uniprot: {e}")
            
    # Mapping back to dataframe
    # We will create a mapping from Gene Symbol to Uniprot record
    gene_to_record = {}
    for record in annotated_data:
        # A record can have multiple gene names separated by space
        gene_names = record.get('Gene Names', '').split()
        for gn in gene_names:
            if gn not in gene_to_record:
                gene_to_record[gn] = record
                
    success_count = 0
    missing_count = 0
    
    # Create new columns
    new_cols = {
        'UniProt Accession': [],
        'Recommended Protein Name': [],
        'Organism': [],
        'Protein Function': [],
        'Subcellular Location': [],
        'Protein Family': [],
        'Associated Diseases': [],
        'GO Biological Process': [],
        'GO Molecular Function': [],
        'GO Cellular Component': [],
        'Protein Length': []
    }
    
    for gene in df['Gene']:
        record = gene_to_record.get(gene)
        if record:
            success_count += 1
            new_cols['UniProt Accession'].append(record.get('Entry', ''))
            new_cols['Recommended Protein Name'].append(record.get('Protein names', ''))
            new_cols['Organism'].append(record.get('Organism', ''))
            new_cols['Protein Function'].append(record.get('Function [CC]', ''))
            new_cols['Subcellular Location'].append(record.get('Subcellular location [CC]', ''))
            new_cols['Protein Family'].append(record.get('Protein families', ''))
            new_cols['Associated Diseases'].append(record.get('Involvement in disease', ''))
            new_cols['GO Biological Process'].append(record.get('Gene Ontology (biological process)', ''))
            new_cols['GO Molecular Function'].append(record.get('Gene Ontology (molecular function)', ''))
            new_cols['GO Cellular Component'].append(record.get('Gene Ontology (cellular component)', ''))
            new_cols['Protein Length'].append(record.get('Length', ''))
        else:
            missing_count += 1
            for k in new_cols.keys():
                new_cols[k].append('')
                
    for k, v in new_cols.items():
        df[k] = v
        
    df.to_csv(output_csv, index=False)
    print(f"Saved {output_csv}")
    
    return df, total_processed, success_count, missing_count

def run(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    up_in = os.path.join(input_dir, "upregulated_proteins.csv")
    up_out = os.path.join(output_dir, "upregulated_proteins_annotated.csv")
    
    down_in = os.path.join(input_dir, "downregulated_proteins.csv")
    down_out = os.path.join(output_dir, "downregulated_proteins_annotated.csv")
    
    up_df, up_tot, up_succ, up_miss = process_genes(up_in, up_out)
    down_df, down_tot, down_succ, down_miss = process_genes(down_in, down_out)
    
    # Generate report
    report_path = os.path.join(output_dir, "uniprot_annotation_summary.md")
    report_content = f"""# UniProt Annotation Summary Report

## Overview
- **Total Proteins Processed**: {up_tot + down_tot}
- **Successfully Annotated**: {up_succ + down_succ}
- **Missing Annotations**: {up_miss + down_miss}

## Detailed Breakdown

### Upregulated Proteins
- **Processed**: {up_tot}
- **Annotated**: {up_succ}
- **Missing**: {up_miss}

### Downregulated Proteins
- **Processed**: {down_tot}
- **Annotated**: {down_succ}
- **Missing**: {down_miss}

## Notes
- Queries were restricted to Human (Taxonomy ID 9606) and reviewed entries.
- Missing entries typically occur if the gene symbol is not canonical or not reviewed in UniProtKB.
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Annotate proteins using UniProt")
    parser.add_argument("--input_dir", required=True, help="Path to input directory")
    parser.add_argument("--output_dir", required=True, help="Path to output directory")
    args = parser.parse_args()
    
    run(args.input_dir, args.output_dir)
