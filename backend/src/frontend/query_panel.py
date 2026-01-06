import streamlit as st

def render_query_panel():
    """
    Renders the sidebar input for user queries.
    Returns the query string if submitted, else None.
    """
    st.sidebar.header("🔍 Knowledge Query")
    
    # Pre-filled examples for easier testing
    example = st.sidebar.selectbox(
        "Try an example:",
        [
            "",
            "List papers by Geoffrey Hinton",
            "What concepts are related to Deep Learning?",
            "Who wrote the paper 'Attention Is All You Need'?"
        ]
    )
    
    query_input = st.sidebar.text_area(
        "Or enter your own question:", 
        value=example if example else "",
        height=100
    )
    
    # "Run" button
    submit = st.sidebar.button("🚀 Run Analysis", type="primary")
    
    if submit and query_input:
        return query_input
    return None