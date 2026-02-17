import pandas as pd
import glob
import json
import os

def generate_excel():
    json_files = glob.glob("revenda*.json")
    all_data = []

    print(f"Found {len(json_files)} JSON files.")

    import re

    for filename in json_files:
        # Extract revenda name from filename
        # "revendagabriel.json" -> "Gabriel"
        basename = os.path.basename(filename)
        revenda_name = basename.replace("revenda", "").replace(".json", "").capitalize()
        
        print(f"Processing {basename} as '{revenda_name}'...")
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Data should be a list of dicts
            if isinstance(data, list):
                for item in data:
                    # Create a new dict with 'Revenda' as the first key (for DataFrame column order preference)
                    row = {"Revenda": revenda_name}
                    
                    # Ensure phone number has '+' prefix
                    if "telefone" in item:
                        phone = str(item["telefone"])
                        # Remove non-digits
                        digits = re.sub(r'[^\d]', '', phone)
                        if digits:
                            item["telefone"] = f"+{digits}"
                    
                    row.update(item)
                    all_data.append(row)
            else:
                print(f"Warning: {filename} does not contain a list.")
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        
        # Ensure 'Revenda' is the first column
        cols = ['Revenda'] + [c for c in df.columns if c != 'Revenda']
        df = df[cols]
        
        output_file = "revendas_consolidadas.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\nSuccessfully created '{output_file}' with {len(df)} records.")
    else:
        print("\nNo data found to save.")

if __name__ == "__main__":
    generate_excel()
