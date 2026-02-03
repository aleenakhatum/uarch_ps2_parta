import subprocess
import math

#Runs espresso tool on the original truth table input to generate a minimized boolean expression
def run_espresso(input_file, output_file, output_filter=None):
    """Run espresso on a PLA input file and save output."""
    
    #Build command
    cmd = ["./espresso.linux"]
    if (output_filter):
        cmd.extend(["-o", output_filter])
    cmd.append(input_file)

    #Run espresso
    result = subprocess.check_output(cmd, text=True)
    
    #Print result
    with open(output_file, "w") as f:
        f.write(result)
    return result


#General Helpers
def count_literals(in_bits):
    """Take an input of a line of bits and pass back the number of
    literals (skip any don't care values)"""
    count = 0
    for bit in in_bits:
        if bit == '0' or bit == '1':
            count += 1
    return count

def detect_input_type(filename):
    """Return 'fsm' if .st line exists, otherwise 'comb'."""
    with open(filename, "r") as f:
        for line in f:
            if line.strip().startswith(".st"):
                return "fsm"
    return "comb"

def write_truth_table_file(filename, state_dict, inputs, outputs):
    """
    Writes a truth table file from a dictionary of states.

    Args:
        filename (str): output file path
        state_dict (dict): {'S0': (input_val, output_val), ...}
    """

    # Extract all input and output values
    if isinstance(state_dict, dict):        
        input_vals = [tup[0] for tup in state_dict.values()]
        output_vals = [tup[1] for tup in state_dict.values()]
    else:
        input_vals = [tup[0] for tup in state_dict]
        output_vals = [tup[1] for tup in state_dict]

    # Calculate number of input/output bits
    #num_inputs = max(input_vals).bit_length() or 1
    num_inputs = math.ceil(math.log2(len(output_vals))) if len(output_vals) > 1 else 1
    num_outputs = len(outputs)

    # Input/output labels
    output_labels = outputs

    # Sort table by input value
    if isinstance(state_dict, dict):
        table = sorted(list(state_dict.values()))
    else:
        table = sorted(list(state_dict))


    # Open file to write
    with open(filename, "w") as f:
        f.write(f".i {num_inputs}\n")
        f.write(f".o {num_outputs}\n")
        f.write(".ilb " + " ".join(inputs) + "\n")
        f.write(".ob " + " ".join(output_labels) + "\n\n")

        for inp_val, out_val in table:
            # Format input bits
            if isinstance(state_dict, dict):
                inp_bits = format(inp_val, f"0{num_inputs}b")
            else:
                inp_bits = inp_val
            # Format output bits
            out_bits = out_val
            f.write(f"{inp_bits} {out_bits}\n")


