import csv
import json
import subprocess
import os
import concurrent.futures

def read_csv(filepath):
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            data.append(row)
    return header, data

def write_csv(filepath, header, data):
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

def run(output_dir, science_plugins_dir):
    REACTOME_DIR = os.path.join(science_plugins_dir, "skills", "reactome_database")
    HPA_DIR = os.path.join(science_plugins_dir, "skills", "human_protein_atlas_database")
    TMP_DIR = os.path.join(output_dir, "tmp")
    
    os.makedirs(TMP_DIR, exist_ok=True)
    
    up_csv = os.path.join(output_dir, "upregulated_proteins_annotated.csv")
    down_csv = os.path.join(output_dir, "downregulated_proteins_annotated.csv")
    up_out = os.path.join(output_dir, "upregulated_proteins_enriched.csv")
    down_out = os.path.join(output_dir, "downregulated_proteins_enriched.csv")
    pathways_out = os.path.join(output_dir, "significant_reactome_pathways.csv")
    hpa_out = os.path.join(output_dir, "human_protein_atlas_summary.csv")
    summary_out = os.path.join(output_dir, "pathway_enrichment_summary.md")
    
    up_header, up_data = read_csv(up_csv)
    down_header, down_data = read_csv(down_csv)
    
    up_genes = [row[0] for row in up_data if row[0]]
    down_genes = [row[0] for row in down_data if row[0]]
    
    def run_reactome(genes, tag):
        gene_file = os.path.join(TMP_DIR, f"{tag}_genes.txt")
        with open(gene_file, "w") as f:
            f.write("\n".join(genes))
            
        json_out = os.path.join(TMP_DIR, f"{tag}_reactome.json")
        cmd = f'uv run scripts/reactome_analysis.py analyze --file "{gene_file}" --fdr 0.05 --output "{json_out}"'
        subprocess.run(cmd, shell=True, cwd=REACTOME_DIR, capture_output=True)
        
        if not os.path.exists(json_out):
            return []
            
        with open(json_out, 'r', encoding='utf-8') as f:
            try:
                res = json.load(f)
            except:
                return []
                
        token = res.get("summary", {}).get("token")
        if token:
            pathways_csv = os.path.join(TMP_DIR, f"{tag}_pathways.csv")
            cmd_dl = f'uv run scripts/reactome_analysis.py download-pathways --token "{token}" --output "{pathways_csv}"'
            subprocess.run(cmd_dl, shell=True, cwd=REACTOME_DIR, capture_output=True)
            if os.path.exists(pathways_csv):
                _, p_data = read_csv(pathways_csv)
                return p_data
        return []
    
    print("Running Reactome Analysis...")
    up_pathways = run_reactome(up_genes, "up")
    down_pathways = run_reactome(down_genes, "down")
    
    sig_pathways = []
    for p in up_pathways:
        try:
            fdr = float(p[6])
            if fdr < 0.05:
                sig_pathways.append([p[0], p[1], p[2], "Upregulated", p[12]])
        except:
            pass
            
    for p in down_pathways:
        try:
            fdr = float(p[6])
            if fdr < 0.05:
                sig_pathways.append([p[0], p[1], p[2], "Downregulated", p[12]])
        except:
            pass
    
    write_csv(pathways_out, ["Reactome ID", "Pathway Name", "Number of enriched proteins", "Regulation", "Associated Gene Symbols"], sig_pathways)
    
    print("Running HPA Analysis...")
    all_genes = list(set(up_genes + down_genes))
    
    def process_gene(gene):
        resolve_json = os.path.join(TMP_DIR, f"{gene}_resolve.json")
        cmd = f'uv run scripts/hpa_cli.py resolve-ensembl-id {gene} --output "{resolve_json}"'
        subprocess.run(cmd, shell=True, cwd=HPA_DIR, capture_output=True)
        
        ensembl_id = None
        if os.path.exists(resolve_json):
            try:
                with open(resolve_json, 'r') as f:
                    j = json.load(f)
                    ensembl_id = j.get("ensembl_id")
            except:
                pass
                
        if not ensembl_id:
            return None
            
        entry_json = os.path.join(TMP_DIR, f"{gene}_entry.json")
        cmd = f'uv run scripts/hpa_cli.py get-atlas-entry {ensembl_id} --output "{entry_json}"'
        subprocess.run(cmd, shell=True, cwd=HPA_DIR, capture_output=True)
        
        entry_data = {}
        if os.path.exists(entry_json):
            try:
                with open(entry_json, 'r') as f:
                    entry_data = json.load(f)
            except:
                pass
                
        tissue_json = os.path.join(TMP_DIR, f"{gene}_tissue.json")
        cmd = f'uv run scripts/hpa_cli.py get-tissue-expression {ensembl_id} --output "{tissue_json}"'
        subprocess.run(cmd, shell=True, cwd=HPA_DIR, capture_output=True)
        
        tissue_data = []
        if os.path.exists(tissue_json):
            try:
                with open(tissue_json, 'r') as f:
                    tissue_data = json.load(f)
            except:
                pass
                
        subcell_json = os.path.join(TMP_DIR, f"{gene}_subcell.json")
        cmd = f'uv run scripts/hpa_cli.py get-subcellular-location {ensembl_id} --output "{subcell_json}"'
        subprocess.run(cmd, shell=True, cwd=HPA_DIR, capture_output=True)
        
        subcell_data = {}
        if os.path.exists(subcell_json):
            try:
                with open(subcell_json, 'r') as f:
                    subcell_data = json.load(f)
            except:
                pass
                
        high_med_tissues = [t['tissue'] for t in tissue_data if t.get('level') in ('high', 'medium')]
        tissue_expr = ", ".join(high_med_tissues) if high_med_tissues else "Low/Not detected"
        
        protein_expr = entry_data.get("Tissue expression cluster", "")
        rna_expr = f"{entry_data.get('RNA tissue specificity', '')} - {entry_data.get('RNA tissue distribution', '')}"
        
        subcell_main = subcell_data.get("main_locations", [])
        if not subcell_main:
            subcell_main = entry_data.get("Subcellular main location", [])
        subcell_main_str = ", ".join(subcell_main) if isinstance(subcell_main, list) else str(subcell_main)
        
        subcell_add = subcell_data.get("additional_locations", [])
        if not subcell_add:
            subcell_add = entry_data.get("Subcellular additional location", [])
        subcell_add_str = ", ".join(subcell_add) if isinstance(subcell_add, list) else str(subcell_add)
        
        spatial_loc = f"Main: {subcell_main_str}; Additional: {subcell_add_str}"
        
        res = [gene, tissue_expr, protein_expr, rna_expr, subcell_main_str, spatial_loc]
        dict_res = {
            "HPA Tissue Expression": tissue_expr,
            "HPA Protein Expression": protein_expr,
            "HPA RNA Expression": rna_expr,
            "HPA Subcellular Localisation": subcell_main_str
        }
        return gene, res, dict_res
    
    hpa_summary = []
    hpa_results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_gene, gene): gene for gene in all_genes}
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            res = future.result()
            if res:
                gene, arr, d = res
                hpa_summary.append(arr)
                hpa_results[gene] = d
            if i % 20 == 0:
                print(f"Processed {i}/{len(all_genes)} genes...")
    
    write_csv(hpa_out, ["Gene Symbol", "Tissue Expression", "Protein Expression", "RNA Expression", "Subcellular Localisation", "Spatial Localisation"], hpa_summary)
    
    new_header = up_header + ["HPA Tissue Expression", "HPA Protein Expression", "HPA RNA Expression", "HPA Subcellular Localisation"]
    
    def enrich_data(data):
        enriched = []
        for row in data:
            gene = row[0]
            res = hpa_results.get(gene, {})
            new_row = row + [
                res.get("HPA Tissue Expression", ""),
                res.get("HPA Protein Expression", ""),
                res.get("HPA RNA Expression", ""),
                res.get("HPA Subcellular Localisation", "")
            ]
            enriched.append(new_row)
        return enriched
    
    up_enriched = enrich_data(up_data)
    down_enriched = enrich_data(down_data)
    
    write_csv(up_out, new_header, up_enriched)
    write_csv(down_out, new_header, down_enriched)
    
    with open(summary_out, 'w', encoding='utf-8') as f:
        f.write("# Pathway Enrichment Summary\n\n")
        f.write(f"- Upregulated genes analyzed: {len(up_genes)}\n")
        f.write(f"- Downregulated genes analyzed: {len(down_genes)}\n")
        f.write(f"- Significant pathways (Upregulated): {len([p for p in sig_pathways if p[3] == 'Upregulated'])}\n")
        f.write(f"- Significant pathways (Downregulated): {len([p for p in sig_pathways if p[3] == 'Downregulated'])}\n")
        f.write(f"- Proteins with HPA annotations: {len(hpa_summary)}\n")
    
    print("Cleanup tmp files...")
    for f in os.listdir(TMP_DIR):
        os.remove(os.path.join(TMP_DIR, f))
    os.rmdir(TMP_DIR)
    
    print("Enrichment done.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--plugins_dir", required=True)
    args = parser.parse_args()
    run(args.output_dir, args.plugins_dir)
