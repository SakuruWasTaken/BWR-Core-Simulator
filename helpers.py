import glob
import PySimpleGUIWeb as sg

def generate_control_rods():
    rods_not_full_out = [
        "26-27",
        "10-27",
        "42-27",
        "42-43",
        "26-43",
        "10-43",
        "18-35",
        "34-35",
        "26-11",
        "10-11",
        "42-11",
        "34-19",
        "18-19"
    ]

    layout = []

    x = 18
    y = 51
    rods_to_generate = 0
    rods_generated_row = 0
    rods_generated_total = 0

    # our reactor has a total of 137 rods
    while rods_generated_total < 137:
        # calculate how many control rods we need for each row, 
        # and our starting position on y (as the rods in a BWR core are in a circular pattern)
        if y == 51 or y == 3:
            rods_to_generate = 5
            x = 18
        elif y == 47 or y == 7:
            rods_to_generate = 9
            x = 10
        elif y == 43 or y == 11 or y == 39 or y == 15:
            rods_to_generate = 11
            x = 6
        elif y <= 35 and y >= 19:
            rods_to_generate = 13
            x = 2

        rods_row = []
        while x <= 50 and y <= 51:
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

                rod_insertion = "08" if rod_number in rods_not_full_out else "48"

                glob.db.execute("INSERT INTO control_rods (rod_number, heat, flux, void, cr_insertion, cr_scram, cr_selected, cr_accum_trouble, cr_drift_alarm) VALUES (?, 24.00, 0, 0, ?, 0, ?, 0, 0)", 
                    [rod_number, rod_insertion, 1 if rod_number == "02-19" else 0]
                )
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


