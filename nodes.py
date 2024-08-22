from typing import List
from langchain_core.prompts import ChatPromptTemplate
from models import GraphState, Exemplar, RetrievedProblem, Plan, parser
from utils import mask_output, extract_expected_output, extract_sample_io, extract_outputs, extract_problem_without_testcase, test_code
from llm import model
# from app import update_progress

def run_test_case_analysis(state:GraphState):
    print("-----GENERATING INITIAL TEST CASE ANALYSIS-----")
    # update_progress("-----GENERATING INITIAL TEST CASE ANALYSIS-----")
    original_problem = state['problem']
#     original_problem = question
    test_case_analysis_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a professional programmer proficient in analysing test-cases.
                You are provided a problem, and its associated test case(s) comprising input and output.
                Provide an analysis on how the given input leads to the given output.
                
                Let's analyze the test case(s) step by step. Your response MUST adhere to the following
                structure/format, fill in all the '<?>'s only with the required info for each test case:
                Note:
                - Put all the analysis in the '<?>' after analysis only. 
                - Mention the output only where needed in the response schema.
                - And also do not use curly brackets anywhere in your response
                
                Problem : {original_problem}
                
                Response structure/format:
                <?> The input is: <?>. The output is <?>. Analysis: <?>. Therefore, the expected
                output is <?>
                """
            )
        ]
    )
    test_case_analysis_chain = test_case_analysis_prompt | model
    initial_understanding = test_case_analysis_chain.invoke({'original_problem': original_problem})
#     return initial_understanding.content
    state['test_case_analysis'] = initial_understanding.content
    expected_outputs = extract_outputs(initial_understanding.content)
    expected_outputs = [s.strip('"') for s in expected_outputs]
    state['expected_output'] = expected_outputs
    print(initial_understanding.content)
    return state

def correctness_checking(state:GraphState):
    print("-----INFERRING OUTPUT FROM TEST CASE ANALYSIS-----")
    # update_progress("-----INFERRING OUTPUT FROM TEST CASE ANALYSIS-----")
    #     initial_understanding = r
    #     original_problem = question
    
    initial_understanding = state['test_case_analysis']
    original_problem = state['problem']
    
    masked_initial_understanding = mask_output(initial_understanding)
    print("MASKED INITAL UNDERSTANDING --- ")
    print(masked_initial_understanding)
    problem_without_testcase = extract_problem_without_testcase(original_problem)
    print("PROBLEM WITHOUT TESTCASE----")
    print(problem_without_testcase)
    
    correctness_checking_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system"
                """
                Problem Description: {problem_without_testcase}
                
                Initial understanding: {masked_initial_understanding}
                
                # Instructions:
                You have been provided a coding problem and an understanding of its logic.
                The understanding comprises of a test case analysis where for each test case you are given:
                - The input
                - The analysis, which mentions how the given input leads to the output.
                Your task is to follow the given analysis, and infer the expected output for the test-case(s).
                
                Your response MUST adhere to the format below only, fill in the <?>s with the required information:
                
                Response format: <?> Therefore, the expected output is <?>
                
                """
            )
        ]
    ).partial(problem_without_testcase=problem_without_testcase)
    correctness_checking_chain = correctness_checking_prompt | model
    inferred_output = correctness_checking_chain.invoke({"masked_initial_understanding":masked_initial_understanding})
#     return inferred_output.content
    state['inferred_output'] = inferred_output.content
    print(inferred_output.content)
    
    expected_outputs = state['expected_output']
    inferred_outputs = extract_outputs(inferred_output.content)
    
    print(f"expected outputs: {expected_outputs}")
    print(f"inferred outputs: {inferred_outputs}")
    
    if len(expected_outputs) != len(inferred_outputs):
        state['correct_understanding'] = False
        return state
    for i in range(len(expected_outputs)):
        if expected_outputs[i] != inferred_outputs[i]:
            state['correct_understanding'] = False
            return state
        
    state['correct_understanding'] = True
    return state

def misunderstanding_fixing(state:GraphState):
    print("-----DESICION: REFINING TEST CASE ANALYSIS-----")
    # update_progress("-----DESICION: REFINING TEST CASE ANALYSIS-----")
    original_problem = state['problem']
    current_understanding = state['test_case_analysis']
    inferred_output = state['inferred_output']
    
#     original_problem = question
#     current_understanding = r
#     inferred_output = c
    misunderstanding_fixing_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are an advanced programmer, proficient in competitive coding and test-case analysis.
                You are provided a coding problem and an analysis of its test cases.
                This test case analysis was used (with the outputs masked) to infer the output from the input test cases,
                but it was incorrect in doing so, meaning that the initial test-case analysis was not accurate or
                descriptive enough. You are also provided with that inferred output.
                
                # Problem Specification: {original_problem}
                
                # Test Case Analysis: {current_understanding}
                
                # Inferred Output from understanding: {inferred_output}
                
                # Your task:
                Analyze why the current understanding(current test-case analysis) is not sufficient to infer the correct output for the test cases.
                Refine and update the understanding of the problem specification to produce the correct output for all the test cases, i.e. provide
                a refined analysis on how the given input leads to the given output provided in the original problem. Do so by
                carefully understanding the problem and breaking down its logic. The test-cases given are 100% correct, it is
                simply your task to correctly break down how the input leads to that output.
                - And also do not use curly brackets anywhere in your response
                
                Let's analyze the test case(s) step by step. Your response MUST adhere to the following
                structure/format, fill in all the '<?>'s only with the required info for each test case:
                
                Response Schema for each test case:
                <?> The input is <?>. The output is <?>. Analysis: <?>. Therefore, the expected
                output is <?>
                """
            )
        ]
    )
    misunderstanding_fixing_prompt_formatted = misunderstanding_fixing_prompt.partial(
        current_understanding=current_understanding,
        inferred_output=inferred_output
    )
    misunderstanding_fixing_chain = misunderstanding_fixing_prompt_formatted | model
    fixed_anaysis = misunderstanding_fixing_chain.invoke({"original_problem":original_problem})
