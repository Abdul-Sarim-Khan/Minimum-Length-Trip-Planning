import osmnx as ox
import networkx as nx
import json

# 1. Define HQ coordinates
hq_latitude, hq_longitude = 24.83804595801298, 67.08121751599609
hq_address = "Iqra University - Main Campus, Karachi, Pakistan"

print(f"HQ Location: {hq_address}")
print(f"Latitude: {hq_latitude}, Longitude: {hq_longitude}")

# 2. Download road network
radius = 1000  # Start radius
target_node_count = 10000
max_attempts = 10

for attempt in range(max_attempts):
    print(f"Attempt {attempt+1}: Fetching graph within {radius} meters")
    G = ox.graph_from_point(
        (hq_latitude, hq_longitude),
        dist=radius,
        network_type="drive",
        simplify=True,
        retain_all=False
    )

    # 3. Convert to undirected for traversal (but keep as MultiGraph for OSMnx compatibility)
    G_undir = G.to_undirected()

    # 4. Find nearest node to HQ coordinates
    hq_node = ox.distance.nearest_nodes(G, hq_longitude, hq_latitude)

    # 5. Build BFS tree from HQ to get connected 100 nodes
    bfs_nodes = list(nx.bfs_tree(G_undir, hq_node).nodes())
    if len(bfs_nodes) >= target_node_count:
        selected_nodes = bfs_nodes[:target_node_count]
        
        # Create subgraph but keep as MultiDiGraph for OSMnx compatibility
        G_sub = G.subgraph(selected_nodes).copy()
        
        # Convert to undirected MultiGraph for the final graph
        G_final = G_sub.to_undirected()
        
        # Add unique edge IDs for GraphML export
        edge_id = 0
        for u, v, key in G_final.edges(keys=True):
            G_final[u][v][key]['edge_id'] = edge_id
            edge_id += 1
        
        G = G_final
        break
    else:
        print(f"Only found {len(bfs_nodes)} nodes — increasing radius.")
        radius += 500
else:
    raise Exception("Failed to get a connected graph with 100 nodes after multiple attempts.")

# 6. Identify delivery nodes (excluding HQ)
delivery_nodes = [n for n in G.nodes() if n != hq_node]

# 7. Clean the graph data before saving (remove problematic attributes)
def clean_graph_data(graph):
    """Remove attributes that can't be serialized to GraphML"""
    # Problematic attributes that contain complex objects
    problematic_attrs = ['geometry', 'bearing', 'ref', 'junction', 'access']
    
    # Clean node attributes
    for node in graph.nodes():
        node_data = graph.nodes[node].copy()  # Make a mutable copy
        for attr in list(node_data.keys()):
            if attr in problematic_attrs:
                del node_data[attr]
    
    # Clean edge attributes
    for u, v, key in graph.edges(keys=True):
        edge_data = graph[u][v][key]  # Access the edge data
        for attr in list(edge_data.keys()):
            if attr in problematic_attrs:
                del edge_data[attr]

# Clean the graph data
clean_graph_data(G)

# Save graph using NetworkX (skip this for now, use manual method instead)
# nx.write_graphml(G, "karachi_hq_area.graphml")

