import glob
import PySimpleGUIWeb as sg
from constants import rod_groups

def remove_group(group_to_remove):
    group_info = rod_groups.groups.get(group_to_remove)
    for rod_number in rod_groups.group_rods.get(group_info["rod_group"]):
        if "|" in rod_number:
            rod_number = rod_number.split("|")[0]
        glob.control_rods[rod_number].update(cr_insertion=float(group_info["max_position"]))

def calculate_current_group():
    # this is a very inefficient way of doing this but im too lazy to come up with a better way
    for group_number, group_info in rod_groups.groups.items():
        for rod_number in rod_groups.group_rods.get(group_info["rod_group"]):
            if group_number < glob.current_group:
                break
            if "|" in rod_number:
                rod_number = rod_number.split("|")[0]

            if int(glob.control_rods.get(rod_number)["cr_insertion"]) == group_info["max_position"] and not rod_number in glob.moving_rods:
                try:
                    glob.current_group_rods.remove(rod_number)
                except:
                    pass

                if len(glob.current_group_rods) == 0:
                    glob.current_group_info = rod_groups.groups.get(glob.current_group + 1)
                    next_group_rods_formatted = []
                    next_group_rods = rod_groups.group_rods.get(glob.current_group_info["rod_group"])
                    for rod in next_group_rods:
                        if "|" in rod:
                            rod = rod_number.split("|")[0]
                        next_group_rods_formatted.append(rod)

                    glob.current_group_rods = next_group_rods_formatted
                    glob.current_group += 1
                    return
            else:
                break



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
                rods_row.append(sg.Button(rod_number, size=(5.2, 2), button_color=("#283b5b" if rod_number == "02-19" else "white", "white" if rod_number == "02-19" else "#283b5b")))

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



