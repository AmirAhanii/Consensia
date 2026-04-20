import json
from sklearn.metrics import cohen_kappa_score, fbeta_score, classification_report

# ==========================================
# CONFIGURATION: ADD ALL 3 RESEARCHERS HERE
# ==========================================
RESEARCHERS = [
    {
        "name": "Alireza Aghamohammadi",
        "truth_file": "aaghamohammadi_only_context.json",
        "predicted_file": "aaghamohammadi_fewshot_results.json",
        "truth_key": "aaghamohammadi" # The exact key in the JSON dict
    },
    {
        "name": "Alexander Trautsch",
        "truth_file": "atrautsch_only_context.json",
        "predicted_file": "atrautsch_fewshot_results.json",
        "truth_key": "atrautsch"
    },
    {
        "name": "Steffen Herbold",
        "truth_file": "sherbold_only_context.json",
        "predicted_file": "sherbold_fewshot_results.json",
        "truth_key": "sherbold"
    }
]

def calculate_scientific_scores():
    
    for researcher in RESEARCHERS:
        print("\n\n" + "="*60)
        print(f" 🔬 SCIENTIFIC ANNOTATION SCORES: {researcher['name']} 🔬 ")
        print("="*60)

        # 1. Load Ground Truth
        try:
            with open(researcher['truth_file'], 'r', encoding='utf-8') as f:
                ground_truth_data = json.load(f)
        except FileNotFoundError:
            print(f"[!] Ground truth file not found for {researcher['name']}. Skipping.")
            continue

        # 2. Load Predictions
        try:
            with open(researcher['predicted_file'], 'r', encoding='utf-8') as f:
                predicted_data = json.load(f).get('results', [])
        except FileNotFoundError:
            print(f"[!] API Results file not found for {researcher['name']}. Have you run the annotation script yet?")
            continue

        y_true = []
        y_pred = []

        # 3. Flatten the hunks
        for i, true_hunk in enumerate(ground_truth_data):
            hunk_idx = i + 1
            
            pred_hunk = next((h for h in predicted_data if h['hunk_number'] == hunk_idx), None)
            if not pred_hunk:
                continue
                
            # Use the dynamic truth_key mapped to this specific researcher
            true_labels_str = true_hunk.get(researcher['truth_key'], '{}')
            try:
                true_labels_dict = json.loads(true_labels_str)
            except json.JSONDecodeError:
                true_labels_dict = {}
                
            pred_labels_dict = pred_hunk.get('labels', {})
            
            all_lines = set()
            for lines in true_labels_dict.values():
                all_lines.update(lines)
            for lines in pred_labels_dict.values():
                all_lines.update(lines)
                
            if not all_lines:
                continue
                
            max_line = max(all_lines)
            
            # 4. Compare Line-by-Line
            for line_num in range(max_line + 1):
                if line_num not in all_lines:
                    continue
                    
                t_label = 'unrelated' 
                for cat, lines in true_labels_dict.items():
                    if line_num in lines:
                        t_label = cat
                        break
                        
                p_label = 'unrelated'
                for cat, lines in pred_labels_dict.items():
                    if line_num in lines:
                        p_label = cat
                        break
                        
                y_true.append(t_label)
                y_pred.append(p_label)

        # 5. Compute Metrics
        if len(y_true) == 0:
            print("[!] No lines evaluated. Check file matching.")
            continue

        kappa = cohen_kappa_score(y_true, y_pred)
        f2_weighted = fbeta_score(y_true, y_pred, beta=2, average='weighted', zero_division=0)
        f2_macro = fbeta_score(y_true, y_pred, beta=2, average='macro', zero_division=0)

        # 6. Print Results
        print(f"Total Lines Evaluated: {len(y_true)}")
        print(f"Cohen's Kappa (κ):     {kappa:.4f}")
        print(f"F2-Score (Weighted):   {f2_weighted:.4f}")
        print(f"F2-Score (Macro):      {f2_macro:.4f}")
        print("-" * 60)
        print("Detailed Classification Report:")
        print(classification_report(y_true, y_pred, zero_division=0))

if __name__ == "__main__":
    calculate_scientific_scores()