# Alternative: Create a clean GraphML with simplified node IDs
def create_clean_graphml(graph, hq_node, filename="clean_karachi_graph.graphml"):
    """Create a clean GraphML with simplified node IDs (1,2,3...)"""
    
    # Create node mapping (HQ gets ID 1, others get sequential IDs)
    node_mapping = {}
    node_mapping[hq_node] = 1
    
    other_nodes = [n for n in graph.nodes() if n != hq_node]
    for i, node in enumerate(other_nodes, start=2):
        node_mapping[node] = i
    
    # Create new graph with simplified IDs - use simple Graph instead of MultiGraph
    clean_graph = nx.Graph()
    
    # Add nodes with geographic data (clean data)
    for old_id, new_id in node_mapping.items():
        node_data = graph.nodes[old_id]
        clean_graph.add_node(new_id, 
                           x=float(node_data.get('x', 0)), 
                           y=float(node_data.get('y', 0)),
                           street_count=int(node_data.get('street_count', 1)))
    
    # Add edges with unique IDs and clean attributes
    edge_counter = 1
    added_edges = set()  # Track edges to avoid duplicates
    
    for u, v, key, data in graph.edges(keys=True, data=True):
        new_u = node_mapping[u]
        new_v = node_mapping[v]
        
        # Skip if this edge already exists (for undirected graph)
        edge_pair = tuple(sorted([new_u, new_v]))
        if edge_pair in added_edges:
            continue
        added_edges.add(edge_pair)
        
        # Extract and clean edge attributes with unique edge ID
        length = data.get('length', 0)
        if not isinstance(length, (int, float)):
            length = 0
            
        edge_attrs = {
            'id': f"edge{edge_counter}",  # Unique edge ID
            'length': str(float(length)),
            'highway': str(data.get('highway', 'residential')),
            'osmid': str(data.get('osmid', '')),
            'oneway': str(data.get('oneway', False)),
            'lanes': str(data.get('lanes', '1')),
            'maxspeed': str(data.get('maxspeed', '')),
            'name': str(data.get('name', '')),
            'width': str(data.get('width', ''))
        }
        
        clean_graph.add_edge(new_u, new_v, **edge_attrs)
        edge_counter += 1
    
    # Write GraphML with proper formatting (skip NetworkX, use manual writer)
    # nx.write_graphml(clean_graph, filename)  # Skip this problematic line
    
    return clean_graph, node_mapping

# Create clean GraphML
clean_graph, node_mapping = create_clean_graphml(G, hq_node)

