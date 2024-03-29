import sqlparse
import re
from num2words import num2words

def draw_latex_arrows(from_cols, to_cols, direction, offset):
    if direction == 'north':
        latex_template = "\\draw[-latex, very thick, black!70!black] (dedi.{} north) -- ++(0,{}) -| (dedi.{} north);\n".format(num2words(from_cols), offset, num2words(to_cols))
    else: # south
        latex_template = "\\draw[-latex, very thick, black!70!black] (dedi.{} south) -- ++(0,-{}) -| (dedi.{} south);\n".format(num2words(from_cols), offset, num2words(to_cols))
    return latex_template


def generate_latex_for_table(table, name):
    cols = table["columns"]
    num_cols = len(cols)
    
    # Making LaTeX for nodes
    latex_nodes = "{"
    for i, col in enumerate(cols):
        latex_nodes += "\\nodepart{{{}}}  ".format(num2words(i+1))
        if any(col in pk for pk in table['primary keys']):
            latex_nodes += "\\underline{{{}}}\n".format(col)
        else:
            latex_nodes += "{{{}}}\n".format(col)
    latex_nodes += "};\n"

    # Get primary key indices
    primary_key_indices = [i+1 for i, col in enumerate(cols) if any(col in pk for pk in table['primary keys'])]

    # Making LaTeX for arrows
    latex_arrows = ""
    for i, col in enumerate(cols):
        # Draw arrows from primary keys to other non-primary key columns
        if any(col in pk for pk in table['primary keys']):
            for j in range(i+1, num_cols):
                if not any(cols[j] in pk for pk in table['primary keys']):  # don't draw arrow to other primary keys
                    latex_arrows += draw_latex_arrows(i+1, j+1, 'south', 0.5)
        # Draw arrows from unique keys to primary keys
        elif col in table['unique keys']:
            for pk_index in primary_key_indices:
                height = table['unique keys'].index(col)+1
                height = height + height
                print(height)
                latex_arrows += draw_latex_arrows(i+1, pk_index, 'north', 0.5+0.1*height)
        
    # Handling combination unique keys
    for unique_key in table['unique keys']:
        if isinstance(unique_key, list):  # If this unique key is a combination of columns
            for i in range(len(unique_key)):
                # determine height by the amount of unique keys in the table
                height = table['unique keys'].index(unique_key)+1
                height = height + height
                for pk_index in primary_key_indices:
                    latex_arrows += draw_latex_arrows(cols.index(unique_key[i])+1, pk_index, 'north', 0.5+0.1*height)

    # Combining everything
    latex_front = "\n\\textbf{" + name + "}\n\\par" + """\n\\begin{tikzpicture}[my shape/.style={
    rectangle split, rectangle split parts=#1, draw, anchor=center}]
    \\node (start) {};"""
    
    latex_col_count = """\\node [my shape={}, rectangle split horizontal,name=dedi]""".format(num_cols)
    
    latex_back = """\\end{tikzpicture}\n"""
    
    latex = latex_front + "\n" + latex_col_count + "\n" + latex_nodes + "\n" + latex_arrows + "\n" + latex_back
    return latex



def generate_latex_from_dict(tables):
    max_cols = max(len(table['columns']) for table in tables.values())
    num_tables = len(tables)

    width = max_cols * 3  # adjust scaling factor as needed
    height = num_tables * 3.5  # adjust scaling factor as needed

    latex_header = """\\documentclass[parskip]{scrartcl}
    \\usepackage[margin=1mm,landscape,paperwidth={""" + str(height) + """cm},paperheight={""" + str(width) + """cm}]{geometry}
    \\usepackage{tikz}
    \\usetikzlibrary{shapes.multipart, calc}

    \\begin{document}"""

    __latex = latex_header

    for name, table in tables.items():
        __latex += generate_latex_for_table(table, name)
        __latex += "\\par" + "\\par"
    
    __latex += """\\end{document}"""
    print(__latex)

    with open("output.txt", "w") as f:
        f.write(__latex)

