import json
import os
import math

# The files we need to split
FILES_TO_SPLIT = [
    "aaghamohammadi_only_context.json",
    "atrautsch_only_context.json",
    "sherbold_only_context.json"
]

def create_splits():
    print("==================================================")
    print(" ✂️ STARTING 80/20 DATA SPLIT ✂️ ")
    print("==================================================")

    for filename in FILES_TO_SPLIT:
        if not os.path.exists(filename):
            print(f"[!] Warning: Could not find {filename}. Skipping.")
            continue

        # 1. Load the full dataset
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total_hunks = len(data)
        if total_hunks == 0:
            print(f"[!] {filename} is empty.")
            continue

        # 2. Calculate the split index (80%)
        split_index = math.floor(total_hunks * 0.8)

        # 3. Slice the arrays (Sequential split to preserve hunk structures)
        train_data = data[:split_index]
        test_data = data[split_index:]

        # 4. Generate new filenames
        base_name = filename.replace("_only_context.json", "")
        train_filename = f"{base_name}_train.json"
        test_filename = f"{base_name}_test.json"

        # 5. Save the 80% Training Set
        with open(train_filename, 'w', encoding='utf-8') as f:
            json.dump(train_data, f, indent=2)

        # 6. Save the 20% Testing Set
        with open(test_filename, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2)

        print(f"\n✅ {base_name}:")
        print(f"   Total Hunks: {total_hunks}")
        print(f"   Training Set (80%): {len(train_data)} hunks -> {train_filename}")
        print(f"   Testing Set (20%):  {len(test_data)} hunks -> {test_filename}")

    print("\n[SUCCESS] All datasets have been split successfully.")

if __name__ == "__main__":
    create_splits()