#     return fixed_anaysis.content
    print(fixed_anaysis.content)
    state['test_case_analysis'] = fixed_anaysis.content
    state['test_case_analysis_iterations'] += 1
    return state

def retrieval_agent(state: GraphState) -> GraphState:
    print("-----RETRIEVING RELEVANT PROBLEMS-----")
    # update_progress("-----RETRIEVING RELEVANT PROBLEMS-----")
    original_problem = state['problem']
    retrieval_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are a retrieval agent. Your task is to assist in solving
                competitive programming problems by recalling similar relevant problems,
                identifying the underlying algorithm, and providing step-by-step solutions
                and detailed plans for each problem. Follow the instructions carefully and provide
                your response in the specified format.

                Here is the question:{question}

                Task instructions:
                1. Recall 3 relevant and distinct problems (different from the problem given above)
                    - They must not be a rephrasing of the original problem or a slight modification of it.
                    - You must ensure each problem is distinct and highlights a different aspect of the approach
                    needed to solve the original problem. Do NOT repeat any problems.
                    - The problems must be relevant and helpful towards solving the original problem.
                2. For each problem :
                    - Provide a description of the problem.
                    - Generate python code to solve that problem.
                    - Finally, generate a plan to solve that problem
                    - Identify the algorithm (Brute-force, Dynamic Programming, 
                    Divide-and-conquer, Greedy, Backtracking, Recursive, Binary search, and so on) 
                    behind it that can be used to solve the original problem and provide a high-level tutorial about it.
                    Do not include any curly brackets within the content of the response.

                Your response MUST be a JSON object that follows this schema (but provide actual content):
                {format_instructions}

                            Do NOT provide a JSON schema or describe the structure; provide the actual content.
                """
            ),
    #         ("placeholder", "{messages}"),
        ]
    ).partial(format_instructions = parser.get_format_instructions())
    
    retrieval_chain = retrieval_prompt | model | parser
    problems = retrieval_chain.invoke({'question': original_problem})
    state['relevant_problems'] = problems
    return state

def planning_agent(state: GraphState) -> GraphState:
    print("-----GENERATING PLANS-----")
    # update_progress("-----GENERATING PLANS-----")
    original_problem = state['problem']
    relevant_problems = state['relevant_problems']
    correct_understanding = state['correct_understanding']
    list_of_plans: List[Plan] = []
        
    base_prompt = """
            You are an advanced planning agent designed to create detailed
            step-by-step plans for solving competitive programming problems.
            You have been provided with a self-retrieved example problem and
            its associated solution. Your task is to generate a concrete plan that includes
            every necessary step to solve a new, original problem. The plan should incorporate
            insights from the provided example. Provide the plan in sequential steps.
            
            - Make sure you do not include any curly brackets in your response. - 

            Relevant problem:
            {description}

            Planning:
            {planning}

            Relevant algorithm: {algorithm}

            Problem to be solved:{original_problem}
    """
    if correct_understanding:
        test_case_analysis = state['test_case_analysis']
        formatted_planning = f"""
        Analysis of the test cases: {test_case_analysis}
        
        Use the provided test case analysis to help guide your planning process
        """
        base_prompt += f"\n{formatted_planning}"
        
    further_instructions = """
        Make sure to 
            - describe in detail how to handle inputs for the problem
            - Analyze the problem to be solved carefully and do not make any logical errors
            - break down the core logic of the problem, detailing each step
            - and also identify potential edge cases and how to handle them.
            Respond with only the planning to solve the problem. Do not write any code.
            Use a Chain-Of-Thought sequence to break down the steps required to solve the problem.
            If you follow all these instructions carefully, I will give you 1000 Euros.
    """
    base_prompt += further_instructions
    
    planning_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                base_prompt
            )
        ]
    )
    
    confidence_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are an advanced evaluation agent designed to assess the quality of
                plans for solving competitive programming problems. Your task is to evaluate
                the provided plan for solving the given problem and assign a confidence score
                based on its completeness, correctness, logical soundness and efficiency.
                
                Your instructions:
                1. Review the original problem description
                2. Review the provided plan
                3. Assign a confidence score to the plan between 0 and 100, where 100 indicates
                complete confidence in the plan's effectiveness.
                
                This is the original problem:
                {problem_description}
                
                Provided plan:
                {plan}
                
                Respond with just the confidence score. Do not provide any explanation or add
                any other words.
                """
            )
        ]
    )
    
    for problem_number, problem in enumerate(relevant_problems.problems):
        planning_prompt_formatted = planning_prompt.partial(
            description=problem.description,
            planning=problem.planning,
            algorithm=problem.algorithm,
        )
