

    '''   
    # Visualize the graph (Optional)
    plt.figure(figsize=(100, 100))
    pos = nx.spring_layout(G)  # You can use other layouts like `circular_layout`, `kamada_kawai_layout`, etc.
    nx.draw(G, pos, node_size=100, node_color='blue', with_labels=True, font_size=16, font_color='black', edge_color='gray')
    plt.title("Graph Visualization of Karachi Delivery Area")
    plt.show()
'''
'''
    # Verify that all nodes are in the graph
    print("Graph nodes:", list(G.nodes())[:10], "...")  # Show first 10 nodes to verify format
    print("Selected nodes:", [hq_node] + selected)
    
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