def parse_sql(sql_scripts):
    parsed = sqlparse.parse(sql_scripts)
    tables = {}
    for statement in parsed:
        if statement.get_type() == 'CREATE':
            table_name = None
            column_names = []
            primary_keys = []
            unique_keys = []

            for token in statement.tokens:
                # Getting table name
                if token.ttype is None and isinstance(token, sqlparse.sql.Identifier):
                    table_name = token.get_real_name()

                # Getting column names, primary keys, unique keys
                elif token.ttype is None and isinstance(token, sqlparse.sql.Parenthesis):
                    columns = token.value.replace('(', '').replace(')', '').replace(',', '').split('\n')
                    while '' in columns:
                        columns.remove('')
                    for col in columns:
                        col_parts = col.strip().split()
                        column_name = col_parts[0]

                        # Exclude UNIQUE keyword from columns list
                        if column_name.upper() != 'UNIQUE' and column_name.upper() != 'PRIMARY':
                            column_names.append(column_name)

                        if 'PRIMARY' in col_parts:
                            if column_name.upper() != 'PRIMARY':
                                primary_keys.append(column_name)
                            else:
                                combination = []
                                if len(col_parts) > 3:
                                    for i in range(2, len(col_parts)):
                                        combination.append(col_parts[i])
                                    primary_keys.append(combination)
                                else:
                                    primary_keys.append(col_parts[1])
                        if 'UNIQUE' in col_parts:
                            if column_name.upper() != 'UNIQUE':
                                unique_keys.append(column_name)
                            else:
                                combination = []
                                if len(col_parts) > 2:
                                    for i in range(1, len(col_parts)):
                                        combination.append(col_parts[i])
                                    unique_keys.append(combination)
                                else:
                                    unique_keys.append(col_parts[1])


            # Storing table information in dictionary
            if table_name:
                tables[table_name] = {
                    "columns": column_names,
                    "primary keys": primary_keys,
                    "unique keys": unique_keys
                }
    return tables

# read sql file
with open("sql.txt", "r") as f:
    sql_scripts = f.read()

tables = parse_sql(sql_scripts)
generate_latex_from_dict(tables)


# ask if user wants to generate additional latex code for arrows
if input("Do you want to generate additional latex code for arrows? (y/n) ") == "y":
    while True:
        # ask for which table
        table_name = input("Enter table name: ")
        if table_name in tables:
            # From column
            from_col = input("Enter column name to draw arrow from: ")
            while from_col not in tables[table_name]['columns']:
                from_col = input("Column not found. Enter column name to draw arrow from: ")
            # To columns, handle multiple columns
            to_col = input("Enter column name to draw arrow to: ")
            while to_col not in tables[table_name]['columns']:
                to_col = input("Column not found. Enter column name to draw arrow to: ")
            # # Direction
            # direction = input("Enter direction (north/south): ")
            # while direction != "north" and direction != "south":
            #     direction = input("Invalid direction. Enter direction (north/south): ")
            # # Offset
            # offset = input("Enter offset: ")
            # while not re.match(r"^\d+(\.\d+)?$", offset):
            #     offset = input("Invalid offset. Enter offset: ")
            
            # Find table in output.txt
            with open("output.txt", "r") as f:
                latex = f.read()
            table_index = latex.find(table_name)
            if table_index == -1:
                print("Table not found in output.txt")
                continue
            # Find the next \end{tikzpicture} after the table
            end_index = latex.find("\\end{tikzpicture}", table_index)
            if end_index == -1:
                print("Table not found in output.txt")
                continue
            # Find the index of the line before \end{tikzpicture}
            line_index = latex.rfind("\n", table_index, end_index)
            if line_index == -1:
                print("Table not found in output.txt")
                continue
            # Insert latex code for arrow
            # check if primary key
            if any(from_col in pk for pk in tables[table_name]['primary keys']):
                latex = latex[:line_index] + draw_latex_arrows(tables[table_name]['columns'].index(from_col)+1, tables[table_name]['columns'].index(to_col)+1, 'south', 0.5) + latex[line_index:]
            else:
                latex = latex[:line_index] + draw_latex_arrows(tables[table_name]['columns'].index(from_col)+1, tables[table_name]['columns'].index(to_col)+1, 'north', 0.5+0.1*(tables[table_name]['columns'].index(from_col)+1)) + latex[line_index:]
            # Write to output.txt
            # Ask if user wants to save to output.txt
            if input("Do you want to save to output.txt? (y/n) ") == "y":
                with open("output.txt", "w") as f:
                    f.write(latex)
        else:
            print("Table not found in sql.txt")
            continue
        if input("Do you want to add more arrows? (y/n) ") == "n":
            break

