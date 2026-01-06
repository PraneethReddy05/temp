import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os
import tempfile

def get_node_color(type_uri):
    """
    Maps ontology types to colors for visualization.
    """
    if "Paper" in type_uri: return "#4da6ff"    # Blue
    if "Author" in type_uri: return "#00cc66"   # Green
    if "Concept" in type_uri: return "#ff9933"  # Orange
    if "Institution" in type_uri: return "#9966ff" # Purple
    return "#cccccc" # Grey default

def render_graph(graph_data):
    """
    Renders an interactive graph from the backend data.
    """
    st.subheader("🕸️ Knowledge Graph Explorer")
    
    if not graph_data or not graph_data.get("nodes"):
        st.info("No graph data to display.")
        return

    # Create PyVis network
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)
    
    # Add nodes
    for node in graph_data["nodes"]:
        net.add_node(
            node["id"], 
            label=node["label"], 
            title=node["title"], # Tooltip
            color=node["color"],
            size=20
        )

    # Add edges
    for edge in graph_data["edges"]:
        net.add_edge(
            edge["from"], 
            edge["to"], 
            label=edge["label"],
            title=edge["label"]
        )

    # Physics options for better layout
    net.set_options("""
    var options = {
      "physics": {
        "hierarchicalRepulsion": {
          "nodeDistance": 150
        }
      }
    }
    """)

    # Save to temp file and render
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
            net.save_graph(tmp_file.name)
            # Read back the file content
            with open(tmp_file.name, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
        # Render in Streamlit
        components.html(html_content, height=620, scrolling=True)
        
    except Exception as e:
        st.error(f"Error visualizing graph: {e}")