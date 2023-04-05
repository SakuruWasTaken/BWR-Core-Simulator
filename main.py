import os, sys, time, threading, random, asyncio

from sqlite3worker import Sqlite3Worker

import helpers
import glob
import PySimpleGUIWeb as sg

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

        
        threading.Thread(target=lambda: self.run_gui(helpers.generate_control_rods()), daemon=False).start()
        
        print(glob.db.execute("SELECT * FROM control_rods"))

        self.average_reactivity = 0.00
        self.average_heat = 0.00
        self.average_void = 0.00
        self.average_power_range = 0.00
        self.source_range = 0.00

        self.mode_switch_position = 2
        # 0: shutdown
        # 1: refuel
        # 2: startup
        # 3: run

        self.scram_active = False
        self.selected_cr = "02-19"

        self.cr_moving = False

        self.cr_direction = 0
        # 0: not moving
        # 1: inserting
        # 2: withdrawing
        # 3: settling

        self.rod_withdraw_block = False
        self.rod_insert_block = False

        self.model_timer()


    def withdraw_selected_cr(self, continuous = False):
        if self.rod_withdraw_block or self.cr_moving:
            return

        # TODO: rod groups

        # TODO: fix rods still trying to withdraw during scram
        
        rod = glob.db.execute("SELECT rod_number, cr_insertion FROM control_rods WHERE cr_selected = 1")[0]
        insertion = rod[1]
        target_insertion = insertion + 1
        rod = rod[0]
        
        # TODO: rod overtravel check
        if int(insertion) >= 48:
            return

        # insert for 0.6 seconds before withdrawl
        runs = 0
        while runs < 6: 
            self.cr_direction = 1
            insertion -= 0.092
            glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [insertion, rod]) 
            time.sleep(0.1)
            runs += 1

        time.sleep(0.1)

        # withdraw for 1.5 seconds
        runs = 0
        while runs < 15: 
            self.cr_direction = 2
            insertion += 0.092
            glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [insertion, rod]) 
            time.sleep(0.1)
            runs += 1

        # let the rod settle into the notch
        if continuous == False:
            runs = 0
            while runs < 50: 
                self.cr_direction = 3
                if insertion >= target_insertion:
                    insertion = target_insertion
                else:
                    insertion += 0.0038
                    
                glob.db.execute("UPDATE control_rods SET cr_insertion = ? WHERE rod_number = ?", [insertion, rod]) 
                time.sleep(0.1)
                runs += 1
            insertion = target_insertion
        self.cr_moving = False
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

            if cr_scram == True and cr_insertion != 0:
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

            glob.db.execute("UPDATE control_rods SET cr_insertion = ?, cr_scram = ?, cr_selected = ?, cr_accum_trouble = ?, cr_drift_alarm = ? WHERE rod_number = ?", 
                            [cr_insertion, int(cr_scram), int(cr_selected), int(cr_accum_trouble), int(cr_drift_alarm), rod_number]
            )

    def model_timer(self):
        # TODO: proper timer instead of just time.sleep
        while True:
            threading.Thread(target=self.control_rods_cycle()).start()
            time.sleep(0.1)


    def rod_display(self):
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

            final_message = f"{final_message} {rod_insertion}"

        return final_message # goodbye


    def run_gui(self, layout):
        layout.append([sg.Button("Withdraw"), sg.Button("Insert (TODO)"), sg.Button("SCRAM")])
        core = self.rod_display().split("\n")
        lines = 0
        for line in core:
            layout.append([sg.Text(line, justification="center", key=str(lines))])
            lines += 1
        sg.theme("Dark Grey 4")

        # Create the window
        window = sg.Window("Window Title", layout, element_justification='c', element_padding=(4,4))

        # Display and interact with the Window using an Event Loop
        while True:
            event, values = window.read(timeout=100 if not self.scram_active else 20)
            if event == sg.TIMEOUT_EVENT:
                core = self.rod_display().split("\n")
                lines = 0
                for line in core:
                    window[str(lines)].update(line)
                    lines += 1
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