from fixed_header_tabs import inject_fixed_header_with_tabs

inject_fixed_header_with_tabs(
    app_title="Clearwater Post Trade Data Bot",
    subtitle="Your AI Assistant for Market Post Trade Data Analytics"
)

# Use Streamlit tabs immediately after
tabs = st.tabs(["💬 Chat", "📊 Result Analysis"])

with tabs[0]:
    st.write("### Chat UI")
    for i in range(30):
        st.write(f"Bot response line {i+1}: ...")

with tabs[1]:
    st.write("### Result Analysis")
    st.write("Analysis content goes here...")
