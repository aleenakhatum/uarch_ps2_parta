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



#Main
def main():
    file_num = 1
    input_file = f"input{file_num}.pla"
    output_file = f"minimized{file_num}.pla"

    # Convert line endings to Unix format
    subprocess.run(["dos2unix", input_file], check=True)

    #Retrieve minimized boolean expression
    print("Running espresso...")
    minimized = run_espresso(input_file, output_file, True)

    print("Espresso output:")
    print(minimized)

if __name__ == "__main__":
    main()

