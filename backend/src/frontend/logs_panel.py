import streamlit as st

def render_logs(log_buffer):
    """
    Renders the system logs captured during execution.
    """
    st.subheader("📜 System Execution Logs")
    
    with st.expander("View Internal Logs", expanded=False):
        if log_buffer:
            # logs come as a list of strings
            log_text = "\n".join(log_buffer)
            st.code(log_text, language="text")
        else:
            st.text("No logs available.")