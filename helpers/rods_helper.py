import glob
import PySimpleGUIWeb as sg
from constants import rod_groups

def remove_group(group_to_remove):
    for rod in rod_groups.groups[group_to_remove]:
        rod = rod.split("|")
        glob.control_rods[rod[0]].update(cr_insertion=float(rod[1].split("-")[1]))


def generate_control_rods():
    layout = []

    x = 18
    y = 59
    rods_to_generate = 0
    rods_generated_row = 0
    rods_generated_total = 0

    # our reactor has a total of 185 rods
    while rods_generated_total < 185:
        # calculate how many control rods we need for each row, 
        # and our starting position on y (as the rods in a BWR core are in a circular pattern)
        if y == 59 or y == 3:
            rods_to_generate = 7
            x = 18
        elif y == 55 or y == 7:
            rods_to_generate = 9
            x = 14
        elif y == 51 or y == 11:
            rods_to_generate = 11
            x = 10
        elif y == 47 or y == 15:
            rods_to_generate = 13
            x = 6
        elif y <= 43 and y >= 19:
            rods_to_generate = 15
            x = 2

        rods_row = []
        while x <= 58 and y <= 59:
            # create rods
            while rods_generated_row < rods_to_generate:
                # there's probably a better way to do this...
                x_str = str(x)
                if len(x_str) < 2:
                    x_str = f"0{x_str}"

                y_str = str(y)
                if len(y_str) < 2:
                    y_str = f"0{y_str}"

                rod_number = f"{x_str}-{y_str}"

                glob.control_rods[rod_number] = {
                        "cr_insertion": 0.00,
                        "cr_scram": False,
                        "cr_accum_trouble": False,
                        "cr_drift_alarm": False
                }

                # size=(5.2, 2) makes the buttons 52x52px
                rods_row.append(sg.Button(rod_number, size=(5.2, 2)))

                # increment y by 4 because we only have a control rod per every four fuel assemblies
                x += 4

                # keep track of how many rods we're generating
                rods_generated_row += 1
                rods_generated_total += 1

            # move on to the next row
            layout.append(rods_row)
            rods_generated_row = 0
            y -= 4
            break

    return layout



