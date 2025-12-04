import sys
import json
import streamlit as st
from src.controller import Controller

def get_controller():
    """
    Initializes a singleton Controller and stores it in st.session_state.
    This prevents re-initializing on every Streamlit script rerun.
    """
    if 'controller' not in st.session_state:
        print("--- INITIALIZING NEW CONTROLLER (SINGLETON) ---")
        st.session_state.controller = Controller()
        print("--- CONTROLLER INITIALIZED ---")
    return st.session_state.controller

def run_cli_app(controller: Controller):
    """
    Runs the interactive Command Line Interface.
    """
    print("\n--- Ontology-Driven Knowledge System (Phase 3) ---")
    print("Type your question, or 'exit' to quit.")
    
    while True:
        try:
            query = input("\nEnter your question: ")
            if query.lower().strip() == 'exit':
                print("Exiting...")
                break
            
            if not query:
                continue
                
            result = controller.handle_user_query(query)
            
            print("\n--- Final Result ---")
            print(json.dumps(result, indent=2, default=str))
            
            if not result['is_empty']:
                print("\nBindings:")
                for binding in result['raw_result']['bindings']:
                    print(f"  - {binding}")

        except EOFError:
            print("\nExiting...")
            break
        except KeyboardInterrupt:
            print("\nExiting...")
            break

def run_streamlit_app():
    """
    Runs the optional Streamlit web interface.
    """
    st.set_page_config(layout="wide")
    st.title("🧠 Ontology-Driven Knowledge System (Phase 3)")
    st.subheader("Query your knowledge graph using natural language.")

    # Get the singleton controller from session state
    controller = get_controller()

    user_query = st.text_input(
        "Enter your question:", 
        "List papers by Geoffrey Hinton"
    )

    if st.button("Execute Query", type="primary"):
        if user_query:
            with st.spinner("Processing... (Phase 1 -> 2 -> 3)"):
                result = controller.handle_user_query(user_query)
            
            st.success("Query processed!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Final SPARQL Query")
                sparql_query = result.get('current_sparql', result.get('original_query', 'N/A'))
                st.code(sparql_query, language="sparql")

            with col2:
                st.subheader("Result Bindings")
                bindings = result.get('raw_result', {}).get('bindings', [])
                if not bindings:
                    st.warning("No results found.")
                else:
                    st.dataframe(bindings)
            
            st.subheader("Full JSON Response")
            st.json(result, expanded=False)
        else:
            st.warning("Please enter a question.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'streamlit':
        print("Starting Streamlit app... Access it in your browser.")
        # We no longer pass the controller here; the function handles it.
        run_streamlit_app()
    else:
        # CLI mode still needs its own controller instance.
        print("Starting CLI app...")
        cli_controller = Controller()
        run_cli_app(cli_controller)