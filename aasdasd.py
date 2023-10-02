import os
def replace_lines_inplace(filename, start_line, lines_to_replace):
    with open(filename, 'r+') as file:  # 'r+' mode allows both reading and writing
        # Move to the starting position
        for _ in range(start_line - 1):
            file.readline()

        # Save the current file position
        pos = file.tell()

        # Check that we have enough lines to replace
        for _ in range(len(lines_to_replace)):
            if not file.readline():
                raise ValueError("Not enough lines in the file to replace")

        # Go back to the starting position
        file.seek(pos)

        # Write the new lines (assuming they fit in the space of the old lines)
        for line in lines_to_replace:
            file.write(line + '\n')

# Usage
lines = ["Modified 7", "Modified 8"]
replace_lines_inplace('storage/disk_1/file_1.txt', 7, lines)
print("boom")