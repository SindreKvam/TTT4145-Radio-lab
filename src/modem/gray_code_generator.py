import numpy as np
import csv
import os

#os.chdir(r"C:\NTNU\Vaar2026\radioCom\Project\TTT4145-Radio-lab\src\tx\gray_codes")
#print("Working directory:", os.getcwd())

def generate_graycode_grid(size = 16):
    horisontal = np.zeros(int(np.sqrt(size)),dtype=int)

    for i in range(1, np.size(horisontal)):
        horisontal[i] = i ^ (i>>1)

    vertical = np.copy(horisontal)
    vertical = np.left_shift(vertical,int(np.log2(size)/2))

    greycode_grid = horisontal[:,None] + vertical[None,:]

    print(greycode_grid)

    return greycode_grid

def store_grid_in_csv(grid):
    with open('graycodes.csv', 'w', newline='') as csvfile:
        fieldnames = ['graycode', 'column', 'row']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        rows, collumns = np.shape(grid)

        for column_index in range(rows):
            for row_index in range(collumns):
                writer.writerow({
                    'graycode': int(grid[column_index][row_index]),
                    'column': column_index, #x axis
                    'row': row_index        #y axis
                })


greycode_grid = generate_graycode_grid(16)#change parameter(M) in here to change M-QAM 
store_grid_in_csv(greycode_grid)

