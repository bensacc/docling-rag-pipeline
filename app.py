import streamlit as st

from config import DATA_DIR, DB_PATH
from extract import build_index
from query import answer_question

st.title("File Directory Query")
st.caption("Ask questions about the contents of the files in this directory.")

# Index (or update the index for) whatever's in DATA_DIR once per session.
# build_index is incremental -- if nothing's new, this is fast.
if "indexed" not in st.session_state:
    with st.spinner(f"Indexing documents in {DATA_DIR} (first run may take a while)..."):
        build_index(DATA_DIR)
    st.session_state["indexed"] = True

with st.sidebar:
    st.caption(f"Data directory: {DATA_DIR}")
    if st.button("Check for new files"):
        with st.spinner("Checking for new files..."):
            build_index(DATA_DIR)
        st.success("Done.")

question = st.text_input("Ask a question:")

if st.button("Ask") and question:
    with st.spinner("Searching and generating answer..."):
        answer, results = answer_question(DB_PATH, question)

    # Streamlit's markdown renderer treats a bare "$" as the start of LaTeX
    # math, which mangles dollar amounts. Escape them so they render literally.
    st.markdown(answer.replace("$", "\\$"))

    with st.expander(f"Sources ({len(results)} chunks retrieved)"):
        for r in results:
            st.markdown(f"**{r['source']}** — page(s) {r['pages']}")
            st.caption(r["text"][:300] + ("..." if len(r["text"]) > 300 else ""))
            st.divider()
