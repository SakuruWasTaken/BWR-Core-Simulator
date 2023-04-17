import os, sys, time, threading, random

from sqlite3worker import Sqlite3Worker
# TODO: switch to more flexible GUI library
import PySimpleGUIWeb as sg

from helpers import rods_helper
import glob
import statistics

class simulator:
    def __init__(self):
        # delete the old sqlite database
        try:
            os.remove("BWR_model.db")
            os.remove("BWR_model.db-journal")
        except:
            pass
        glob.db = Sqlite3Worker("BWR_model.db")
        glob.db.execute("CREATE TABLE control_rods(rod_number varchar(5) NOT NULL, heat double, flux double, void double, cr_insertion double, cr_scram int, cr_selected int, cr_accum_trouble int, cr_drift_alarm int)")

        self.debug_mode = False

        # stuff for rods

        self.mode_switch_position = 3
        # 0: shutdown
        # 1: refuel
        # 2: startup
        # 3: run

        self.scram_active = False
        self.selected_cr = "02-19"

        self.moving_rods = []
        self.cr_direction = 0
        # 0: not moving
        # 1: inserting
        # 2: withdrawing
        # 3: settling

        self.rod_withdraw_block = False
        self.rod_insert_block = False

        self.scram_timer = -1

        self.current_group = 2

        # stuff for physics
        # all of this stuff related to pysics is currently unused experimental stuff

        self.reactivity = 0.00
        self.control_rod_coefficient = 44.2043795620438
        self.void_coefficient = -7.9543795620438
        self.heat = 290.00
        self.heat_coefficient = -36.25

        self.aprm = 100.0

        # actually running the simulator

        self.layout = rods_helper.generate_control_rods()

        threading.Thread(target=lambda: self.run_gui(self.layout), daemon=False).start()
        
        group = 0
        while group < 72:
            rods_helper.remove_group(group)
            group += 1

        self.model_timer()

        


    def withdraw_selected_cr(self, continuous = False):
        if self.rod_withdraw_block or self.cr_direction != 0:
            return

        # TODO: rod groups
        rod = glob.db.execute("SELECT rod_number, cr_insertion FROM control_rods WHERE cr_selected = 1")[0]

        insertion = rod[1]
        target_insertion = insertion + 1
        rod = rod[0]
        
        # TODO: rod overtravel check
        if int(insertion) >= 48:
            return

        self.moving_rods.append(rod)

        # insert for 0.6 seconds before withdrawl
        runs = 0
        while runs < 6 and not self.scram_active: 
            self.cr_direction = 1
            insertion -= 0.041
            if self.debug_mode:
                print(f"IN: {insertion}")
            glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [insertion, rod]) 
            time.sleep(0.1)
            runs += 1

        time.sleep(0.1)

        # withdraw for 1.5 seconds
        runs = 0
        while runs < 15 and not self.scram_active: 
            self.cr_direction = 2
            insertion += 0.072
            if self.debug_mode:
                print(f"WD: {insertion}")
            glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [insertion, rod]) 
            time.sleep(0.1)
            runs += 1

        # let the rod settle into the notch
        # TODO: settle after continuous withdraw
        if continuous == False:
            runs = 0
            while runs < 60 and not self.scram_active: 
                self.cr_direction = 3
                if insertion >= target_insertion:
                    insertion = target_insertion
                else:
                    insertion += 0.0032
                
                if self.debug_mode: 
                    print(f"SE: {insertion}")
                glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [insertion, rod]) 
                time.sleep(0.1)
                runs += 1
            glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [target_insertion, rod]) 

        try:
            self.moving_rods.remove(rod)
        except:
            pass
        self.cr_direction = 0

    def insert_selected_cr(self, continuous = False):
        if self.rod_insert_block or self.cr_direction != 0:
            return

        # TODO: rod groups
        
        rod = glob.db.execute("SELECT rod_number, cr_insertion FROM control_rods WHERE cr_selected = 1")[0]
        insertion = rod[1]
        target_insertion = insertion - 1
        rod = rod[0]
        
        # TODO: rod overtravel check
        if int(insertion) <= 0:
            return

        self.moving_rods.append(rod)

        # insert for 2.9 seconds
        runs = 0
        while runs < 29 and not self.scram_active: 
            self.cr_direction = 1
            insertion -= 0.041
            if self.debug_mode:
                print(f"IN: {insertion}")
            glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [insertion, rod]) 
            time.sleep(0.1)
            runs += 1

        time.sleep(1.4)

        # let the rod settle into the notch
        if continuous == False:
            runs = 0
            while runs < 53 and not self.scram_active: 
                self.cr_direction = 3
                if insertion >= target_insertion:
                    insertion = target_insertion
                else:
                    insertion += 0.0038
                if self.debug_mode:
                    print(f"SE: {insertion}")
                glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [insertion, rod]) 
                time.sleep(0.1)
                runs += 1
            glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [target_insertion, rod]) 

        try:
            self.moving_rods.remove(rod)
        except:
            pass
        self.cr_direction = 0



    def control_rods_cycle(self):
        control_rods = glob.db.execute("SELECT * FROM control_rods")
        for rod in control_rods:
            rod_number = rod[0]
            cr_insertion = float(rod[4])
            cr_accum_trouble = bool(rod[7])

            # this is done so it is possible to scram one rod without scramming the whole reactor
            # iirc this is done in real life for testing purposes.
            cr_scram = True if bool(rod[5]) == True or self.scram_active == True else False

            cr_drift_alarm = bool(rod[8])
            cr_selected = True if bool(rod[6]) == True and self.selected_cr == rod_number else False

            if cr_scram == True: 
                if self.scram_timer == -1:
                    self.scram_timer = 120
                self.rod_withdraw_block = True
                if cr_insertion != 0:
                    if not rod_number in self.moving_rods:
                        self.moving_rods.append(rod_number)
                    cr_accum_trouble = True

                    # in a few videos from columbia's simulator, some of the "DRIFT" indicators
                    # seem to remain lit following a scram, i do not know what causes this, 
                    # but i will do this to replicate that effect.
                    if cr_insertion == 48 and random.randint(1, 15) == 5:
                        cr_drift_alarm = True

                    if cr_insertion != 0:
                        # the time from full out to full in is around ~2.6 seconds
                        cr_insertion -= 1.84
                        if cr_insertion <= 0:
                            cr_insertion = 0
                else:
                    try:
                        self.moving_rods.remove(rod_number)
                    except:
                        pass

            glob.db.execute("UPDATE control_rods SET cr_insertion = ?, cr_scram = ?, cr_selected = ?, cr_accum_trouble = ?, cr_drift_alarm = ? WHERE rod_number = ?", 
                            [cr_insertion, int(cr_scram), int(cr_selected), int(cr_accum_trouble), int(cr_drift_alarm), rod_number]
            )

    def physics_cycle(self):
        # unused experimental stuff

        # TODO: calculate physics for each rod in reactor

        # calculate control rod coefficient
        control_rods = glob.db.execute("SELECT cr_insertion FROM control_rods")
        #print(glob.db.execute("SELECT COUNT(*) FROM control_rods"))
        rods = []
        for rod in control_rods:
            rods.append(float(rod[0]))
        average_insertion = statistics.mean(rods)
        # TODO: calculate worth for individual rods
        self.control_rod_coefficient = average_insertion
        #print(average_insertion)
        #print(self.control_rod_coefficient)

        # calculate heat coefficient
        self.heat_coefficient = (self.heat - (self.heat/8)) - self.heat
        #print(self.heat_coefficient)


    def model_timer(self):
        # TODO: proper timer instead of just time.sleep
        while True:
            threading.Thread(target=lambda: self.control_rods_cycle(), daemon=False).start()
            threading.Thread(target=lambda: self.physics_cycle(), daemon=False).start()
            if self.scram_timer >= 1:
                self.scram_timer -= 1
            elif self.scram_timer != -1:
                self.rod_insert_block = True
            time.sleep(0.1)


    def reset_scram(self):
        if self.scram_timer == 0:
            glob.db.execute("UPDATE control_rods SET cr_scram = 0, cr_drift_alarm = 0, cr_accum_trouble = 0")
            self.rod_withdraw_block = False
            self.rod_insert_block = False
            self.scram_active = False
            self.scram_timer = -1

    def rod_display(self):
        # TODO: move this into the GUI code
        all_rods_insertion = glob.db.execute("SELECT rod_number, cr_insertion FROM control_rods")
        rods_printed_row = 0
        y = 0
        final_message = ""
        for rod in all_rods_insertion:
            # i know there are better ways to do this, but this is temporary code anyways (as i am planning on implementing a realistic full core display), so i don't care.
            rod_number = rod[0]
            rod_insertion = int(rod[1])
            if y != int(rod_number.split("-")[1]):
                final_message = f"{final_message}\n"
            y = int(rod_number.split("-")[1])

            if rod_number in self.moving_rods:
                rod_insertion = "--"

            if len(str(rod_insertion)) == 1:
                rod_insertion = f"0{rod_insertion}"

            final_message = f"{final_message}|{rod_insertion}{'sel' if self.selected_cr == rod_number else ''}"
        return final_message # goodbye


    def run_gui(self, layout):
        
        column_1 = layout
        column_2 = [[sg.Text("Rod Motion")], [sg.Button("Withdraw", size=(5.2, 2)), sg.Button("Insert", size=(5.2, 2)), sg.Button("SCRAM", size=(5.2, 2)), sg.Button("Reset SCRAM", size=(5.2, 2))]]
        column_3 = [[sg.Text("Rod Positions")]]
        column_4 = [[sg.Text("Information")], 
        [
            sg.Text("Rod Withdraw Block", text_color='greenyellow', key="withdraw_block"),
            sg.Text("Rod Insert Block", text_color='greenyellow', key="insert_block"),
            sg.Text("SCRAM Active", text_color='greenyellow', key="scram_active")
        ],
        [
            sg.Text("Selected rod: 02-19", key="selected_rod"),
            sg.Text("Current group: 3", key="current_group")
        ],
        [
            sg.Text("Withdraw", text_color='greenyellow', key="withdraw_lt"),
            sg.Text("Insert", text_color='greenyellow', key="insert_lt"),
            sg.Text("Settle", text_color='greenyellow', key="settle_lt")
            
        ]
        ]
        # TODO: mode switch
        core = self.rod_display().split("\n")
        rods_number = 0
        for line in core:
            rods = []
            for rod in line.split("|"):
                rods.append(sg.Text(rod, justification="center", key=f"ROD_DISPLAY_{str(rods_number)}", text_color='darkred', pad=(2,2)))
                rods_number += 1
            column_3.append(rods)

        # Create the window
        layout = [[sg.Column(column_1, element_justification='c'),
                   sg.Column(column_2, element_justification='c'),
                   sg.Column(column_3, element_justification='c'),
                   sg.Column(column_4, element_justification='c'),
                 ]]
        window = sg.Window("Window Title", layout, element_padding=(4,4))

        # Display and interact with the Window using an Event Loop
        while True:
            event, values = window.read(timeout=100 if not self.scram_active else 2.4)
            if event == sg.TIMEOUT_EVENT:
                window["withdraw_block"].update(text_color="darkred" if self.rod_withdraw_block else "greenyellow")
                window["insert_block"].update(text_color="darkred" if self.rod_insert_block else "greenyellow")
                window["scram_active"].update(text_color="darkred" if self.scram_active else "greenyellow")
                window["selected_rod"].update(f"Selected rod: {self.selected_cr}")
                window["current_group"].update(f"Current group: {self.current_group + 1}")
                window["withdraw_lt"].update(text_color="darkred" if self.cr_direction == 2 else "greenyellow")
                window["insert_lt"].update(text_color="darkred" if self.cr_direction == 1 else "greenyellow")
                window["settle_lt"].update(text_color="darkred" if self.cr_direction == 3 else "greenyellow")

                core = self.rod_display().split("\n")
                rods_number = 0
                for line in core:
                    rods = line.split("|")
                    for rod in rods:
                        font = ("monospace", 15)
                        # check if rod is selected
                        if len(rod) >= 5:
                            font = ("monospace", 18)
                            rod = rod[:-3] # <--- cat face
                        color = "darkred" if rod == "48" or rod == "--" else "greenyellow" if rod == "00" else "black" if rod == "49" else "orange" 
                        window[f"ROD_DISPLAY_{str(rods_number)}"].update(rod, text_color=color, font=font)
                        rods_number += 1
            elif len(event) == 5 and "-" in event:
                # we can assume it's a rod
                # TODO: remove selected value from db and just use self.selected_cr
                self.selected_cr = event
                # this could potentially cause issues if a query happens in between but i'll fix it later
                glob.db.execute("UPDATE control_rods SET cr_selected = 0 WHERE cr_selected = 1")
                glob.db.execute("UPDATE control_rods SET cr_selected = 1 WHERE rod_number = ?", [event])

            elif event == "SCRAM":
                self.scram_active = True

            elif event == "Withdraw":
                threading.Thread(target=lambda: self.withdraw_selected_cr(), daemon=False).start()

            elif event == "Insert":
                threading.Thread(target=lambda: self.insert_selected_cr(), daemon=False).start()

            elif event == "Reset SCRAM":
                threading.Thread(target=lambda: self.reset_scram(), daemon=False).start()

            # See if user wants to quit or window was closed
            elif event == sg.WINDOW_CLOSED or event == "Quit":
                break

        # Finish up by removing from the screen
        window.close()
        os._exit(0)


try:
    simulator()
except KeyboardInterrupt:
    # TODO: exit gracefully
    os._exit(0)
except Exception as e:
    print(e) 
    os._exit(0)