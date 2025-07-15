import networkx as nx
import json
import random
import itertools
import matplotlib.pyplot as plt

# Load Graph
G = nx.read_graphml("karachi_graph.graphml")

# Load delivery node info
with open("delivery_nodes.json", "r") as f:
    data = json.load(f)

# Convert all node IDs to strings to match GraphML format
hq_node = str(data["hq_node"])  # Convert HQ node to string
selected = list(map(str, data["delivery_nodes_200"]))  # Convert delivery nodes to strings

# ----------------------------------------------
# Pre-processing Block (safe and debug-friendly)
# ----------------------------------------------

# Peek into one edge's data to understand available attributes
edges_sample = list(G.edges(data=True))[:5]
if edges_sample:
    print("Sample edge attributes:", list(edges_sample[0][2].keys()))
else:
    print("Graph has no edges! Please check the GraphML file.")
    exit()

# Determine which attribute to use for edge weight
# Try 'd10', else fall back to 'length', else raise error
sample_edge_attrs = edges_sample[0][2]
if 'd10' in sample_edge_attrs:
    weight_attr = 'd10'
elif 'length' in sample_edge_attrs:
    weight_attr = 'length'
else:
    raise ValueError("No usable weight attribute ('d10' or 'length') found in graph edges.")

# Remove edges that don't have the selected attribute
edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if weight_attr not in d]
print(f"Removing {len(edges_to_remove)} edges without '{weight_attr}'...")
G.remove_edges_from(edges_to_remove)

# Assign the length attribute for routing, convert to km if needed
for u, v, edge_data in G.edges(data=True):
    raw_value = float(edge_data[weight_attr])
    edge_data['length'] = raw_value / 1000 if raw_value > 1000 else raw_value  # auto scale meters to km

# Print edge length statistics
lengths = [d['length'] for _, _, d in G.edges(data=True)]
if lengths:
    print(f"Edge length stats — min: {min(lengths)}, max: {max(lengths)}, avg: {sum(lengths)/len(lengths):.2f}")
else:
    print("No valid edges remain after filtering. Please check the graph data.")
    exit()


# 2. Compute Distance Matrix
def compute_distance_matrix(G, nodes):
    """Compute all-pairs Dijkstra distances for given nodes."""
    D = {}
    for u in nodes:
        try:
            # Use networkx's dijkstra_path_length to get distances
            lengths = nx.single_source_dijkstra_path_length(G, u, weight='length')
            for v in nodes:
                # Only add if the node is reachable
                if v in lengths:
                    D[(u, v)] = lengths[v]
                else:
                    # If no path exists, use a very large number instead of infinity
                    D[(u, v)] = 1e9
        except nx.NetworkXNoPath:
            for v in nodes:
                D[(u, v)] = 1e9
    return D

# 3. Random Tour
def random_tour(hq, delivery_nodes, D):
    """Return a tour starting/ending at HQ in random order."""
    tour = random.sample(delivery_nodes, len(delivery_nodes))
    full_tour = [hq] + tour + [hq]
    
    # Handle potential missing connections
    try:
        cost = sum(D.get((full_tour[i], full_tour[i+1]), 1e9) for i in range(len(full_tour) - 1))
        return full_tour, cost
    except KeyError:
        return full_tour, float('inf')

# 4. Equal-Priority Tour via MST
def mst_tour(hq, delivery_nodes, D):
    """Return approximate tour using MST + preorder traversal."""
    nodes = [hq] + delivery_nodes
    G_complete = nx.Graph()
    
    for u, v in itertools.combinations(nodes, 2):
        G_complete.add_edge(u, v, weight=D.get((u, v), 1e9))

    try:
        mst = nx.minimum_spanning_tree(G_complete)
        tour = list(nx.dfs_preorder_nodes(mst, source=hq))
        tour.append(hq)  # return to HQ

        cost = sum(D.get((tour[i], tour[i+1]), 1e9) for i in range(len(tour) - 1))
        return tour, cost
    except nx.NetworkXError:
        return [hq], float('inf')

# 5. greedy_priority_tour
def get_user_priorities(nodes):
    """Prompt user to enter priorities for each delivery node."""
    priorities = {}
    print("\nSet priority for each node (1-10, 10=highest priority):")
    for node in nodes:
        while True:
            try:
                priority = int(input(f"Priority for node {node}: "))
                if 1 <= priority <= 10:
                    priorities[node] = priority
                    break
                else:
                    print("Please enter a value between 1 and 10")
            except ValueError:
                print("Invalid input. Please enter a number")
    return priorities

