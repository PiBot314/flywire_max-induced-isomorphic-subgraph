"""
Circuit Network Visualizer
==========================
Creates publication-quality network visualizations of the isomorphic circuit.
Supports multiple layout algorithms and styling options.

Usage:
    python visualize_circuit.py [--dataset BANC|FAFB|MAOL] [--layout spring|circular|hierarchical]
"""

import json
import pandas as pd
import igraph as ig
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import argparse
import sys
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = Path("/Users/arnav/agcode/flywire/qual_challenge/")
GRAPHS_DIR = DATA_DIR / "processed" / "graph"
CHECKPOINT_FILE = DATA_DIR / "network.json"
ANALYSIS_DIR = DATA_DIR / "analysis"
OUTPUT_DIR = DATA_DIR / "visualizations"

DATASET_NAMES = {
    1: "BANC",
    2: "FAFB",
    3: "MANC",
    4: "MAOL",
    5: "MCNS"
}

# Visualization settings
FIGURE_SIZE = (16, 12)
DPI = 300
NODE_SIZE_SCALE = 200
EDGE_WIDTH_SCALE = 2.0
FONT_SIZE = 8

# Color schemes
COLORS = {
    'hub': '#e74c3c',      # Red for high-degree hubs
    'medium': '#3498db',   # Blue for medium degree
    'low': '#95a5a6',      # Gray for low degree
    'isolated': '#ecf0f1', # Light gray for isolated
    'edge': '#34495e',     # Dark gray for edges
    'background': '#ffffff' # White background
}

# ============================================================================
# DATA LOADING
# ============================================================================

def load_checkpoint(checkpoint_path: Path) -> dict:
    """Load checkpoint JSON with circuit mapping."""
    with open(checkpoint_path, 'r') as f:
        return json.load(f)

def load_graph(dataset_idx: int) -> ig.Graph:
    """Load igraph from pickle file."""
    dataset_name = DATASET_NAMES[dataset_idx]
    graph_file = GRAPHS_DIR / f"{dataset_name}_graph.pkl"
    
    if not graph_file.exists():
        raise FileNotFoundError(f"Graph not found: {graph_file}")
    
    print(f"  Loading {dataset_name} graph...")
    return ig.Graph.Read_Picklez(str(graph_file))

def extract_induced_subgraph(graph: ig.Graph, neuron_ids: list) -> ig.Graph:
    """Extract induced subgraph for given neuron IDs."""
    vertex_indices = []
    
    for neuron_id in neuron_ids:
        try:
            v = graph.vs.find(name=str(neuron_id))
            vertex_indices.append(v.index)
        except ValueError:
            print(f"    Warning: Neuron {neuron_id} not found in graph")
    
    subgraph = graph.induced_subgraph(vertex_indices)
    
    # Preserve original neuron IDs as names
    for i, v_idx in enumerate(vertex_indices):
        subgraph.vs[i]['name'] = graph.vs[v_idx]['name']
    
    return subgraph

def load_degree_data(dataset_name: str) -> pd.DataFrame:
    """Load pre-computed degree data."""
    degree_file = ANALYSIS_DIR / f"{dataset_name}_degrees.csv"
    if degree_file.exists():
        return pd.read_csv(degree_file)
    return None

# ============================================================================
# LAYOUT ALGORITHMS
# ============================================================================

def compute_layout(subgraph: ig.Graph, layout_type: str = 'spring') -> list:
    """Compute node positions using specified layout algorithm."""
    print(f"  Computing {layout_type} layout...")
    
    if layout_type == 'spring':
        # Fruchterman-Reingold force-directed layout
        layout = subgraph.layout_fruchterman_reingold(niter=1000)
    elif layout_type == 'circular':
        # Circular layout
        layout = subgraph.layout_circle()
    elif layout_type == 'hierarchical':
        # Hierarchical layout based on in-degree
        layout = subgraph.layout_reingold_tilford(mode='in')
    elif layout_type == 'kamada_kawai':
        # Kamada-Kawai layout (good for small graphs)
        layout = subgraph.layout_kamada_kawai()
    elif layout_type == 'grid':
        # Grid layout
        layout = subgraph.layout_grid()
    else:
        # Default to spring
        layout = subgraph.layout_fruchterman_reingold()
    
    return layout.coords

# ============================================================================
# VISUALIZATION
# ============================================================================

