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

    for line in espresso_output_file.splitlines():
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
            

            input_num = 0
            while (count != 0):
                if (count % 4 == 0): #4 input gate
                    f.write(f"and4$(p{index}, {in_terms[0]}, {in_terms[1]}, {in_terms[2]}, {in_terms[3]});")
                    in_terms = in_terms[4:]
                elif (count % 4 != 0):
                    if (count % 3 == 0): #3 input gate
                        f.write(f"and3$(p{index}, {in_terms[0]}, {in_terms[1]}, {in_terms[2]});")
                        in_terms = in_terms[3:]
                    elif (count % 3 != 0):
                        if (count % 2 == 0): #2 input gate
                            f.write(f"and2$(p{index}, {in_terms[0]}, {in_terms[1]});")
                            in_terms = in_terms[2:]
                        elif (count % 2 != 0): #assign gate directly
                            f.write(f"assign p{index} = {in_terms[0]});")
                            in_terms = in_terms[1:]

                count = count - input_num
                temp_terms[index] = f"p{index}"
                temp_count = temp_count + 1

            while (temp_count != 0):



                

        
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
    minimized = run_espresso(input_file, espresso_output_file, True)
    print("Espresso output:")
    print(minimized)

    #Create module file
    inputs, outputs, num_prod_terms, prod_terms = parse_inputs_outputs(espresso_output_file)
    write_module(output_file, inputs, outputs, num_prod_terms, prod_terms)

if __name__ == "__main__":
    main()

