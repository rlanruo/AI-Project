# clean transcripts.

import re

def remove_timestamps(input_file, output_file):
    """
    Removes timestamps from the beginning of each line in a text file.

    Args:
        input_file: Path to the input text file.
        output_file: Path to the output text file.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
            for line in infile:
                # Remove timestamp pattern (e.g., 00:02:09) at the beginning of the line
                cleaned_line = re.sub(r"^\d{2}:\d{2}:\d{2}\s*", "", line)
                outfile.write(cleaned_line)
        print(f"Timestamps removed and saved to {output_file}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# Specify the input and output file paths
input_file = r"transcript.txt"
output_file = r"transcript-notime.txt"

# Call the function to remove timestamps
remove_timestamps(input_file, output_file)
