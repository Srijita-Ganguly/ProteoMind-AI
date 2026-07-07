import csv
import json
import subprocess
import os
import concurrent.futures
from collections import defaultdict
import math

def read_csv(filepath):
    data = []
    if not os.path.exists(filepath):
        return [], []
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

def get_evidence_string(row):
    ev = []
    if float(row.get('escore', 0)) > 0: ev.append("Experimental")
    if float(row.get('dscore', 0)) > 0: ev.append("Database")
    if float(row.get('tscore', 0)) > 0: ev.append("Textmining")
    if float(row.get('cscore', 0) if 'cscore' in row else 0) > 0: ev.append("Coexpression")
    if float(row.get('nscore', 0)) > 0: ev.append("Neighborhood")
    if float(row.get('fscore', 0)) > 0: ev.append("Fusion")
    if float(row.get('pscore', 0)) > 0: ev.append("Phylogenetic")
    return ", ".join(ev)

def build_network_stats(network_data, annotations):
    stats = defaultdict(lambda: {
        "interactors": set(),
        "scores": [],
        "evidence": [],
        "highest_interaction": "",
        "max_score": 0.0,
        "string_id": "",
        "gene_symbol": ""
    })
    
    for row in network_data:
        pA = row['preferredName_A']
        pB = row['preferredName_B']
        score = float(row.get('score', 0))
        ev = get_evidence_string(row)
        
        stats[pA]["interactors"].add(pB)
        stats[pA]["scores"].append(score)
        stats[pA]["evidence"].append(ev)
        stats[pA]["string_id"] = row['stringId_A']
        stats[pA]["gene_symbol"] = pA
        
        if score > stats[pA]["max_score"]:
            stats[pA]["max_score"] = score
            stats[pA]["highest_interaction"] = f"{pB} ({score})"
            
        stats[pB]["interactors"].add(pA)
        stats[pB]["scores"].append(score)
        stats[pB]["evidence"].append(ev)
        stats[pB]["string_id"] = row['stringId_B']
        stats[pB]["gene_symbol"] = pB
        
        if score > stats[pB]["max_score"]:
            stats[pB]["max_score"] = score
            stats[pB]["highest_interaction"] = f"{pA} ({score})"
            
    final_stats = {}
    for p, s in stats.items():
        avg_score = sum(s["scores"]) / len(s["scores"]) if s["scores"] else 0.0
        bp = " | ".join(annotations.get(p, {}).get("Process", []))
        mf = " | ".join(annotations.get(p, {}).get("Function", []))
        cc = " | ".join(annotations.get(p, {}).get("Component", []))
        all_annots = " | ".join([a for a in [bp, mf, cc] if a])
        
        final_stats[p] = {
            "STRING Protein Identifier": s["string_id"],
            "Gene Symbol": s["gene_symbol"],
            "Number of interacting proteins": len(s["interactors"]),
            "Interaction Partners": ", ".join(s["interactors"]),
            "Average interaction confidence score": round(avg_score, 3),
            "Highest confidence interaction": s["highest_interaction"],
            "Evidence Type": ", ".join(list(set(s["evidence"]))),
            "Biological Process": bp,
            "Molecular Function": mf,
            "Cellular Component": cc,
            "Functional Annotation": all_annots
        }
    return final_stats

def get_mapping(func_data):
    mapping = {}
    for row in func_data:
        inputs = row.get("inputGenes", "").split(",")
        prefs = row.get("preferredNames", "").split(",")
        for i, inp in enumerate(inputs):
            inp = inp.strip()
            if i < len(prefs):
                pref = prefs[i].strip()
                mapping[inp] = pref
                mapping[pref] = inp
    return mapping

