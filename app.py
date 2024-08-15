import streamlit as st
from graph import app
from utils import create_initial_state
from langchain_core.runnables.config import RunnableConfig

# Title of the app
st.title("Competitive Coding Solver")

# Main section
st.write("## Input Section")
st.markdown("""
### Instructions:
Please input your problem in the following format:
1. **Problem Statement:** Provide the complete problem description followed by **'-----Example-----'** to signify the start of the test-cases.
2. **Input/Output Format:** Mention **'Input:'** followed by all the inputs. Then **'Output:'** followed by the outputs. End with a **'-----Note-----'**

**Example Format:**""")
problem_desc = st.text_area("Enter the problem here: ", height = 300, value="")

# Run your code based on the inputs
if st.button("Solve Problem"):
    # Insert your code logic here, using the parameters from the sidebar
    initial_state = create_initial_state(problem_desc)
    config = RunnableConfig(
        recursion_limit = 70,
        configurable = {"thread_id": "129"}
    )
    result = app.invoke(initial_state, config)
    success = False

    execution_result = result['code_exec_result']
    if execution_result['execution_successful'] and execution_result['output_matches']:
        st.success("Working solution was found")
        generated_code = result['generated_code']
        st.code(f"Generated code: {generated_code}", language="python")
    else:
        state_history = list(app.get_state_history(config))
        all_states = []
        relevant_states = []
        relevant_states_ids = []
        for i, state in enumerate(state_history):
            all_states.append(state)
            if i < len(state_history)-1 and i != 0:
                current_plan = state.values['cur_plan']
                next_plan = state_history[i+1].values['cur_plan']
                if current_plan and next_plan:
                    if current_plan == next_plan-1:
                        relevant_states.append(state)
        relevant_states.append(app.get_state(config))
        
        st.write("## Report of explored options:")
        st.divider()

        for i, state in enumerate(relevant_states):
            state_values = state.values
            st.write(f"## Path {i+1}")
            st.write(f"### Modified Plan {i+1} after debugging:")
            st.write(state_values['modified_plan'])
            st.write("### Confidence Score: ", state_values['plans'][i].confidence_score)
            code_exec_result = state_values['code_exec_result']
            st.write("### Code Execution Result: ", code_exec_result)
            st.divider()
        
        user_plan_choice = st.number_input(
            "Which plan seems most accurate?",
            min_value = 1, max_value = len(relevant_states),
            value = 1 ,
            placeholder = "Type 1 for Plan 1, 2 for Plan 2 etc..."
        )
        user_feedback = st.text_area(
            "Provide some feedback to assist in the debugging process.",
            placeholder = "Enter feedback/suggestion here..."
        )

        relevant_state_config = relevant_states[user_plan_choice-1].config
        debug_iterations = [0 if i == user_plan_choice-1 else 3 for i in range(3)]
        branch_config = app.update_state(
            relevant_state_config,
            {
                "cur_plan": user_plan_choice-1,
                "user_feedback": user_feedback,
                "taken_feedback": True,
                "debug_iterations": debug_iterations
            }
        )

        if st.button("Retry with feedback"):
            result = app.invoke(None, branch_config)


# Add more sections or outputs as needed
