import re
import sys
from io import StringIO
import traceback
from models import Exemplar, GraphState

def extract_sample_io(problem: str):
    input_match = re.search(r"-----Example-----\s*Input:\s+(.*?)\s*Output:\s", problem, re.DOTALL)
    sample_input = input_match.group(1).strip() if input_match else ""
    
    output_match = re.search(r"Output:\s+(.*?)\s*-----Note-----", problem, re.DOTALL)
    sample_output = output_match.group(1).strip() if output_match else ""
    return sample_input, sample_output

def mask_output(text):
    pattern = re.compile(r'output is [^.\n]*')
    masked_text = pattern.sub('output is <?>', text)
    return masked_text

def extract_expected_output(text):
    # Define the regex pattern to match the specific expected output
    pattern = re.compile(r'Therefore, the expected output is ([^.\n]*)')
    # Find all matches in the input text
    matches = pattern.findall(text)
    return matches

def extract_outputs(text):
    outputs = re.findall(r"the expected output is ([^.\n]*)", text)
    outputs = [output.strip() for output in outputs]
    return outputs

def extract_problem_without_testcase(text):
    pattern = re.compile(r'^(.*?)Example', re.DOTALL)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    else:
        return text

def normalize_string(s):
    # Strip leading/trailing whitespace and collapse multiple spaces
    return re.sub(r'\s+', ' ', s.strip())

def test_code(code: str, sample_input, sample_output, fn_name:str=None):
    if isinstance(sample_input, str):
        print("test input is string")
        def mock_input():
            for line in sample_input.strip().split("\n"):
                yield line
        print("defined mock input")
        input_gen = mock_input()
        def input():
            return next(input_gen)
    
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        sys.stdin = StringIO(sample_input.strip())
        sys.stdout = StringIO()
        
#         print("redirected stdin")

        namespace = {
            "input": input,
            "print": print,
            "map": map,
            "int": int,
            "range": range,
            # Any other necessary built-ins can be added here
        }
        execution_successful = False
        output_matches = False
        error_message = ""
        output = ""
        
        try:
            exec(code, namespace)
#             print("executed code")
            output = sys.stdout.getvalue().strip()
            execution_successful = True
        except SystemExit:
            error_message = "SystemExit called in the code"
            output = f"Generated code has an error:{error_message}"
        except Exception as e:
            error_message = traceback.format_exc()
            output = f"Generated code has an error:{error_message}"
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout
        if execution_successful:
            # Normalize both output and expected output
            normalized_output = normalize_string(output)
            normalized_expected_output = normalize_string(sample_output)
            output_matches = normalized_output == normalized_expected_output
#             sample_output = sample_output.strip()
#             output_matches = output == sample_output[0]
#     else:
#         namespace = {
#             "print": print,
#             "map": map,
#             "int": int,
#             "range": range,
#         }
        
#         execution_successful = False
#         output_matches = False
#         error_message = ""
#         try:
#             exec(code, namespace)
#             if fn_name is None:
#                 fn_name = extract_function_name(code)
#                 if fn_name is None:
#                     raise ValueError("No function definition in the code")
#             output = namespace[fn_name](*sample_input)
#             execution_successful = True
#         except SystemExit as e:
#             error_message = "SystemExit called in the code"
#             output = f"Generated code has an error:{error_message}"
#         except Exception as e:
#             error_message = traceback.format_exc()
#             output = f"Generated code has an error:{error_message}"
# #         error_message = str(e)

#         if execution_successful:
#             if isinstance(sample_output[0], list):
#                 sample_output = sample_output[0]
#             if isinstance(output, list) and isinstance(sample_output, list):
#                 output_matches = output == sample_output
#             else:
#                 output_matches = False
            
    result ={
        "execution_successful":execution_successful,
        "output_matches":output_matches,
        "output":output,
        "expected_output":sample_output,
        "error_message":error_message
    }
    return result

def router_function(state:GraphState):
    # extract code execution results
    code_exec_result = state['code_exec_result']
    execution_successful = code_exec_result["execution_successful"]
    output_matches = code_exec_result["output_matches"]
    cur_plan = state['cur_plan']
    
    if execution_successful and output_matches:
        # generated code is successful, return to user
        print("-----DESICION FINISH-----")
        return "end"
    else:
        if state['debug_iterations'][cur_plan] >= 3:
            if state['taken_feedback']:
                print ("-----END: HUMAN FEEDBACK LOOP HAS ENDED-----")
                return "end"
            else:
                if cur_plan >= 2:
                    print("-----DESICION : Could not find working solution-----")
                    return "human_feedback"
                # select plan with next highest confidence and try again
                print("-----DESICION : TRY NEXT PLAN-----")
                return "next_plan"
        else:
            # go to debugging agent to try fixing code
            print("-----DESICION : TRY FIXING CODE-----")
            return "debug"

def check_inferred_output(state:GraphState):
    print("-----CHECKING CORRECTNESS OF INFERRED OUTPUT-----")
    correct_understanding = state['correct_understanding']
    if correct_understanding:
        print("-----DESICION: ACCURATE TEST CASE ANALYSIS FOUND-----")
        return "proceed"
    else:
        test_case_analysis_iterations = state['test_case_analysis_iterations']
        if test_case_analysis_iterations < 3:
            print("-----DESICION: MISUNDERSTANDING IN TEST CASE ANALYSIS-----")
            return "misunderstanding_present"
        else:
            print("-----DESICION: COULD NOT GENERATE ACCURATE TEST CASE ANALYSIS-----")
            return "proceed"
        
def create_initial_state(problem:str)->GraphState:
    return GraphState(
        problem=problem,
        test_case_analysis="",
        inferred_output="",
        test_case_analysis_iterations=0,
        relevant_problems=Exemplar(problems=[]), 
        plans=[],
        cur_plan=0,
        generated_code="",
        code_exec_result={},
        modified_plan="",
        debug_iterations=[0,0,0],
        taken_feedback=False,
        user_feedback="",
    )