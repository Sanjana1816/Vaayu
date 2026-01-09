import networkx as nx
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import models

# --- 1. A Mocked Map of Our "World" ---
# In a real app, this would come from a database or a map service.
# For our project, this is perfect to demonstrate the algorithm.
# We define intersections (nodes) with their real-world coordinates.
MAP_NODES = {
    "A_Home": (-74.0060, 40.7128),         # Downtown
    "B_Intersection": (-73.9960, 40.7228), # Lower East Side
    "C_Risky_Area": (-73.9860, 40.7328),   # East Village (inside our risk zone)
    "D_Intersection": (-73.9950, 40.7428), # Flatiron District
    "E_Work": (-73.9850, 40.7528)          # Midtown near Grand Central
}

MAP_EDGES = [
    ("A_Home", "B_Intersection"),
    ("B_Intersection", "C_Risky_Area"),
    ("B_Intersection", "D_Intersection"),
    ("C_Risky_Area", "E_Work"),
    ("D_Intersection", "E_Work")
]

def get_edge_risk_weight(node1_coords: tuple, node2_coords: tuple, db: Session) -> int:
    """
    Calculates the "risk weight" of a street (edge).
    A street is considered risky if its midpoint falls within a defined RiskZone.
    """
    # Calculate the midpoint of the street segment.
    mid_lon = (node1_coords[0] + node2_coords[0]) / 2
    mid_lat = (node1_coords[1] + node2_coords[1]) / 2
    
    midpoint_wkt = f'POINT({mid_lon} {mid_lat})'
    geography_midpoint = func.ST_GeogFromText(midpoint_wkt)

    # Use the ST_DWithin function we know is correct for the Geography type.
    is_in_risk_zone = db.query(models.RiskZone).filter(
        func.ST_DWithin(models.RiskZone.zone, geography_midpoint, 0)
    ).first()

    # Assign a very high weight to risky streets to make Dijkstra's avoid them.
    if is_in_risk_zone:
        return 100  # High cost for risky path
    else:
        return 1    # Low cost for safe path

def create_map_graph(db: Session) -> nx.Graph:
    """
    Builds a networkx graph from our mocked map data.
    The weight of each edge is calculated based on its risk.
    """
    G = nx.Graph()
    for node_name, coords in MAP_NODES.items():
        G.add_node(node_name, pos=coords)

    for u, v in MAP_EDGES:
        weight = get_edge_risk_weight(MAP_NODES[u], MAP_NODES[v], db)
        G.add_edge(u, v, weight=weight)
        
    return G

def find_safest_route(start_node: str, end_node: str, db: Session):
    """
    The main function that finds the safest path between two nodes.
    It builds the graph and then runs Dijkstra's algorithm.
    """
    if start_node not in MAP_NODES or end_node not in MAP_NODES:
        return None 

    graph = create_map_graph(db)
    
    try:
        path_nodes = nx.dijkstra_path(graph, source=start_node, target=end_node, weight='weight')
        path_coordinates = [MAP_NODES[node] for node in path_nodes]
        
        return {"path_nodes": path_nodes, "path_coordinates": path_coordinates}
    except nx.NetworkXNoPath:
        return None