# Modified Priority-Based Tour with enhanced priority weighting
def priority_based_tour(hq, delivery_nodes, D, priority_map):
    """Tour that balances both priority and distance using a weighted score."""
    unvisited = delivery_nodes.copy()
    tour = [hq]
    current = hq
    
    while unvisited:
        # Calculate scores: 70% weight to priority, 30% to inverse distance
        scores = {
            node: (0.7 * priority_map[node]) + (0.3 * (1/D.get((current, node), 1e9)))
            for node in unvisited
        }
        
        next_node = max(unvisited, key=lambda x: scores[x])
        tour.append(next_node)
        unvisited.remove(next_node)
        current = next_node
    
    tour.append(hq)  # Return to HQ
    total_cost = sum(D.get((tour[i], tour[i+1]), 1e9) for i in range(len(tour)-1))
    return tour, total_cost


def dijkstra_tsp_tour(hq, delivery_nodes, G):
    """
    Solves the TSP using Dijkstra distances between nodes, ensuring each location
    and edge is visited only once. Returns an approximate tour.
    """
    import networkx as nx
    from networkx.algorithms.approximation import traveling_salesman_problem, greedy_tsp

    # Create complete graph with shortest path distances as edge weights
    all_nodes = [hq] + delivery_nodes
    complete_graph = nx.Graph()

    for u, v in itertools.combinations(all_nodes, 2):
        try:
            dist = nx.dijkstra_path_length(G, u, v, weight='length')
        except nx.NetworkXNoPath:
            dist = 1e9
        complete_graph.add_edge(u, v, weight=dist)

    # Approximate TSP using greedy heuristic
    tsp_tour = traveling_salesman_problem(complete_graph, cycle=True, method=greedy_tsp)

    # Calculate total cost based on complete_graph weights
    total_cost = sum(complete_graph[tsp_tour[i]][tsp_tour[i + 1]]['weight'] for i in range(len(tsp_tour) - 1))

    return tsp_tour, total_cost


if __name__ == "__main__":

    
    # Verify that all nodes are in the graph
    print("Graph nodes:", list(G.nodes())[:10], "...")  # Show first 10 nodes to verify format
    'print("Selected nodes:", [hq_node] + selected)'
    
    # Compute the distance matrix
    D = compute_distance_matrix(G, [hq_node] + selected)

    # Create priority map (ensure keys are strings)
    priority_map = {node: random.randint(1, 10) for node in selected}
    priority_map[hq_node] = 0  # HQ has no priority

    print("\n--- Random Tour ---")
    rtour, rcost = random_tour(hq_node, selected, D)
    print("Tour:", rtour)
    print("Total distance (km):", round(rcost / 1000, 2))

    print("\n--- MST Tour ---")
    mtour, mcost = mst_tour(hq_node, selected, D)
    print("Tour:", mtour)
    print("Total distance (km):", round(mcost / 1000, 2))

    print("\n--- Minimum Distance Tour (Dijkstra Chaining) ---")
    dtour, dcost = dijkstra_tsp_tour(hq_node, selected, G)
    print("Tour:", dtour)
    print("Total distance (km):", round(dcost / 1000, 2))

    # Get meaningful priorities from user instead of random
    priority_map = get_user_priorities(selected)
    priority_map[hq_node] = 0  # HQ has no priority

    print("\n--- Priority-Based Tour (User Defined) ---")
    ptour, pcost = priority_based_tour(hq_node, selected, D, priority_map)
    print("Tour:", ptour, "\n")
    print("Total distance (km):", round(pcost / 1000, 2), "\n")
    print("Priority sequence:", [priority_map[node] for node in ptour[1:-1]])
    
    '''
    # Print the first 50 nodes and their attributes
    print("First 50 Nodes and their attributes:")
    for node, data in list(G.nodes(data=True))[:20]:  # Slice to show only the first 50 nodes
        print(f"Node {node}: {data}")

    # Print the first 50 edges and their attributes (distances as weights)
    print("\nFirst 50 Edges and their attributes (distances as weights):")
    for u, v, data in list(G.edges(data=True))[:20]:  # Slice to show only the first 50 edges
        weight = data.get('length', 'No length attribute')  # Adjust according to your actual attribute name
        print(f"Edge ({u}, {v}) - Distance: {weight} km")
    '''

    '''   
    # Visualize the graph (Optional)
    plt.figure(figsize=(100, 100))
    pos = nx.spring_layout(G)  # You can use other layouts like `circular_layout`, `kamada_kawai_layout`, etc.
    nx.draw(G, pos, node_size=100, node_color='blue', with_labels=True, font_size=16, font_color='black', edge_color='gray')
    plt.title("Graph Visualization of Karachi Delivery Area")
    plt.show()
    '''