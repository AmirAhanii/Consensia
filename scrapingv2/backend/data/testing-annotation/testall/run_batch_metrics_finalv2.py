import json
from sklearn.metrics import cohen_kappa_score, fbeta_score, classification_report

# ==========================================
# CONFIGURATION: THE EVALUATION SETUP
# ==========================================
RESEARCHERS = [
    {
        "name": "Alexander Trautsch",
        "truth_file": "atrautsch_only_context.json",
        "predicted_file": "atrautsch_api_results.json",
        "truth_key": "atrautsch"
    },
    {
        "name": "Steffen Herbold",
        "truth_file": "sherbold_only_context.json",
        "predicted_file": "sherbold_api_results.json",
        "truth_key": "sherbold"
    },
    {
        "name": "Alireza Aghamohammadi",
        "truth_file": "aaghamohammadi_only_context.json",
        "predicted_file": "aaghamohammadi_api_results.json",
        "truth_key": "aaghamohammadi" 
    }
]

def calculate_scientific_scores():
    
    for researcher in RESEARCHERS:
        print("\n\n" + "="*60)
        print(f" 📊 SCIENTIFIC ANNOTATION SCORES: {researcher['name']} 📊 ")
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
            print(f"[!] API Results file not found for {researcher['name']}. Skipping.")
            continue

        y_true = []
        y_pred = []

        # 3. Flatten the hunks and extract Line-by-Line Labels
        for i, true_hunk in enumerate(ground_truth_data):
            hunk_idx = i + 1
            
            # Find the matching predicted hunk
            pred_hunk = next((h for h in predicted_data if h['hunk_number'] == hunk_idx), None)
            if not pred_hunk:
                continue
                
            # Extract Truth Labels
            true_labels_str = true_hunk.get(researcher['truth_key'], '{}')
            try:
                true_labels_dict = json.loads(true_labels_str)
            except json.JSONDecodeError:
                true_labels_dict = {}
                
            # Extract Predicted Labels
            pred_labels_dict = pred_hunk.get('labels', {})
            
            # Find the maximum line number in this hunk to build the array
            all_lines = set()
            for lines in true_labels_dict.values():
                all_lines.update(lines)
            for lines in pred_labels_dict.values():
                all_lines.update(lines)
                
            if not all_lines:
                continue
                
            max_line = max(all_lines)
            
            # 4. Compare Line-by-Line strictly
            for line_num in range(max_line + 1):
                if line_num not in all_lines:
                    continue
                    
                # Determine True Label
                t_label = 'unrelated' 
                for cat, lines in true_labels_dict.items():
                    if line_num in lines:
                        t_label = cat
                        break
                        
                # Determine Predicted Label
                p_label = 'unrelated'
                for cat, lines in pred_labels_dict.items():
                    if line_num in lines:
                        p_label = cat
                        break
                        
                y_true.append(t_label)
                y_pred.append(p_label)

        # 5. Compute Scientific Metrics
        if len(y_true) == 0:
            print("[!] No lines evaluated. Check if the API results are empty or mismatched.")
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