#         print(planning_prompt_formatted)
        planning_chain = planning_prompt_formatted | model
        the_plan = planning_chain.invoke({'original_problem': original_problem})
        
        confidence_prompt_formatted = confidence_prompt.partial(
            plan=the_plan.content,
        )
        confidence_gen_chain = confidence_prompt_formatted | model
        confidence_score = confidence_gen_chain.invoke({'problem_description':original_problem})
        
        generated_plan = Plan(
            plan_description = the_plan.content,
            confidence_score = confidence_score.content
        )
        
        list_of_plans.append(generated_plan)
        
    list_of_plans = sorted(list_of_plans, key=lambda x: x.confidence_score, reverse = True)
    state['plans'] = list_of_plans
    return state

def coding_agent(state: GraphState) -> GraphState:
    cur_plan = state['cur_plan']
    print(f"-----GENERATING CODE FOR PLAN {cur_plan + 1}-----")
    # update_progress(f"-----GENERATING CODE FOR PLAN {cur_plan + 1}-----")
    plans = state['plans']
    current_plan = plans[cur_plan]
    original_problem = state['problem']
    debug_iterations = state['debug_iterations']
    
    routed_from_debugger = False
    
    #check if being re-routed from debugging agent
    if (debug_iterations[cur_plan] > 0):
        routed_from_debugger = True
        modified_plan = state['modified_plan']
    
    
    coding_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                You are an advanced coding agent designed to convert detailed plans
                into executable python code. You have been provided with a problem, and a
                plan to solve that problem. Your task is to write the code to solve
                the original problem based on the plan.
                
                Plan to solve the problem:
                {plan}
                
                Original problem: 
                {original_problem}
                
                Lets think step by step.
                Respond with the code only. Do not add any extra explanation or words
                """
            )
        ]
    )
    
    if (routed_from_debugger):
        # format coding_prompt with new plan
        coding_prompt_formatted = coding_prompt.partial(
            plan = modified_plan
        )
    else:
        # need to implement logic to cycle through different plans if no. of iterations exceeds some limit
        coding_prompt_formatted = coding_prompt.partial(
            plan=current_plan.plan_description,
        )
        
    # print(coding_prompt_formatted)
    coding_chain = coding_prompt_formatted | model
        
    # print(coding_chain)
    code = coding_chain.invoke({'original_problem': original_problem})
    
#     test_input, test_output = extract_sample_io(hard_question)
#     result = test_code(code.content, test_input, test_output)

#     print("generated code")
#     print(code.content)
    
    state['generated_code'] = code.content
#     state['result'] = result
    
    return state

def executor_agent(state:GraphState)->GraphState:
    print("-----TESTING CODE AGAINST SAMPLE IO-----")
    # update_progress("-----TESTING CODE AGAINST SAMPLE IO-----")
    code = state['generated_code']
    original_problem = state['problem']
    
    test_input, test_output = extract_sample_io(original_problem)
#     print("test input")
#     print(test_input)
#     print("test output")
#     print(test_output)
    
    exec_result = test_code(code, test_input, test_output)
    print(f"execution result: {exec_result}")
    
    state['code_exec_result'] = exec_result
    return state

def next_plan(state:GraphState):
    state['cur_plan'] +=1 
#     state['debug_iterations'] = 0
    return state

def human_feedback(state:GraphState):
    # graph has been interrputed right before reaching this node, state['user_feedback'] was just populated by user
    # cur_plan has also been updated with users choice
    state['taken_feedback'] = True
    cur_plan = state['cur_plan']
    state['debug_iterations'][cur_plan] = 0
    print("DEBUG ITERATIONS STATE RN")
    print(state['debug_iterations'])
    return state;

def debugging_agent(state:GraphState)->GraphState:
    print("-----DEBUGGING-----")
    # update_progress("-----DEBUGGING-----")
    code_exec_result = state['code_exec_result']
    generated_code = state['generated_code']
    original_problem = state['problem']
    taken_feedback = state['taken_feedback']
    correct_understanding = state['correct_understanding']
    
    execution_successful = code_exec_result["execution_successful"]
    output_matches = code_exec_result["output_matches"]
    output = code_exec_result["output"]
    expected_output = code_exec_result["expected_output"]
    error_message = code_exec_result["error_message"]
    
    if (execution_successful):
        if(not output_matches):
            # test case didnt pass
            base_prompt = """
                Given a competitive programming problem, you have generated Python code to solve the problem. But the generated
                code did not pass sample test cases. Analyse the code carefully, check whether the logic is correct, whether it
                accounts for all edge cases.

                Your task is to provide a modified planning to solve the original problem. Analyse the problem, understand where
                the current code is incorrect, and generate a plan to solve the original problem. Make sure that you
                - Explain each step in detail
                - Takes into account all edge cases
                - Break down the logic in a clear manner.
                - Do not make any logical errors.

                Return your response in the following format: 
                "Explanation" : <Explanation of why the previous code was wrong>
                "Modified Plan" :<The modified plan> 

                Original Problem: {original_problem}
                Code: {generated_code}
                Expected output: {expected_output}
                Actual output: {output}
            """
            if correct_understanding:
                test_case_analysis = state['test_case_analysis']
                formatted_planning = f"""
                Analysis of the test cases: {test_case_analysis}
        
                Use the provided test case analysis to help guide your planning process
                """
                base_prompt += f"\n{formatted_planning}"
            
            if taken_feedback:
                user_feedback = state['user_feedback']
                formatted_feedback = f"""The user has provided some additional information to guide your debugging process.
                Incorporate it into your planning process.
                User input: {user_feedback}
                """
                base_prompt += f"\n{formatted_feedback}"
            debugging_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        base_prompt
                    )
                ]
            )
            debugging_prompt_formatted = debugging_prompt.partial(
                generated_code=generated_code,
                expected_output=expected_output,
                output=output,
            )
    else:
        # code execution error
        base_prompt = """
        You are an advanced debugging specialist.
        Given a competitive programming, you have generated Python code to solve the problem. But the generated code
        faced an error upon execution. You are provided with the error message. Identify what the error is and 
        generate a new plan to solve the problem that doesn't encounter the same error, or any other errors.
                    
        Make sure that the plan is
                - Explained in detail step-by-step
                - Takes into account all edge cases
                - Break down the logic to solve the problem
                - Do not make any logical errors.

        Return your response in the following format: 
                "Explanation" : <Explanation of why the previous code was wrong>
                "Modified Plan" :<The modified plan> 

        Original Question: {original_problem}
        Code: {generated_code}
        Error message: {error_message}
        """
        if correct_understanding:
            test_case_analysis = state['test_case_analysis']
            formatted_planning = f"""
            Analysis of the test cases: {test_case_analysis}
        
            Use the provided test case analysis to help guide your planning process
            """
            base_prompt += f"\n{formatted_planning}"
        
        if taken_feedback:
            user_feedback = state['user_feedback']
            formatted_feedback = f"""\nThe user has provided some additional information to guide your debugging process.
            Incorporate it into your planning process.
            User input: {user_feedback}
            """
            base_prompt += f"\n{formatted_feedback}"
        debugging_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    base_prompt
                )
            ]
        )
        debugging_prompt_formatted = debugging_prompt.partial(
            generated_code=generated_code,
            error_message=error_message,
        )
    
    debugging_chain = debugging_prompt_formatted | model
    modified_plan = debugging_chain.invoke({'original_problem': original_problem})
    state['modified_plan'] = modified_plan.content
    cur_plan = state['cur_plan']
    state['debug_iterations'][cur_plan] += 1
    return state