def apply_enrichment(header, data, stats, mapping, new_cols):
    new_header = header + new_cols
    new_data = []
    for row in data:
        uniprot = row[0]
        pref_name = mapping.get(uniprot, uniprot)
        s = stats.get(pref_name, {})
        if not s and uniprot in stats:
            s = stats[uniprot]
            
        new_row = row + [
            s.get("STRING Protein Identifier", ""),
            s.get("Interaction Partners", ""),
            s.get("Number of interacting proteins", 0),
            s.get("Average interaction confidence score", ""),
            s.get("Highest confidence interaction", ""),
            s.get("Evidence Type", ""),
            s.get("Biological Process", ""),
            s.get("Molecular Function", ""),
            s.get("Cellular Component", ""),
            s.get("Functional Annotation", "")
        ]
        new_data.append(new_row)
    return new_header, new_data

def append_combined(network_data, annotations, regulation, combined_data):
    for row in network_data:
        pA = row['preferredName_A']
        pB = row['preferredName_B']
        score = row.get('score', 0)
        ev = get_evidence_string(row)
        
        bp = " | ".join(annotations.get(pA, {}).get("Process", []))
        mf = " | ".join(annotations.get(pA, {}).get("Function", []))
        cc = " | ".join(annotations.get(pA, {}).get("Component", []))
        func = " | ".join([a for a in [bp, mf, cc] if a])
        
        combined_data.append([pA, pB, score, ev, func, regulation])

def get_hubs(stats, top_n=5):
    sorted_stats = sorted(stats.items(), key=lambda x: x[1].get("Number of interacting proteins", 0), reverse=True)
    return sorted_stats[:top_n]

def get_highest_interactions(network_data, top_n=5):
    sorted_net = sorted(network_data, key=lambda x: float(x.get('score', 0)), reverse=True)
    return sorted_net[:top_n]

def parse_functional(func_data):
    annotations = defaultdict(lambda: defaultdict(list))
    for row in func_data:
        cat = row.get("category", "")
        desc = row.get("description", "")
        input_genes = row.get("inputGenes", "").split(",")
        for g in input_genes:
            g = g.strip()
            if g and len(annotations[g][cat]) < 3:
                annotations[g][cat].append(desc)
    return annotations

