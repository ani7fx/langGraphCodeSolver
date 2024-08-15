import streamlit as st
from graph import app
from utils import create_initial_state
from langchain_core.runnables.config import RunnableConfig

# Title of the app
st.title("Competitive Coding Solver")

# Sidebar for user inputs
st.sidebar.header("Input Parameters")

# Add your input widgets in the sidebar
parameter1 = st.sidebar.number_input("Parameter 1", min_value=0, max_value=100, value=50)
parameter2 = st.sidebar.text_input("Parameter 2", value="default text")
# Add more inputs as required

# Main section
st.write("## Input Section")
st.markdown("""
### Instructions:
Please input your problem in the following format:
1. **Problem Statement:** Provide the complete problem description as a single paragraph.
2. **Input/Output Format:** After the problem description, include the input/output format.
3. **Example:** Finally, include an example with "Input:" and "Output:" sections.

**Example Format:**""")
problem_desc = st.text_area("Enter the problem here: ", height = 300, value="")

# Run your code based on the inputs
if st.button("Solve Problem"):
    # Insert your code logic here, using the parameters from the sidebar
    initial_state = create_initial_state(problem_desc)
    config = RunnableConfig(
        recursion_limit = 70,
        configurable = {"thread_id": "123"}
    )
    result = app.invoke(initial_state, config)
    generated_code = result['generated_code']
    st.write(f"Generated code: {generated_code}")

# Add more sections or outputs as needed
