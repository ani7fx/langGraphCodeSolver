import streamlit as st
from graph import app
from utils import create_initial_state, extract_modified_plan
from langchain_core.runnables.config import RunnableConfig
import uuid

st.set_page_config(layout="wide", page_title="Code Solver")
st.title("Competitive Coding Solver")

def reset_state():
    st.session_state.problem_solved = False
    st.session_state.feedback_given = False
    st.session_state.relevant_states = []
    st.session_state.solution = None

# Initialize session state variables
if "problem_solved" not in st.session_state:
    st.session_state.problem_solved = False
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = False
if "relevant_states" not in st.session_state:
    st.session_state.relevant_states = []
if "solution" not in st.session_state:
    st.session_state.solution = None

# Display solution if it exists
if st.session_state.solution:
    st.success("Working solution was found")
    st.write("Generated code:")
    st.code(st.session_state.solution, language="python")
    if st.button("Start New Problem"):
        reset_state()
        st.rerun()

# Input Section
elif not st.session_state.problem_solved:
    st.write("## Input Section")
    st.markdown("""
    ### Instructions:
    Please input your problem in the following format:
    1. **Problem Statement:** Provide the complete problem description followed by **'-----Example-----'** to signify the start of the test cases.
    2. **Input/Output Format:** Mention **'Input:'** followed by all the inputs. Then **'Output:'** followed by the outputs. End with a **'-----Note-----'**

    **Example Format:**""")

    problem_desc = st.text_area(
        "Enter the problem here: ",
        height=300,
        placeholder="""
        <problem_description>
        "-----Example-----"
        "Input:"
        <inputs>
        "Output:"
        <outputs>
        "-----Note-----"
        """
    )

    if st.button("Solve Problem"):
        initial_state = create_initial_state(problem_desc)
        config = RunnableConfig(
            recursion_limit=70,
            configurable={"thread_id": str(uuid.uuid4())}
        )

        with st.spinner("Generating a solution..."):
            result = app.invoke(initial_state, config)

        execution_result = result['code_exec_result']
        if execution_result['execution_successful'] and execution_result['output_matches']:
            st.session_state.problem_solved = True
            st.session_state.solution = result['generated_code']
            st.rerun()
        else:
            state_history = list(app.get_state_history(config))
            relevant_states = []
            for i, state in enumerate(state_history):
                if i < len(state_history) - 1 and i != 0:
                    current_plan = state.values['cur_plan']
                    next_plan = state_history[i+1].values['cur_plan']
                    if current_plan is not None and next_plan is not None:
                        if current_plan == next_plan - 1:
                            relevant_states.append(state)
            relevant_states.append(app.get_state(config))
            st.session_state.relevant_states = relevant_states
            st.rerun()

# Feedback Section
elif not st.session_state.problem_solved and st.session_state.relevant_states:
    st.error("Working solution could not be found.")
    st.write("## Report of Explored Options:")
    st.divider()

    num_columns = min(len(st.session_state.relevant_states), 3)
    columns = st.columns(num_columns, gap="large")

    for i, state in enumerate(st.session_state.relevant_states):
        col = columns[i % num_columns]
        with col:
            st.write(f"## Path {i + 1}")
            st.write(f"### Modified Plan {i + 1} after debugging:")
            modified_plan = extract_modified_plan(state.values['modified_plan'])
            st.write(modified_plan)
            st.write("### Confidence Score:", state.values['plans'][i].confidence_score)
            st.write("### Code Execution Result:", state.values['code_exec_result'])
            st.divider()

    user_plan_choice = st.number_input(
        "Which plan seems most accurate?",
        min_value=1, max_value=len(st.session_state.relevant_states),
        value=1,
        help="Type 1 for Plan 1, 2 for Plan 2, etc."
    )

    user_feedback = st.text_area(
        "Provide some feedback to assist in the debugging process.",
        placeholder="Enter feedback/suggestion here..."
    )

    if st.button("Retry with Feedback"):
        if user_feedback.strip():
            relevant_state = st.session_state.relevant_states[user_plan_choice - 1]
            relevant_state_config = relevant_state.config

            debug_iterations = [0 if i == user_plan_choice - 1 else 3 for i in range(3)]
            branch_config = app.update_state(
                relevant_state_config,
                {
                    "cur_plan": user_plan_choice - 1,
                    "user_feedback": user_feedback,
                    "taken_feedback": True,
                    "debug_iterations": debug_iterations
                }
            )
            with st.spinner("Re-trying with user feedback..."):
                result = app.invoke(None, branch_config)
                execution_result = result['code_exec_result']
                if execution_result['execution_successful'] and execution_result['output_matches']:
                    st.session_state.problem_solved = True
                    st.session_state.solution = result['generated_code']
                    st.rerun()
                else:
                    st.error("Working code could not be found.")
                    st.write("Current code:")
                    st.code(result['generated_code'], language="python")
        else:
            st.warning("Please provide some feedback before retrying.")

if st.button("Start New Problem"):
    reset_state()
    st.rerun()