def assign_node_colors(subgraph: ig.Graph, degree_df: pd.DataFrame = None) -> list:
    """Assign colors based on node degree."""
    colors = []
    
    for i in range(subgraph.vcount()):
        total_degree = subgraph.degree(i, mode='all')
        
        if total_degree == 0:
            colors.append(COLORS['isolated'])
        elif total_degree >= 4:
            colors.append(COLORS['hub'])
        elif total_degree >= 2:
            colors.append(COLORS['medium'])
        else:
            colors.append(COLORS['low'])
    
    return colors

def assign_node_sizes(subgraph: ig.Graph) -> list:
    """Assign node sizes based on degree."""
    sizes = []
    
    for i in range(subgraph.vcount()):
        total_degree = subgraph.degree(i, mode='all')
        # Size proportional to degree, with minimum size for isolated nodes
        size = max(NODE_SIZE_SCALE * (1 + total_degree), NODE_SIZE_SCALE * 0.5)
        sizes.append(size)
    
    return sizes

def create_network_visualization(
    subgraph: ig.Graph,
    layout_coords: list,
    dataset_name: str,
    degree_df: pd.DataFrame = None,
    show_labels: bool = True,
    highlight_components: bool = True
) -> plt.Figure:
    """Create publication-quality network visualization."""
    
    fig, ax = plt.subplots(figsize=FIGURE_SIZE, facecolor=COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    ax.set_aspect('equal')
    
    # Get node properties
    node_colors = assign_node_colors(subgraph, degree_df)
    node_sizes = assign_node_sizes(subgraph)
    
    # Convert layout to numpy array
    pos = np.array(layout_coords)
    
    # Draw edges first (so they appear behind nodes)
    edge_list = subgraph.get_edgelist()
    for edge in edge_list:
        src, tgt = edge
        x = [pos[src, 0], pos[tgt, 0]]
        y = [pos[src, 1], pos[tgt, 1]]
        
        ax.plot(x, y, color=COLORS['edge'], linewidth=EDGE_WIDTH_SCALE, 
                alpha=0.6, zorder=1)
        
        # Add arrow
        dx = pos[tgt, 0] - pos[src, 0]
        dy = pos[tgt, 1] - pos[src, 1]
        ax.arrow(pos[src, 0], pos[src, 1], dx*0.85, dy*0.85,
                head_width=0.3, head_length=0.2, fc=COLORS['edge'], 
                ec=COLORS['edge'], alpha=0.6, zorder=1, length_includes_head=True)
    
    # Highlight connected components if requested
    if highlight_components:
        components = subgraph.connected_components(mode='weak')
        for i, component in enumerate(components):
            if len(component) > 1:  # Only highlight non-isolated nodes
                comp_pos = pos[component]
                # Draw convex hull around component
                from scipy.spatial import ConvexHull
                if len(component) >= 3:
                    try:
                        hull = ConvexHull(comp_pos)
                        for simplex in hull.simplices:
                            ax.plot(comp_pos[simplex, 0], comp_pos[simplex, 1], 
                                   'r--', alpha=0.3, linewidth=1, zorder=0)
                    except:
                        pass
    
    # Draw nodes
    for i in range(subgraph.vcount()):
        ax.scatter(pos[i, 0], pos[i, 1], s=node_sizes[i], c=node_colors[i],
                  edgecolors='black', linewidths=1.5, zorder=2, alpha=0.9)
    
    # Add labels if requested
    if show_labels:
        for i in range(subgraph.vcount()):
            neuron_id = subgraph.vs[i]['name']
            # Truncate long IDs for readability
            label = neuron_id if len(neuron_id) <= 10 else f"{neuron_id[:8]}..."
            
            # Get degree for label
            degree = subgraph.degree(i, mode='all')
            label_text = f"{label}\n(d={degree})"
            
            ax.text(pos[i, 0], pos[i, 1], label_text, 
                   fontsize=FONT_SIZE, ha='center', va='center',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                            alpha=0.7, edgecolor='none'), zorder=3)
    
    # Add title and statistics
    n_nodes = subgraph.vcount()
    n_edges = subgraph.ecount()
    n_components = len(subgraph.connected_components(mode='weak'))
    is_connected = subgraph.is_connected(mode='weak')
    
    title = f"{dataset_name} Circuit Network\n"
    title += f"Nodes: {n_nodes} | Edges: {n_edges} | "
    title += f"Components: {n_components} | "
    title += f"Connected: {'YES' if is_connected else 'NO'}"
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Create legend
    legend_elements = [
        mpatches.Patch(color=COLORS['hub'], label='Hub (degree ≥ 4)'),
        mpatches.Patch(color=COLORS['medium'], label='Medium (degree 2-3)'),
        mpatches.Patch(color=COLORS['low'], label='Low (degree 1)'),
        mpatches.Patch(color=COLORS['isolated'], label='Isolated (degree 0)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10,
             framealpha=0.9, edgecolor='black')
    
    # Remove axes
    ax.axis('off')
    
    # Add warning if not connected
    if not is_connected:
        warning_text = "WARNING: Circuit is NOT weakly connected!\n"
        warning_text += f"Contains {n_components} disconnected components."
        ax.text(0.5, 0.02, warning_text, transform=ax.transAxes,
               fontsize=12, ha='center', va='bottom',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow',
                        alpha=0.8, edgecolor='red', linewidth=2),
               color='red', fontweight='bold')
    
    plt.tight_layout()
    return fig

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def visualize_circuit(dataset_name: str = 'MANC', layout_type: str = 'spring',
                     show_labels: bool = True, save_format: str = 'png'):
    """Main visualization function."""
    
    print("\n" + "="*70)
    print(f"CIRCUIT NETWORK VISUALIZATION - {dataset_name}")
    print("="*70 + "\n")
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Load checkpoint
    print("Loading checkpoint data...")
    checkpoint = load_checkpoint(CHECKPOINT_FILE)
    
    dataset_triple = checkpoint['dataset_triple']
    mapping = checkpoint['mapping']
    
    # Find dataset index
    dataset_idx = None
    for idx, name in DATASET_NAMES.items():
        if name == dataset_name:
            dataset_idx = idx
            break
    
    if dataset_idx not in dataset_triple:
        print(f"✗ Error: {dataset_name} not in checkpoint datasets")
        print(f"  Available: {[DATASET_NAMES[d] for d in dataset_triple]}")
        sys.exit(1)
    
    # Get neuron IDs for this dataset
    col_idx = dataset_triple.index(dataset_idx)
    neuron_ids = [mapping[str(i)][col_idx] for i in range(len(mapping))]
    
    print(f"  Circuit size: {len(neuron_ids)} neurons")
    
    # Load graph and extract subgraph
    graph = load_graph(dataset_idx)
    subgraph = extract_induced_subgraph(graph, neuron_ids)
    
    print(f"  Extracted subgraph: {subgraph.vcount()} nodes, {subgraph.ecount()} edges")
    
    # Load degree data
    degree_df = load_degree_data(dataset_name)
    
    # Compute layout
    layout_coords = compute_layout(subgraph, layout_type)
    
    # Create visualization
    print("  Creating visualization...")
    fig = create_network_visualization(
        subgraph, layout_coords, dataset_name, degree_df, show_labels
    )
    
    # Save figure
    output_file = OUTPUT_DIR / f"{dataset_name}_circuit_{layout_type}.{save_format}"
    fig.savefig(output_file, dpi=DPI, bbox_inches='tight', 
               facecolor=COLORS['background'])
    
    print(f"\n{'='*70}")
    print(f"Visualization saved to: {output_file}")
    print(f"{'='*70}\n")
    
    # Show statistics
    print("Circuit Statistics:")
    print(f"  Nodes: {subgraph.vcount()}")
    print(f"  Edges: {subgraph.ecount()}")
    print(f"  Density: {subgraph.density():.4f}")
    print(f"  Connected: {subgraph.is_connected(mode='weak')}")
    print(f"  Components: {len(subgraph.connected_components(mode='weak'))}")
    
    return fig

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Visualize isomorphic circuit network'
    )
    parser.add_argument('--dataset', type=str, default='MANC',
                       choices=['BANC', 'FAFB', 'MAOL'],
                       help='Dataset to visualize (default: MANC)')
    parser.add_argument('--layout', type=str, default='spring',
                       choices=['spring', 'circular', 'hierarchical', 
                               'kamada_kawai', 'grid'],
                       help='Layout algorithm (default: spring)')
    parser.add_argument('--no-labels', action='store_true',
                       help='Hide node labels')
    parser.add_argument('--format', type=str, default='png',
                       choices=['png', 'pdf', 'svg'],
                       help='Output format (default: png)')
    
    args = parser.parse_args()
    
    try:
        visualize_circuit(
            dataset_name=args.dataset,
            layout_type=args.layout,
            show_labels=not args.no_labels,
            save_format=args.format
        )
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

# Made with Bob