#Comb Functions
def parse_comb_file(espresso_output_file):
    """Take an input of an espresso output file and identify characteristics 
    about the passed in boolean equation such as the inputs, outputs, number
    of product terms, and the product terms themselves"""

    inputs = []
    outputs = []
    num_prod_terms = 0
    prod_terms = []

    # Open the file and read lines
    with open(espresso_output_file, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        if line.startswith("#"):
            continue

        if line.startswith(".ilb"):
            tokens = line.split()
            inputs = tokens[1:]   # skip ".ilb"

        elif line.startswith(".ob"):
            tokens = line.split()
            outputs = tokens[1:]  # skip ".ob"
        
        elif line.startswith(".p"):
            tokens = line.split()
            num_prod_terms = int(tokens[1])
        
        # Skip empty lines and headers
        if not line or line.startswith("."):
            continue

        # Split product line
        in_bits, out_bits = line.split()
        prod_terms.append((in_bits, out_bits))

    return inputs, outputs, num_prod_terms, prod_terms

def write_comb_header(f, inputs, outputs, module_name):
    f.write(f"module {module_name}(\n")
    for inp in inputs:
        f.write(f"    input {inp},\n")
    for i, outp in enumerate(outputs):
        comma = "," if i < len(outputs)-1 else ""
        f.write(f"    output {outp}{comma}\n")
    f.write(");\n\n")
    # Declare inverted wires
    for inp in inputs:
        f.write(f"wire n{inp};\n")
    f.write("\n")

def write_comb_module(f, inputs, outputs, prod_terms, fsm, idxstr = "", gate_start=0):
    """ Uses only lib1 gates """
    gate_count = gate_start

    # NOT gates
    for i, inp in enumerate(inputs):
        f.write(f"inv1$ {idxstr}u{i} (n{inp}, {inp});\n")
        gate_count += 1
    f.write("\n")

    # Product wires
    product_wires_per_output = {out: [] for out in outputs}

    # AND terms
    for idx, (in_bits, out_bits) in enumerate(prod_terms):
        out_bits = out_bits.strip()
        for o_index, bit in enumerate(out_bits):
            if bit != "1":
                continue
            w = f"{idxstr}p{idx}_{o_index}" 
            product_wires_per_output[outputs[o_index]].append(w)

            term_inputs = []
            for b, name in zip(in_bits, inputs):
                if b == "1":
                    term_inputs.append(name)
                elif b == "0":
                    term_inputs.append(f"n{name}")
                elif b == "-":
                    continue


            n_inputs = len(term_inputs)
            if n_inputs == 1:
                f.write(f"assign {w} = {term_inputs[0]};\n")
            elif n_inputs == 2:
                f.write(f"and2$ {idxstr}u{gate_count} ({w}, {term_inputs[0]}, {term_inputs[1]});\n")
                gate_count += 1
            elif n_inputs == 3:
                f.write(f"and3$ {idxstr}u{gate_count} ({w}, {term_inputs[0]}, {term_inputs[1]}, {term_inputs[2]});\n")
                gate_count += 1
            elif n_inputs == 4:
                f.write(f"and4$ {idxstr}u{gate_count} ({w}, {term_inputs[0]}, {term_inputs[1]}, {term_inputs[2]}, {term_inputs[3]});\n")
                gate_count += 1
            else:
                # tree
                intermediate = term_inputs
                while len(intermediate) > 4:
                    w_tmp = f"tmp{gate_count}"
                    f.write(f"and4$ {idxstr}u{gate_count} ({w_tmp}, {', '.join(intermediate[:4])});\n")
                    gate_count += 1
                    intermediate = [w_tmp] + intermediate[4:]
                # last AND
                if len(intermediate) == 2:
                    f.write(f"and2$ {idxstr}u{gate_count} ({w}, {intermediate[0]}, {intermediate[1]});\n")
                    gate_count += 1
                elif len(intermediate) == 3:
                    f.write(f"and3$ {idxstr}u{gate_count} ({w}, {intermediate[0]}, {intermediate[1]}, {intermediate[2]});\n")
                    gate_count += 1
                elif len(intermediate) == 4:
                    f.write(f"and4$ {idxstr}u{gate_count} ({w}, {intermediate[0]}, {intermediate[1]}, {intermediate[2]}, {intermediate[3]});\n")
                    gate_count += 1

    f.write("\n")

    # OR terms
    for out in outputs:
        wires = product_wires_per_output[out]
        if len(wires) == 0:
            f.write(f"assign {out} = 1'b0;\n")
        elif len(wires) == 1:
            f.write(f"assign {out} = {wires[0]};\n")
        else:
            n_terms = len(wires)
            if n_terms <= 4:
                f.write(f"or{n_terms}$ {idxstr}u{gate_count} ({out}, {', '.join(wires)});\n")
                gate_count += 1
            else:
                # tree
                intermediate = wires
                while len(intermediate) > 4:
                    w_tmp = f"tmp{gate_count}"
                    f.write(f"or4$ {idxstr}u{gate_count} ({w_tmp}, {', '.join(intermediate[:4])});\n")
                    gate_count += 1
                    intermediate = [w_tmp] + intermediate[4:]
                # last OR
                if len(intermediate) == 2:
                    f.write(f"or2$ {idxstr}u{gate_count} ({out}, {intermediate[0]}, {intermediate[1]});\n")
                    gate_count += 1
                elif len(intermediate) == 3:
                    f.write(f"or3$ {idxstr}u{gate_count} ({out}, {intermediate[0]}, {intermediate[1]}, {intermediate[2]});\n")
                    gate_count += 1
                elif len(intermediate) == 4:
                    f.write(f"or4$ {idxstr}u{gate_count} ({out}, {intermediate[0]}, {intermediate[1]}, {intermediate[2]}, {intermediate[3]});\n")
                    gate_count += 1

        if (not fsm):
            f.write("endmodule\n")
    return gate_count


#FSM Functions
def parse_fsm_file(filename):
    inputs = []
    outputs = []
    states = []
    state_outputs = {}
    transitions = []

    # Counter for assigning state numbers
    state_counter = 0
    state_number_map = {}  # maps state name -> state number

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith(".ilb"):
                inputs = line.split()[1:]
            elif line.startswith(".ob"):
                outputs = line.split()[1:]
            elif line.startswith(".st"):
                states = line.split()[1:]
            elif line.startswith(".so"):
                parts = line.split()  # [".so", "S0", "0"]
                state_name = parts[1]
                output_val = parts[2]

                # Assign a unique number to the state if not already assigned
                if state_name not in state_number_map:
                    state_number_map[state_name] = state_counter
                    state_counter += 1

                state_outputs[state_name] = (state_number_map[state_name], output_val)
            elif line.startswith(".t"):
                # transition line: cur_state input_bits next_state
                parts = line.split()  
                if len(parts) == 4:
                    _, cur_state, input_bits, next_state = parts
                    transitions.append((cur_state, input_bits, next_state))


    return inputs, outputs, states, state_outputs, transitions

def write_fsm_header(f, module_name, inputs, outputs, state_bits):
    """
    Writes the module header, input/output ports, state wires, and input inverters.
    Opens the file itself.
    filename: file to write to
    module_name: string for module name
    inputs: list of input names
    outputs: list of output names
    state_bits: number of state flip-flops
    """
    f.write(f"module {module_name}(\n")
    f.write("    input clk,\n    input rst,\n    input set,\n")
    for inp in inputs:
        f.write(f"    input {inp},\n")
    for i, outp in enumerate(outputs):
        comma = "," if i < len(outputs)-1 else ""
        f.write(f"    output {outp}{comma}\n")
    f.write(");\n\n")

def write_fsm_module(fname, inputs, outputs, states, state_outputs, transitions):
    """
    Generate FSM module (after header has been written).
    Uses write_comb_module() for combinational logic.
    """

    idxstr_i = 0

    #Prepare State Ouput Logic
    state_wires = []
    state_bits = max(1, math.ceil(math.log2(len(states))))
    for i in range(state_bits):
        state_wires.append(f"state{i}")
    state_wires.reverse()  

    filename = fname + "_TT"
    write_truth_table_file(filename, state_outputs, state_wires, outputs)
    print("TT", outputs)
    with open(filename, "r") as f: #print contents of file
        contents = f.read()
        print(contents)
    output_file = fname + "_espresso_out_TT"
    run_espresso(filename, output_file)
    with open(output_file, "r") as f: #print contents of file
        contents = f.read()
        print(contents)

    #Prepare Transition Output Logic
    state_encoding = {s: format(i, f"0{state_bits}b") for i, s in enumerate(states)}
    comb_inputs = [f"state{i}" for i in range(state_bits)] 
    comb_inputs.reverse()
    comb_inputs += inputs
    next_state_outputs = [f"ns{i}" for i in range(state_bits)]
    next_state_outputs.reverse()

    prod_terms = []
    for cur_state, input_bits, next_state in transitions:
        cur_state_enc = state_encoding[cur_state]
        full_input_bits = cur_state_enc + input_bits
        ns_bits = state_encoding[next_state]
        out_bits = ns_bits
        prod_terms.append((full_input_bits, out_bits))

    filename2 = fname + "_transitions"
    write_truth_table_file(filename2, prod_terms, comb_inputs, next_state_outputs)
    with open(filename2, "r") as f: #print contents of file
        contents = f.read()
        print(contents)
    output_file2 = fname + "_espresso_out_transitions"
    run_espresso(filename2, output_file2)
    with open(output_file2, "r") as f: #print contents of file
        contents = f.read()
        print(contents)
    
    #Write combinational logic transitions
    with open(fname, "a") as f:
        # State Wires
        for i in range(state_bits):
            f.write(f"wire state{i};\n")
            f.write(f"wire nstate{i};\n")
        f.write("\n")
        
        # Declare intermediate wires for combinational logic
        intermediate_wires = set()
        for inp in inputs: #inverted
            intermediate_wires.add(f"n{inp}")
        for i in range(len(prod_terms)): #prod
            intermediate_wires.add(f"call{idxstr_i}p{i}_0")
        for i in range(state_bits): #ns
            intermediate_wires.add(f"ns{i}")
        for w in sorted(intermediate_wires):
            f.write(f"wire {w};\n")
        f.write("\n")

        # Write combinational logic
        idxstr = "call" + str(idxstr_i)
        inputs, outputs, num_prod_terms, prod_terms = parse_comb_file(output_file2)
        print("REHEHEEHEH", inputs, outputs, num_prod_terms, prod_terms)
        gate_count = write_comb_module(f, inputs, outputs, prod_terms, True, idxstr = idxstr)
        idxstr_i += 1

    #Write combinational Logic OUTPUTS
    inputs, outputs, num_prod_terms, prod_terms = parse_comb_file(output_file)
    with open(fname, "a") as f: 
        #Make intermediate wires
        intermediate_wires = set()
        for i in range(len(prod_terms)): #prod
            intermediate_wires.add(f"call{idxstr_i}p{i}_0")
        for w in sorted(intermediate_wires):
            f.write(f"wire {w};\n")
        f.write("\n")

        idxstr = "call" + str(idxstr_i)
        write_comb_module(f, inputs, outputs, prod_terms, True, idxstr = idxstr)
        idxstr_i += 1

        # Flip-flops for state
        for i in range(state_bits):
            f.write(f"dff$ u_dff{i} (clk, ns{i}, state{i}, nstate{i}, rst, set);\n")
        
        f.write("endmodule\n")   

#Main
def main():
    file_num = 5 #CHANGE BEFORE RUNNING
    module_name = "state3" #CHANGE BEFORE RUNNING 
    input_file = f"input{file_num}.pla"
    espresso_output_file = f"minimized{file_num}.pla"
    output_file = f"module{file_num}.pla"

    # Convert line endings to Unix format
    subprocess.run(["dos2unix", input_file], check=True)

    # Determine type of input
    input_type = detect_input_type(input_file)
    print(f"Detected input type: {input_type}")

    #Retrieve minimized boolean expression
    if input_type == "fsm":
        print("State Machine Input File DETECTED")
        inputs, outputs, states, state_outputs, transitions = parse_fsm_file(input_file)
        with open(output_file, "w") as f: # open in append mode
            write_fsm_header(f, module_name, inputs, outputs, len(states))
        write_fsm_module(output_file, inputs, outputs, states, state_outputs, transitions)
        print(f"State Machine Module Complete in: {output_file}")

    elif input_type == "comb":
        print("Truth Table Input File DETECTED")
        print("Running espresso...")
        minimized = run_espresso(input_file, espresso_output_file)
        print("Espresso output:")
        print(minimized)

        #Create module file
        inputs, outputs, num_prod_terms, prod_terms = parse_comb_file(espresso_output_file)
        with open(output_file, "w") as f: 
            write_comb_header(f, inputs, outputs, module_name)
            write_comb_module(f, inputs, outputs, prod_terms, False)
        print(f"Combinational Logic Module Complete in: {output_file}")

if __name__ == "__main__":
    main()

