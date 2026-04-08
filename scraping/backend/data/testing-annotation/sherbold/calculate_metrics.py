import json
from sklearn.metrics import cohen_kappa_score, fbeta_score, classification_report

def calculate_scientific_scores():
    # 1. Load Ground Truth (Real Steffen)
    with open('sherbold_only_context.json', 'r', encoding='utf-8') as f:
        ground_truth_data = json.load(f)

    # 2. Load Predictions (LLM Steffen)
    with open('sherbold_api_results.json', 'r', encoding='utf-8') as f:
        predicted_data = json.load(f).get('results', [])

    y_true = []
    y_pred = []

    # 3. Flatten the hunks into line-by-line classifications
    for i, true_hunk in enumerate(ground_truth_data):
        hunk_idx = i + 1
        
        # Find the matching hunk in the API results
        pred_hunk = next((h for h in predicted_data if h['hunk_number'] == hunk_idx), None)
        if not pred_hunk:
            continue
            
        # Parse the stringified JSON in the ground truth
        true_labels_str = true_hunk.get('sherbold', '{}')
        try:
            true_labels_dict = json.loads(true_labels_str)
        except json.JSONDecodeError:
            true_labels_dict = {}
            
        pred_labels_dict = pred_hunk.get('labels', {})
        
        # Determine the maximum line number in this specific hunk
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
                
            # Extract ground truth label (Default to 'unrelated' if unmapped)
            t_label = 'unrelated' 
            for cat, lines in true_labels_dict.items():
                if line_num in lines:
                    t_label = cat
                    break
                    
            # Extract predicted label
            p_label = 'unrelated'
            for cat, lines in pred_labels_dict.items():
                if line_num in lines:
                    p_label = cat
                    break
                    
            y_true.append(t_label)
            y_pred.append(p_label)

    # 5. Compute Scientific Metrics
    # Cohen's Kappa for Inter-Rater Reliability
    kappa = cohen_kappa_score(y_true, y_pred)
    
    # F2 Score (beta=2 favors recall). Using 'weighted' to account for class imbalance.
    f2_weighted = fbeta_score(y_true, y_pred, beta=2, average='weighted')
    f2_macro = fbeta_score(y_true, y_pred, beta=2, average='macro')

    # 6. Print Results for the Paper
    print("==================================================")
    print(" 🔬 SCIENTIFIC ANNOTATION SCORES (Line-Level) 🔬 ")
    print("==================================================")
    print(f"Total Lines Evaluated: {len(y_true)}")
    print(f"Cohen's Kappa (κ):     {kappa:.4f}  <-- Report this as Inter-Rater Reliability")
    print(f"F2-Score (Weighted):   {f2_weighted:.4f}  <-- Report this for classification strength")
    print(f"F2-Score (Macro):      {f2_macro:.4f}")
    print("==================================================\n")
    
    print("Detailed Classification Report (Standard F1/Precision/Recall):")
    print(classification_report(y_true, y_pred, zero_division=0))

if __name__ == "__main__":
    calculate_scientific_scores()