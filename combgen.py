import subprocess

#Runs espresso tool on the original truth table input to generate a minimized boolean expression
def run_espresso(input_file, output_file, output_filter=None):
    """Run espresso on a PLA input file and save output."""
    
    #Build command
    cmd = ["espresso.linux"]
    if (output_filter):
        cmd.extend(["-o", output_filter])
    cmd.append(input_file)

    #Run espresso
    result = subprocess.check_output(cmd, text=True)
    
    #Print result
    with open(output_file, "w") as f:
        f.write(result)
    return result

def parse_inputs_outputs(espresso_output_file):
    inputs = []
    outputs = []
    num_prod_terms = 0
    prod_terms = []

    # Open the file and read lines
    with open(espresso_output_file, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

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

def count_literals(in_bits):
    count = 0
    for bit in in_bits:
        if bit == '0' or bit == '1':
            count += 1
    return count


def write_module(filename, inputs, outputs, num_prod_terms, prod_terms):
    with open(filename, "w") as f:
        f.write("module temp(\n")

        #write inputs
        for input in inputs:
            f.write(f"    input {input},\n")
        
        #write outputs
        for output in outputs:
            f.write(f"    output {output},\n")

        f.write(");\n\n")

        #write structural verilog
        index = 0
        while (num_prod_terms):
            cur_term = prod_terms[index]
            in_bits = cur_term[0]

            in_terms = inputs
            count = count_literals(in_bits)

            #Map bits to actual signal name for product term
            temp_terms = []
            for bit, name in zip(in_bits, inputs):
                if bit == '0':
                    temp_terms.append(f"n{name}")
                elif bit == '1':
                    temp_terms.append(name)
            
            #build AND tree
            temp_count = 0
            temp_wires = []
            while len(temp_terms) > 4:
                inputs_for_gate = temp_terms[:3]
                temp_terms = temp_terms[4:]
                wire_name = f"tmp{temp_count}_{index}"
                f.write(f"and4$({wire_name}, {', '.join(inputs_for_gate)});\n")
                temp_wires.append(wire_name)
                temp_count += 1

            final_inputs = temp_wires + temp_terms
            gate_type = f"and{len(final_inputs)}$"
            f.write(f"{gate_type}(p{index}, {', '.join(final_inputs)});\n")
        
            index = index + 1
            num_prod_terms = num_prod_terms - 1
        f.write("endmodule\n")

#Main
def main():
    file_num = 1
    input_file = f"input{file_num}.pla"
    espresso_output_file = f"minimized{file_num}.pla"
    output_file = f"module{file_num}.pla"

    # Convert line endings to Unix format
    subprocess.run(["dos2unix", input_file], check=True)

    #Retrieve minimized boolean expression
    print("Running espresso...")
    minimized = run_espresso(input_file, espresso_output_file)
    print("Espresso output:")
    print(minimized)

    #Create module file
    inputs, outputs, num_prod_terms, prod_terms = parse_inputs_outputs(espresso_output_file)
    write_module(output_file, inputs, outputs, num_prod_terms, prod_terms)

if __name__ == "__main__":
    main()

