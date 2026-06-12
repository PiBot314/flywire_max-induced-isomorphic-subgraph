import csv
import os
import ast

def convert_motif_file(input_path, output_path, type):
    # Line 6: Read the entire raw text file
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Line 10: Normalize line endings and split blocks by double newlines
    content = content.replace('\r\n', '\n')
    blocks = content.strip().split('\n\n')
    
    motif_rows = []
    int_ids = []

    for block in blocks:
        # 1. Clean and split into individual lines
        raw_lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        # 2. Extract numeric IDs from the lists
        # Using eval() or ast.literal_eval is necessary because the lines 
        # look like string representations of lists (e.g., "['7205...', 'LC9']")
        for value in raw_lines:
            # print(value, ".", end="|")
            try:
                # value = ast.literal_eval(line)
                # Check if the first element is a digit-only string
                if value.isdigit():
                    int_ids.append(int(value))
            except (ValueError, SyntaxError):
                continue
        print(int_ids,"\n")
                
    # 3. Group the integers into trios
    for i in range(0, len(int_ids) - (len(int_ids) % 3), 3):
        motif_rows.append([int_ids[i], int_ids[i+1], int_ids[i+2], type])
            
    # Line 24: Write the structural rows into the specific output CSV file
    headers = ['neuron_a_id', 'neuron_b_id', 'neuron_c_id', 'type']
    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # writer.writerow("")
        # writer.writerow(headers)
        writer.writerows(motif_rows)
    print(f"Processed {len(motif_rows)} motifs. Output saved to '{output_path}'.")

if __name__ == "__main__":
    # Line 35: Set your specific input and output file names here
    input_file = "raw_motifs.txt"
    output_file = "mcns_motif.csv"
    types = ["SC", "BR", "VC", "VD", "FL", "CR"] 
    #refer motif_basic_thoughts.md for acronym full forms
    type = types[4]

    if os.path.exists(input_file):
        convert_motif_file(input_file, output_file, type)
    else:
        print(f"Error: The file '{input_file}' does not exist.")