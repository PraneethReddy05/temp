import streamlit as st
import json

def render_explanation(result):
    """
    Renders the transparency and provenance panel.
    """
    st.subheader("🧠 Reasoning Trace & Provenance")
    
    # 1. Validation Badge
    status = result.get("validation_status", "UNKNOWN")
    if status == "PASSED":
        st.success("✅ **Ontology Validation Passed** (Constraints Checked)")
    else:
        st.warning(f"⚠️ **Validation Status:** {status}")

    # 2. SPARQL Query
    with st.expander("🔎 Final SPARQL Query", expanded=True):
        st.code(result.get("sparql", "# No query generated"), language="sparql")

    # 3. Agents Involved
    agents = result.get("agents_used", [])
    if agents:
        st.info(f"🤖 **Agents Invoked:** {', '.join(agents)}")
    else:
        st.write("🤖 **Agents Invoked:** None (Direct Answer)")

    # 4. Result Bindings (The Data)
    with st.expander("📊 Raw Data Bindings"):
        bindings = result.get("answer", {}).get("raw_result", {}).get("bindings", [])
        if bindings:
            st.dataframe(bindings)
        else:
            st.write("No bindings returned.")