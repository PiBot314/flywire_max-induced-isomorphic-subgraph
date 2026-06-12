import os
import pandas as pd
import igraph as ig

def process_neuron_graph(input_csv, graph_out, degree_out):
    # Line 6: Read CSV in chunks, enforcing string type for 64-bit ID preservation
    chunks = []
    cols = ['source neuron id', 'target neuron id']
    for chunk in pd.read_csv(input_csv, chunksize=1000000, usecols=cols, dtype={c: str for c in cols}):
        if chunk.isnull().values.any():
            chunk = chunk.dropna()
        chunks.append(chunk)
        
    # Line 13: Combine chunks into a single DataFrame
    df = pd.concat(chunks, ignore_index=True)
    
    # Line 16: Identify and drop duplicate directed edges
    initial_len = len(df)
    df.drop_duplicates(subset=cols, inplace=True)
    print(f"File: {input_csv} | Removed {initial_len - len(df)} duplicate edges out of {initial_len} lines.")
    
    # Line 21: Construct igraph directly from the DataFrame columns
    g = ig.Graph.DataFrame(df, directed=True, use_vids=False)
    
    # Line 24: Save the graph structure to disk
    g.write_picklez(graph_out)
    
    # Line 27: Extract node IDs and calculate degree metrics
    nodes = g.vs['name']
    in_degrees = g.indegree()
    out_degrees = g.outdegree()
    
    # Line 32: Output the metrics to a CSV file
    degree_df = pd.DataFrame({
        'neuron_id': nodes,
        'in_degree': in_degrees,
        'out_degree': out_degrees
    })
    degree_df.to_csv(degree_out, index=False)

if __name__ == "__main__":
    # Line 43: Define the 5 target edge list files
    files = ["/Users/arnav/agcode/flywire/qual_challenge/data/edgelists/BANC_edgelist.csv", 
             "/Users/arnav/agcode/flywire/qual_challenge/data/edgelists/FAFB_edgelist.csv", 
             "/Users/arnav/agcode/flywire/qual_challenge/data/edgelists/MANC_edgelist.csv", 
             "/Users/arnav/agcode/flywire/qual_challenge/data/edgelists/MAOL_edgelist.csv", 
             "/Users/arnav/agcode/flywire/qual_challenge/data/edgelists/MCNS_edgelist.csv"]
    
    for i, f in enumerate(files, start=1):
        if os.path.exists(f):
            process_neuron_graph(f, f"neuron_graph_{i}.pkl", f"neuron_degrees_{i}.csv")