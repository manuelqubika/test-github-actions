import re
import sys

# Function to add space after the keywords and remove parentheses after return statement
def format_code(filename):
    # Open the file in read and write mode
    with open(filename, 'r+') as file:
        # Read the contents of the file
        data = file.read()

        # Add space after keywords and remove parentheses
        data_new = re.sub(r'\b(if|switch|while|for|do)\(', r'\1 (', data)

        # Remove parentheses after return statement and add space
        data_new = re.sub(r'\breturn\(', r'return (', data_new)

        # Move the file pointer to the beginning of the file
        file.seek(0)

        # Write the modified data back to the file
        file.write(data_new)

        # Check if the data was replaced
        if data_new != data:
            print(" >> Code format is successful!")

        # Truncate the file to remove any remaining content
        file.truncate()

if __name__ == "__main__":
    format_code(sys.argv[1])