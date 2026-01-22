import streamlit as st
import logging
import io

# Add project root to path to fix module not found errors
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.controller import Controller
from src.frontend.query_panel import render_query_panel
from src.frontend.graph_visualizer import render_graph
from src.frontend.explanation_panel import render_explanation
from src.frontend.logs_panel import render_logs

# Setup Logging Capture for UI
class StringHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_capture_string = io.StringIO()

    def emit(self, record):
        msg = self.format(record)
        self.log_capture_string.write(msg + '\n')

    def get_logs(self):
        return self.log_capture_string.getvalue().split('\n')

def main():
    # st.set_page_config(layout="wide", page_title="Ontology-Driven Knowledge Graph")
    
    
    # # Initialize Logger
    # if 'log_handler' not in st.session_state:
    #     handler = StringHandler()
    #     formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    #     handler.setFormatter(formatter)
    #     logging.getLogger().addHandler(handler)
    #     st.session_state.log_handler = handler
    
    st.set_page_config(layout="wide", page_title="Ontology-Driven Knowledge Graph")
    st.title("🧠 Ontology-Driven Knowledge System")
    
    # --- LOGGING REPAIR ---
    # We want to keep the terminal logs while CAPTURING them for the UI
    if 'log_handler' not in st.session_state:
        # Import setup_logging from utils to ensure terminal is active
        from src.utils import setup_logging
        setup_logging("INFO") # This turns the terminal back ON
        
        # Now add the special UI capture handler
        ui_handler = StringHandler()
        ui_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
        ui_handler.setFormatter(ui_formatter)
        
        logging.getLogger().addHandler(ui_handler)
        st.session_state.log_handler = ui_handler
    # ----------------------
    
    # Initialize Controller
    if 'controller' not in st.session_state:
        with st.spinner("Initializing Knowledge System..."):
            st.session_state.controller = Controller()
            st.success("System Online.")

    # --- SIDEBAR CONTROLS ---
    user_query = render_query_panel()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🕸️ Graph Options")
    view_mode = st.sidebar.radio(
        "Visualization Mode:",
        ["Focused Result", "Entire Knowledge Graph"],
        help="Focused: Shows only nodes related to your query.\nEntire: Shows the complete ontology graph."
    )

    # --- QUERY EXECUTION ---
    if user_query:
        # Clear previous logs
        st.session_state.log_handler.log_capture_string.truncate(0)
        st.session_state.log_handler.log_capture_string.seek(0)
        
        with st.spinner("Processing Query... (Phase 1 -> 2 -> 3 -> 4)"):
            result = st.session_state.controller.handle_user_query(user_query)
        
        # --- GRAPH DATA CONSTRUCTION ---
        graph_viz_data = {"nodes": [], "edges": []}
        seen_nodes = set()

        if view_mode == "Focused Result":
            # OPTION A: Build graph from Result Bindings only
            bindings = result.get("raw_result", {}).get("bindings", [])
            for row in bindings:
                for k, v in row.items():
                    # v is usually a string URI or Literal
                    if isinstance(v, str) and (v.startswith("http") or v.startswith("urn") or ":" in v):
                        node_id = v
                        # Simple label extraction
                        label = v.split("#")[-1] if "#" in v else v.split("/")[-1]
                        
                        # Color Logic
                        color = "#cccccc"
                        if "Author" in v or ("A" in label and label[1:].isdigit()): color = "#00cc66" # Green
                        if "Paper" in v or ("W" in label and label[1:].isdigit()): color = "#4da6ff"  # Blue
                        if "Concept" in v: color = "#ff9933" # Orange
                        
                        if node_id not in seen_nodes:
                            graph_viz_data["nodes"].append({
                                "id": node_id, "label": label, "title": v, "color": color
                            })
                            seen_nodes.add(node_id)
                            
            # Note: Edges are harder to infer purely from bindings unless the query explicitly selects ?p
            # For the focused view, we often just show the nodes found.

        else:
            # OPTION B: Build graph from the ENTIRE Ontology
            # We access the raw RDFLib graph from the controller
            full_graph = st.session_state.controller.ontology_manager.graph
            
            for s, p, o in full_graph:
                # Convert Subject
                s_id = str(s)
                s_label = s_id.split("#")[-1] if "#" in s_id else s_id.split("/")[-1]
                
                # Convert Object (only if it's a URI, skip huge literals for visual sanity)
                o_id = str(o)
                o_label = o_id.split("#")[-1] if "#" in o_id else o_id.split("/")[-1]

                # Color Logic for Subject
                s_color = "#cccccc"
                if "Author" in s_id or "A" in s_label[:2]: s_color = "#00cc66"
                if "Paper" in s_id or "W" in s_label[:2]: s_color = "#4da6ff"
                
                # Color Logic for Object
                o_color = "#cccccc"
                if "Author" in o_id: o_color = "#00cc66"
                if "Paper" in o_id: o_color = "#4da6ff"
                
                # Add Nodes
                if s_id not in seen_nodes:
                    graph_viz_data["nodes"].append({"id": s_id, "label": s_label, "title": s_id, "color": s_color})
                    seen_nodes.add(s_id)
                
                # Only add Object node if it's likely an entity (URI), not a text blob
                if "http" in o_id or "urn" in o_id: 
                    if o_id not in seen_nodes:
                        graph_viz_data["nodes"].append({"id": o_id, "label": o_label, "title": o_id, "color": o_color})
                        seen_nodes.add(o_id)
                    
                    # Add Edge
                    p_label = str(p).split("#")[-1]
                    graph_viz_data["edges"].append({
                        "from": s_id, "to": o_id, "label": p_label
                    })

        # --- PREPARE UI OUTPUT ---
        logs = st.session_state.log_handler.get_logs()
        
        ui_result = {
            "answer": result,
            "sparql": result.get("current_sparql", result.get("original_query", "N/A")),
            "graph": graph_viz_data,
            "agents_used": result.get("missing_terms", []),
            "logs": logs,
            "validation_status": "PASSED"
        }
        
        # Render Columns
        col1, col2 = st.columns([2, 1])
        
        with col1:
            render_graph(ui_result["graph"])
            render_explanation(ui_result)
            
        # with col2:
            # render_logs(ui_result["logs"])

if __name__ == "__main__":
    main()