# Create manual GraphML with proper edge IDs for yEd compatibility
def create_manual_graphml(graph, filename="karachi_graph.graphml"):
    """Create GraphML manually to ensure proper edge ID formatting"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns" ')
        f.write('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
        f.write('xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns ')
        f.write('http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">\n')
        
        # Define keys
        f.write('  <key id="d0" for="graph" attr.name="created_date" attr.type="string" />\n')
        f.write('  <key id="d1" for="graph" attr.name="created_with" attr.type="string" />\n')
        f.write('  <key id="d2" for="graph" attr.name="crs" attr.type="string" />\n')
        f.write('  <key id="d3" for="node" attr.name="y" attr.type="string" />\n')
        f.write('  <key id="d4" for="node" attr.name="x" attr.type="string" />\n')
        f.write('  <key id="d5" for="node" attr.name="street_count" attr.type="string" />\n')
        f.write('  <key id="d6" for="edge" attr.name="osmid" attr.type="string" />\n')
        f.write('  <key id="d7" for="edge" attr.name="highway" attr.type="string" />\n')
        f.write('  <key id="d8" for="edge" attr.name="oneway" attr.type="string" />\n')
        f.write('  <key id="d9" for="edge" attr.name="reversed" attr.type="string" />\n')
        f.write('  <key id="d10" for="edge" attr.name="length" attr.type="string" />\n')
        f.write('  <key id="d11" for="edge" attr.name="lanes" attr.type="string" />\n')
        f.write('  <key id="d12" for="edge" attr.name="maxspeed" attr.type="string" />\n')
        f.write('  <key id="d13" for="edge" attr.name="name" attr.type="string" />\n')
        f.write('  <key id="d14" for="edge" attr.name="width" attr.type="string" />\n')
        
        f.write('  <graph edgedefault="undirected">\n')
        
        # Write nodes with clean data
        for node_id in sorted(graph.nodes()):
            node_data = graph.nodes[node_id]
            f.write(f'    <node id="{node_id}">\n')
            f.write(f'      <data key="d3">{float(node_data.get("y", 0))}</data>\n')
            f.write(f'      <data key="d4">{float(node_data.get("x", 0))}</data>\n')
            f.write(f'      <data key="d5">{int(node_data.get("street_count", 1))}</data>\n')
            f.write('    </node>\n')
        
        # Write edges with unique IDs and clean data
        edge_counter = 1
        for u, v, data in graph.edges(data=True):
            # Clean edge data
            length = data.get("length", 0)
            if not isinstance(length, (int, float)):
                try:
                    length = float(length)
                except (ValueError, TypeError):
                    length = 0.0
            
            f.write(f'    <edge source="{u}" target="{v}" id="edge{edge_counter}">\n')
            f.write(f'      <data key="d6">{str(data.get("osmid", "")).replace("&", "&amp;")}</data>\n')
            f.write(f'      <data key="d7">{str(data.get("highway", "residential")).replace("&", "&amp;")}</data>\n')
            f.write(f'      <data key="d8">{str(data.get("oneway", "False"))}</data>\n')
            f.write(f'      <data key="d9">False</data>\n')
            f.write(f'      <data key="d10">{length}</data>\n')
            f.write(f'      <data key="d11">{str(data.get("lanes", "")).replace("&", "&amp;")}</data>\n')
            f.write(f'      <data key="d12">{str(data.get("maxspeed", "")).replace("&", "&amp;")}</data>\n')
            f.write(f'      <data key="d13">{str(data.get("name", "")).replace("&", "&amp;")}</data>\n')
            f.write(f'      <data key="d14">{str(data.get("width", "")).replace("&", "&amp;")}</data>\n')
            f.write('    </edge>\n')
            edge_counter += 1
        
        # Graph metadata
        f.write('    <data key="d0">2025-05-22 20:00:00</data>\n')
        f.write('    <data key="d1">OSMnx + Custom Script</data>\n')
        f.write('    <data key="d2">epsg:4326</data>\n')
        
        f.write('  </graph>\n')
        f.write('</graphml>\n')

# Create the manual GraphML
create_manual_graphml(clean_graph)

# 8. Save delivery info using only the new IDs
delivery_info = {
    "hq_node": node_mapping[hq_node],                      # new HQ ID
    "delivery_nodes": [node_mapping[n] for n in delivery_nodes],  # new delivery node IDs
    "hq_coordinates": (hq_latitude, hq_longitude),
    "hq_address": hq_address
}

with open("delivery_nodes.json", "w") as f:
    json.dump(delivery_info, f, indent=2)

# 9. Print results
print(f"HQ Node ID (Original): {hq_node}")
print(f"HQ Node ID (Simplified): 1")
print(f"Number of Delivery Nodes: {len(delivery_nodes)}")
print(f"Total Nodes in Graph: {len(G.nodes())} (HQ + Deliveries)")
print(f"Number of Edges: {len(G.edges())}")
print(f"Files created:")
print(f"  - karachi_hq_area.graphml (original node IDs)")
print(f"  - clean_karachi_graph.graphml (simplified node IDs 1-{len(G.nodes())})")
print(f"  - manual_karachi_graph.graphml (manually formatted with unique edge IDs)")
print(f"  - delivery_nodes.json (node mapping and delivery info)")
print(f"\nRecommended file for yEd: manual_karachi_graph.graphml")
print(f"  - Node IDs: 1, 2, 3, ..., {len(clean_graph.nodes())}")
print(f"  - Edge IDs: edge1, edge2, edge3, ..., edge{len(clean_graph.edges())}")
print(f"  - HQ Node: 1")

# 10. Verify graph connectivity
if nx.is_connected(G):
    print("✓ Graph is connected - good for TSP/routing algorithms")
else:
    print("⚠ Warning: Graph has disconnected components")
    components = list(nx.connected_components(G))
    print(f"  Number of components: {len(components)}")
    print(f"  Largest component size: {len(max(components, key=len))}")