def run(output_dir, science_plugins_dir):
    STRING_DIR = os.path.join(science_plugins_dir, "skills", "string_database")
    TMP_DIR = os.path.join(output_dir, "tmp_string")
    
    os.makedirs(TMP_DIR, exist_ok=True)
    
    up_csv = os.path.join(output_dir, "upregulated_proteins_enriched.csv")
    down_csv = os.path.join(output_dir, "downregulated_proteins_enriched.csv")
    
    up_out = os.path.join(output_dir, "upregulated_ppi_network.csv")
    down_out = os.path.join(output_dir, "downregulated_ppi_network.csv")
    combined_out = os.path.join(output_dir, "combined_ppi_network.csv")
    summary_out = os.path.join(output_dir, "string_network_summary.md")
    
    up_header, up_data = read_csv(up_csv)
    down_header, down_data = read_csv(down_csv)
    
    up_genes = [row[0] for row in up_data if row[0]]
    down_genes = [row[0] for row in down_data if row[0]]
    
    print(f"Upregulated proteins: {len(up_genes)}")
    print(f"Downregulated proteins: {len(down_genes)}")
    
    def run_string_network(genes, tag):
        if not genes:
            return []
        out_file = os.path.join(TMP_DIR, f"{tag}_network.tsv")
        
        genes_str = " ".join(genes)
        cmd = ["uv", "run", "scripts/string_cli.py", "network", "--identifiers"] + genes + ["--species", "9606", "--required_score", "700", "--output", out_file]
        
        print(f"Running STRING network for {tag} ({len(genes)} proteins)...")
        subprocess.run(cmd, cwd=STRING_DIR, capture_output=True)
        
        network_data = []
        if os.path.exists(out_file):
            with open(out_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    network_data.append(row)
        return network_data
    
    def run_string_functional(genes, tag):
        if not genes:
            return []
        out_file = os.path.join(TMP_DIR, f"{tag}_functional.tsv")
        cmd = ["uv", "run", "scripts/string_cli.py", "functional-annotation", "--identifiers"] + genes + ["--species", "9606", "--output", out_file]
        
        print(f"Running STRING functional annotation for {tag} ({len(genes)} proteins)...")
        subprocess.run(cmd, cwd=STRING_DIR, capture_output=True)
        
        functional_data = []
        if os.path.exists(out_file):
            with open(out_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    functional_data.append(row)
        return functional_data
    
    up_network = run_string_network(up_genes, "up")
    down_network = run_string_network(down_genes, "down")
    
    up_func = run_string_functional(up_genes, "up")
    down_func = run_string_functional(down_genes, "down")
    
    up_annotations = parse_functional(up_func)
    down_annotations = parse_functional(down_func)
    
    up_stats = build_network_stats(up_network, up_annotations)
    down_stats = build_network_stats(down_network, down_annotations)
    
    new_cols = [
        "STRING Protein Identifier",
        "Interaction Partners",
        "Number of interacting proteins",
        "Average interaction confidence score",
        "Highest confidence interaction",
        "Evidence Type",
        "Biological Process",
        "Molecular Function",
        "Cellular Component",
        "Functional Annotation"
    ]
    
    up_mapping = get_mapping(up_func)
    down_mapping = get_mapping(down_func)
    
    up_out_header, up_out_data = apply_enrichment(up_header, up_data, up_stats, up_mapping, new_cols)
    down_out_header, down_out_data = apply_enrichment(down_header, down_data, down_stats, down_mapping, new_cols)
    
    write_csv(up_out, up_out_header, up_out_data)
    write_csv(down_out, down_out_header, down_out_data)
    
    combined_header = ["Source Protein", "Target Protein", "STRING Score", "Evidence Type", "Functional Annotation", "Regulation"]
    combined_data = []
    
    append_combined(up_network, up_annotations, "Upregulated", combined_data)
    append_combined(down_network, down_annotations, "Downregulated", combined_data)
    
    write_csv(combined_out, combined_header, combined_data)
    
    total_queried = len(up_genes) + len(down_genes)
    mapped_proteins = len(up_stats) + len(down_stats)
    no_match = total_queried - mapped_proteins
    total_interactions = len(up_network) + len(down_network)
    
    up_hubs = get_hubs(up_stats)
    down_hubs = get_hubs(down_stats)
    
    top_up_interactions = get_highest_interactions(up_network)
    top_down_interactions = get_highest_interactions(down_network)
    
    with open(summary_out, 'w', encoding='utf-8') as f:
        f.write("# STRING Protein-Protein Interaction Network Summary\n\n")
        f.write(f"- **Total proteins queried**: {total_queried}\n")
        f.write(f"- **Successfully mapped proteins**: {mapped_proteins}\n")
        f.write(f"- **Proteins with no STRING match**: {no_match}\n")
        f.write(f"- **Total interactions retrieved**: {total_interactions} (Score >= 0.7)\n\n")
        
        f.write("## Hub Proteins (Most Connected)\n\n")
        f.write("### Upregulated Network\n")
        for pref, stat in up_hubs:
            f.write(f"- **{pref}**: {stat['Number of interacting proteins']} interactions\n")
            
        f.write("\n### Downregulated Network\n")
        for pref, stat in down_hubs:
            f.write(f"- **{pref}**: {stat['Number of interacting proteins']} interactions\n")
            
        f.write("\n## Highest Confidence Interactions\n\n")
        f.write("### Upregulated\n")
        for row in top_up_interactions:
            f.write(f"- {row['preferredName_A']} - {row['preferredName_B']} (Score: {row['score']})\n")
            
        f.write("\n### Downregulated\n")
        for row in top_down_interactions:
            f.write(f"- {row['preferredName_A']} - {row['preferredName_B']} (Score: {row['score']})\n")
    
    print("Done. Cleaning up temp files...")
    for f in os.listdir(TMP_DIR):
        os.remove(os.path.join(TMP_DIR, f))
    os.rmdir(TMP_DIR)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--plugins_dir", required=True)
    args = parser.parse_args()
    run(args.output_dir, args.plugins_dir)
