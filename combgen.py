import subprocess

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

        # Inputs
        for inp in inputs:
            f.write(f"    input {inp},\n")

        # Outputs
        for i, outp in enumerate(outputs):
            comma = "," if i < len(outputs)-1 else ""
            f.write(f"    output {outp}{comma}\n")
        f.write(");\n\n")

        # Generate inverted wires
        for inp in inputs:
            f.write(f"wire n{inp};\n")
            f.write(f"not1$(n{inp}, {inp});\n")
        f.write("\n")

        # Initialize lists of product wires for each output
        product_wires_per_output = {out: [] for out in outputs}

        # Build each product term
        for idx, (in_bits, out_bits) in enumerate(prod_terms):
            out_bits = out_bits.strip()
            for o_index, bit in enumerate(out_bits):
                if bit != "1":
                    continue  # Only consider outputs that are 1

                w = f"p{idx}_{o_index}"
                product_wires_per_output[outputs[o_index]].append(w)

                # Build AND inputs
                term_inputs = []
                for bit_in, name in zip(in_bits, inputs):
                    if bit_in == "1":
                        term_inputs.append(name)
                    elif bit_in == "0":
                        term_inputs.append(f"n{name}")
                    elif bit_in == "-":
                        continue

                # Write the AND gate
                if len(term_inputs) == 1:
                    f.write(f"assign {w} = {term_inputs[0]};\n")
                else:
                    f.write(f"and{len(term_inputs)}$({w}, {', '.join(term_inputs)});\n")

        f.write("\n")

        # OR all product terms for each output
        for out in outputs:
            wires = product_wires_per_output[out]
            if len(wires) == 0:
                f.write(f"assign {out} = 1'b0;\n")
            elif len(wires) == 1:
                f.write(f"assign {out} = {wires[0]};\n")
            else:
                f.write(f"or{len(wires)}$({out}, {', '.join(wires)});\n")

        f.write("\nendmodule\n")

def write_module1(filename, inputs, outputs, num_prod_terms, prod_terms):
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
        and_index = 0
        and_num = num_prod_terms
        or_temp_terms = []
        while (and_num):
            cur_term = prod_terms[and_index]
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
            
            and_temp_count = 0
            temp_wires = []

            #build AND tree
            and_temp_terms = temp_terms
            while len(and_temp_terms) > 4:
                inputs_for_gate = and_temp_terms[:3]
                and_temp_terms = and_temp_terms[4:]
                wire_name = f"tmp{and_temp_count}_{and_index}"
                f.write(f"and4$({wire_name}, {', '.join(inputs_for_gate)});\n")
                temp_wires.append(wire_name)
                and_temp_count += 1
            
            #build OR terms
            or_temp_terms.append(f"p{and_index}")

            #Write verilog for each product term into module
            final_inputs = temp_wires + and_temp_terms
            gate_type = f"and{len(final_inputs)}$"
            f.write(f"{gate_type}(p{and_index}, {', '.join(final_inputs)});\n")
            
            and_index = and_index + 1
            and_num = and_num - 1

        #Build OR tree
        or_index = 0
        or_temp_count = 0
        while len(or_temp_terms) > 1:
            temp_wires = []
            while len(or_temp_terms) >= 4:
                inputs_for_gate = or_temp_terms[:4]
                or_temp_terms = or_temp_terms[4:]
                wire_name = f"tmp{or_temp_count}_{or_index}"
                f.write(f"or4$({wire_name}, {', '.join(inputs_for_gate)});\n")
                temp_wires.append(wire_name)
                or_temp_count += 1
            
            if len(or_temp_terms) > 1:
                wire_name = f"tmp{or_temp_count}_{or_index}"
                gate_type = f"or{len(or_temp_terms)}$"
                f.write(f"{gate_type}({wire_name}, {', '.join(or_temp_terms)});\n")
                temp_wires.append(wire_name)
                or_temp_count += 1
            else:
                temp_wires.extend(or_temp_terms)

            or_temp_terms = temp_wires
        
        f.write(f"assign {outputs[or_index]} = {or_temp_terms[0]};\n")
        or_index = or_index + 1

        print("blah")
        f.write("endmodule\n")

#Main
def main():
    file_num = 1 #  CHANGE BEFORE RUNNING
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

