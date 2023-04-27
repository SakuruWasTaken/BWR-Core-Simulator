import os, sys, time, threading, random, math, traceback

# TODO: switch to more flexible GUI library
import PySimpleGUIWeb as sg

from helpers import rods_helper
import glob
import statistics

class simulator:
    def __init__(self):
        self.debug_mode = False

        # stuff for rods
        self.scram_active = False

        self.half_scram = False

        self.selected_cr = "02-19"

        self.cr_direction = 0
        # 0: not moving
        # 1: inserting
        # 2: withdrawing
        # 3: settling

        self.continuous_mode = 0
        # 0: stopped
        # 1: continuous insert
        # 2: continuous withdraw

        self.rod_commanded_movement = 0
        # 0: not moving
        # 1: inserting
        # 2: withdrawing

        self.target_insertion = 0

        self.scram_timer = -1

        self.previous_insertion = 0

        # actually running the simulator

        self.layout = rods_helper.generate_control_rods()

        threading.Thread(target=lambda: self.run_gui(self.layout), daemon=False).start()
        
        group = 1

        while group < glob.current_group:
            rods_helper.remove_group(group)
            group += 1
        self.model_timer()


    def withdraw_selected_cr(self):
        if glob.rod_withdraw_block != [] or self.cr_direction != 0:
            return

        # TODO: rod groups
        rod = self.selected_cr
        insertion = glob.control_rods.get(rod)["cr_insertion"]
        self.target_insertion = insertion + 2
  
        
        # TODO: rod overtravel check
        if int(insertion) >= 48:
            return

        # time delay to unlatch control
        time.sleep(random.uniform(0.00, 0.04))

        glob.moving_rods.append(rod)
        self.previous_insertion = insertion
        self.rod_commanded_movement = 2
        

        # insert (unlatch) for 0.6 seconds before withdrawal
        runs = 0
        while runs < 6 and not self.scram_active: 
            self.cr_direction = 1
            insertion -= 0.082
            if self.debug_mode:
                print(f"IN: {insertion}")
            glob.control_rods[rod].update(cr_insertion=insertion)
            time.sleep(random.uniform(0.085, 0.115))
            runs += 1

        time.sleep(random.uniform(0, 0.15))

        # withdraw for 1.5 seconds
        runs = 0
        while runs < 15 and not self.scram_active: 
            self.cr_direction = 2
            insertion += 0.144
            if self.debug_mode:
                print(f"WD: {insertion}")
            glob.control_rods[rod].update(cr_insertion=insertion)
            time.sleep(random.uniform(0.090, 0.11))
            runs += 1

        # TODO: simulate switching overlap between withdraw control and settle control

        # let the rod settle into the notch
        runs = 0
        while runs < 60 and not self.scram_active: 
            self.cr_direction = 3
            if insertion >= self.target_insertion:
                insertion = self.target_insertion
            else:
                insertion += 0.0064
            
            if self.debug_mode: 
                print(f"SE: {insertion}")
            glob.control_rods[rod].update(cr_insertion=insertion)
            time.sleep(random.uniform(0.090, 0.11))
            runs += 1
        glob.control_rods[rod].update(cr_insertion=self.target_insertion)

        if glob.rod_select_error:
            glob.rod_withdraw_block.append(f"Withdraw error on {rod}, correct position is {int(self.previous_insertion)}")

        try:
            glob.moving_rods.remove(rod)
        except:
            pass
        self.cr_direction = 0
        self.rod_commanded_movement = 0

    def continuous_withdraw_selected_cr(self):
        if glob.rod_withdraw_block != [] or self.cr_direction != 0:
            return

        # TODO: rod groups
        rod = self.selected_cr
        insertion = glob.control_rods.get(rod)["cr_insertion"]

        # TODO: rod overtravel check
        if int(insertion) >= 48:
            return

        # time delay to unlatch control
        time.sleep(random.uniform(0.00, 0.04))
        glob.moving_rods.append(rod)
        self.target_insertion = insertion + 2
        self.previous_insertion = insertion
        self.rod_commanded_movement = 2
        

        # insert (unlatch) for 0.5 seconds before withdrawal
        runs = 0
        while runs < 5 and not self.scram_active: 
            self.cr_direction = 1
            insertion -= 0.082
            if self.debug_mode:
                print(f"IN: {insertion}")
            glob.control_rods[rod].update(cr_insertion=insertion)
            time.sleep(random.uniform(0.085, 0.115))
            runs += 1

        time.sleep(random.uniform(0, 0.15))

        # withdraw for 1.4 seconds each cycle
        self.continuous_mode = 2
        self.cr_direction = 2
        
        while self.continuous_mode == 2 and glob.rod_withdraw_block == [] and not self.scram_active and self.target_insertion <= 46 or self.target_insertion == 48:
            runs = 0
            while runs < 14 and not self.scram_active: 
                insertion += 0.1435
                if self.debug_mode:
                    print(f"CWD: {insertion}")
                glob.control_rods[rod].update(cr_insertion=insertion)
                time.sleep(random.uniform(0.090, 0.11))
                runs += 1

            self.previous_insertion = self.target_insertion

            if glob.rod_withdraw_block == [] and not self.scram_active and self.continuous_mode == 2 and self.target_insertion != 48:
                if glob.rod_select_error:
                    glob.rod_withdraw_block.append(f"Withdraw error on {rod}, correct position is {int(self.previous_insertion) - 2}")
                    break
                self.target_insertion += 2
                if self.debug_mode:
                    print(f"target insertion changed: {self.target_insertion}")
            else:
                break
            
        self.previous_insertion = self.target_insertion
        self.continuous_mode = 0

        # TODO: simulate switching overlap between withdraw control and settle control

        # let the rod settle into the notch
        runs = 0
        while runs < 60 and not self.scram_active: 
            self.cr_direction = 3
            if insertion >= self.target_insertion:
                insertion = self.target_insertion
            else:
                insertion += 0.0070
            
            if self.debug_mode: 
                print(f"SE: {insertion}")
            glob.control_rods[rod].update(cr_insertion=insertion)
            time.sleep(random.uniform(0.090, 0.11))
            runs += 1
        glob.control_rods[rod].update(cr_insertion=self.target_insertion)

        try:
            glob.moving_rods.remove(rod)
        except:
            pass
        self.cr_direction = 0
        self.rod_commanded_movement = 0

    def insert_selected_cr(self):
        if glob.rod_insert_block != [] or self.cr_direction != 0:
            return

        # TODO: rod groups
        rod = self.selected_cr
        insertion = glob.control_rods.get(rod)["cr_insertion"]
        self.target_insertion = insertion - 2
        
        # TODO: rod overtravel check
        if int(insertion) <= 0:
            return


        # time delay to insert control
        time.sleep(random.uniform(0.00, 0.04))

        glob.moving_rods.append(rod)
        self.previous_insertion = insertion
        self.rod_commanded_movement = 1

        # insert for 2.9 seconds
        runs = 0
        while runs < 29 and not self.scram_active: 
            self.cr_direction = 1
            insertion -= 0.082
            if self.debug_mode:
                print(f"IN: {insertion}")
            glob.control_rods[rod].update(cr_insertion=insertion)
            time.sleep(random.uniform(0.090, 0.11))
            runs += 1

        # let the rod settle into the notch
        runs = 0
        while runs < 53 and not self.scram_active: 
            self.cr_direction = 3
            if insertion >= self.target_insertion:
                insertion = self.target_insertion
            else:
                insertion += 0.0076
            if self.debug_mode:
                print(f"SE: {insertion}")
            glob.control_rods[rod].update(cr_insertion=insertion)
            time.sleep(random.uniform(0.090, 0.11))
            runs += 1
        glob.control_rods[rod].update(cr_insertion=self.target_insertion)
        if f"Withdraw error on {rod}, correct position is {int(insertion)}" in glob.rod_withdraw_block:
            glob.rod_withdraw_block.remove(f"Withdraw error on {rod}, correct position is {int(insertion)}")

        try:
            glob.moving_rods.remove(rod)
        except:
            pass
        self.cr_direction = 0
        self.rod_commanded_movement = 0

    def continuous_insert_selected_cr(self):
        if glob.rod_insert_block != [] or self.cr_direction != 0:
            return

        # TODO: rod groups
        rod = self.selected_cr
        insertion = glob.control_rods.get(rod)["cr_insertion"]
        
        
        # TODO: rod overtravel check
        if int(insertion) <= 0:
            return

        # time delay to insert control
        time.sleep(random.uniform(0.00, 0.04))
        glob.moving_rods.append(rod)
        self.target_insertion = insertion - 2
        self.previous_insertion = insertion
        self.rod_commanded_movement = 1
        self.continuous_mode = 1
        self.cr_direction = 1

        # insert for 2.9 seconds each cycle
        while self.continuous_mode == 1 and glob.rod_insert_block == [] and not self.scram_active and self.target_insertion >= 2 or self.target_insertion == 0:
            runs = 0
            while runs < 24 and not self.scram_active: 
                insertion -= 0.0832
                if self.debug_mode:
                    print(f"CIN: {insertion}")
                glob.control_rods[rod].update(cr_insertion=insertion)
                time.sleep(random.uniform(0.090, 0.11))
                runs += 1
            self.previous_insertion = self.target_insertion
            if glob.rod_insert_block == [] and not self.scram_active and self.continuous_mode == 1 and self.target_insertion != 0:
                if f"Withdraw error on {rod}, correct position is {int(self.previous_insertion)}" in glob.rod_withdraw_block:
                    glob.rod_withdraw_block.remove(f"Withdraw error on {rod}, correct position is {int(self.previous_insertion)}")
                self.target_insertion -= 2
                if self.debug_mode:
                    print(f"target insertion changed: {self.target_insertion}")
            else:
                break

        # move the rod a tiny bit further for settle
        # TODO: is this realistic?
        if not self.scram_active:
            runs = 0
            while runs < 4 and not self.scram_active: 
                insertion -= 0.082
                glob.control_rods[rod].update(cr_insertion=insertion)
                time.sleep(random.uniform(0.090, 0.11))
                runs += 1
        
        self.previous_insertion = self.target_insertion
        self.continuous_mode = 0

        # let the rod settle into the notch
        runs = 0
        while runs < 53 and not self.scram_active: 
            self.cr_direction = 3
            if insertion >= self.target_insertion:
                insertion = self.target_insertion
            else:
                insertion += 0.0076
            if self.debug_mode:
                print(f"SE: {insertion}")
            glob.control_rods[rod].update(cr_insertion=insertion)
            time.sleep(random.uniform(0.090, 0.11))
            runs += 1
        glob.control_rods[rod].update(cr_insertion=self.target_insertion)

        try:
            glob.moving_rods.remove(rod)
        except:
            pass
        self.cr_direction = 0
        self.rod_commanded_movement = 0


    def control_rods_cycle(self):
        for rod_number, rod_info in glob.control_rods.items():
            cr_insertion = rod_info["cr_insertion"]
            cr_accum_trouble = rod_info["cr_accum_trouble"]
            cr_scram = True if rod_info["cr_scram"] == True or self.scram_active == True else False
            cr_drift_alarm = rod_info["cr_drift_alarm"]
            cr_selected = True if self.selected_cr == rod_number else False

            if cr_scram == True: 
                if self.scram_timer == -1:
                    self.scram_timer = 120
                glob.rod_withdraw_block.append("SCRAM")
                if cr_insertion != 0:
                    if self.scram_timer < 117:
                        cr_accum_trouble = True

                    # in a few videos from columbia's simulator, some of the "DRIFT" indicators
                    # seem to remain lit following a scram, i do not know what causes this, 
                    # but i will do this to replicate that effect.
                    # TODO: fix and re-enable
                    #if cr_insertion == 48 and random.randint(1, 15) == 5:
                        #cr_drift_alarm = True

                    if cr_insertion != 0 and self.scram_timer < 114:
                        if not rod_number in glob.moving_rods:
                            glob.moving_rods.append(rod_number)
                        # the time from full out to full in is around ~2.6 seconds
                        cr_insertion -= 2.23
                        if cr_insertion <= 0:
                            cr_insertion = 0
                else:
                    try:
                        glob.moving_rods.remove(rod_number)
                    except:
                        pass

            glob.control_rods[rod_number].update(cr_insertion=cr_insertion, cr_scram=cr_scram, cr_accum_trouble=cr_accum_trouble, cr_drift_alarm=cr_drift_alarm)

    def model_timer(self):
        # TODO: proper timer instead of just time.sleep
        while True:
            threading.Thread(target=lambda: self.control_rods_cycle(), daemon=False).start()
            # TODO: only calculate when rods are moved
            # TODO: finish group calculation
            threading.Thread(target=lambda: rods_helper.calculate_current_group(), daemon=False).start()
            if self.scram_timer >= 1:
                self.scram_timer -= 1
            time.sleep(0.1)


    def reset_scram(self):
        if self.scram_active == True:
            self.scram_active = False
            self.half_scram = False
            self.scram_timer = -1
            # short pause to wait for control_rods_cycle to finish
            time.sleep(0.1)
            glob.rod_withdraw_block.remove("SCRAM")
            for rod_number, rod_info in glob.control_rods.items():
                glob.control_rods[rod_number].update(cr_scram=False, cr_accum_trouble=False, cr_drift_alarm=False)

            # TODO: fix
            current_group = 0
            current_group_rods = ['26-31', '34-39', '42-31', '34-23', '26-15', '18-23', '10-31', '18-39', '26-47', '42-47', '50-39', '50-23', '42-15', '34-07', '18-07', '10-15', '02-23', '02-39', '10-47', '18-55', '34-55', '58-31']
            current_group_info = {'rod_group': 1, 'min_position': 0, 'max_position': 48}

        elif self.half_scram == True:
            self.half_scram = False



    def run_gui(self, layout):
        column_1 = layout
        column_2 = [[sg.Text("Rod Motion")], 
            [sg.Button("Withdraw", size=(5.2, 2)), sg.Button("Insert", size=(5.2, 2))],
            [sg.Button("Cont.\nWithdraw", size=(5.2, 2)), sg.Button("Stop", size=(5.2, 2)), sg.Button("Cont.\nInsert", size=(5.2, 2))],
            [sg.Button("Manual\nSCRAM\nTrip A", size=(5.2, 2)), sg.Button("Manual\nSCRAM\nTrip B", size=(5.2, 2)), sg.Button("Reset SCRAM", size=(5.2, 2))]
        ]
        column_3 = [[sg.Text("CR Guide", size=(15,1), justification="center", background_color="black")],
            [sg.Text("NEX 00-00 00→00", text_color="yellowgreen", key="cr_guide_next", size=(15, 1), justification="center", font=("monospace", 15), background_color="black")],
            [sg.Text("SEL 00-00 00→00", text_color="white", key="cr_guide_selected", size=(15, 1), justification="center", font=("monospace", 15), background_color="black")]
        ]
        column_4 = [[sg.Text("Information")], 
            [
                sg.Text("Rod Withdraw Block", text_color='greenyellow', key="withdraw_block"),
                sg.Text("Rod Insert Block", text_color='greenyellow', key="insert_block"),
                sg.Text("Half SCRAM", text_color='greenyellow', key="half_scram"),
                sg.Text("SCRAM Active", text_color='greenyellow', key="scram_active")
            ],
            [
                sg.Text("Selected rod: 02-19", key="selected_rod"),
                sg.Text("Current group: 3", key="current_group"),
                sg.Text("Rod Select Error", text_color='greenyellow', key="rod_select_error")
            ],
            [
                sg.Text("Withdraw", text_color='greenyellow', key="withdraw_lt"),
                sg.Text("Insert", text_color='greenyellow', key="insert_lt"),
                sg.Text("Settle", text_color='greenyellow', key="settle_lt")
                
            ]
        ]

        # TODO: mode switch
        rods_number = 0
        rods = []
        y = 59
        for rod_number, rod_info in glob.control_rods.items():
            new_y = rod_number.split("-")[1]
            if new_y != y:
                column_3.append(rods)
                rods = []
            rods.append(sg.Text("00", justification="center", key=f"ROD_DISPLAY_{rod_number}", text_color='darkred', pad=(2,2), background_color="black"))
            rods_number += 1
            y = new_y
        column_3.append(rods)

        # Create the window
        layout = [[sg.Column(column_1, element_justification='c'),
                   sg.Column(column_2, element_justification='c'),
                   sg.Column(column_3, element_justification='c', background_color="black"),
                   sg.Column(column_4, element_justification='c'),
                 ]]
        window = sg.Window("Window Title", layout, element_padding=(4,4))

        # Display and interact with the Window using an Event Loop
        while True:
            event, values = window.read(timeout=100 if not self.scram_active else 2.4)
            if event == sg.TIMEOUT_EVENT:
                # Update CR Guide
                # TODO: improve this horrible code
                try:
                    rod = glob.control_rods.get(glob.current_group_rods[0])
                    
                    if not self.scram_active:
                        current_position = int(rod['cr_insertion'])

                        if rod_number in glob.moving_rods:
                            current_position = int(self.previous_insertion)

                        if len(str(current_position)) == 1:
                            current_position = f"0{current_position}"
                        rod_number = glob.current_group_rods[0]         
                        if rod_number == self.selected_cr:

                            current_position = int(rod['cr_insertion'])

                            if rod_number in glob.moving_rods:
                                current_position = int(self.previous_insertion)

                            if len(str(current_position)) == 1:
                                current_position = f"0{current_position}"
                            selected_to_position = glob.current_group_info['max_position']
                            if len(str(selected_to_position)) == 1:
                                selected_to_position = f"0{selected_to_position}"
                            
                            cr_guide_selected = f"SEL {rod_number} {current_position}→{selected_to_position}"
                            cr_guide_next = f"NEX   -     →  "
                        else:
                            next_to_position = glob.current_group_info['max_position']
                            if len(str(next_to_position)) == 1:
                                next_to_position = f"0{next_to_position}"

                            cr_guide_next = f"NEX {rod_number} {current_position}→{next_to_position}"
                            selected_to_position = int(glob.current_group_info['max_position'] if self.selected_cr in glob.current_group_rods else glob.control_rods.get(self.selected_cr)['cr_insertion'] if not self.selected_cr in glob.moving_rods else self.previous_insertion)
                            if self.selected_cr in glob.moving_rods:
                                selected_current_position = int(self.previous_insertion)
                            else:
                                selected_current_position = int(glob.control_rods.get(self.selected_cr)['cr_insertion'])

                            # TODO: put this in a function or something
                            if len(str(selected_current_position)) == 1:
                                selected_current_position = f"0{selected_current_position}"

                            if len(str(selected_to_position)) == 1:
                                selected_to_position = f"0{selected_to_position}"

                            cr_guide_selected = f"SEL {self.selected_cr} {selected_current_position}→{selected_to_position}"
                    else:
                        cr_guide_selected = f"SEL   -     →  "
                        cr_guide_next = f"NEX   -     →  "
                except Exception:
                    # exceptions are normal here in certain cases (for example: switching to a new group)
                    #print(traceback.format_exc())
                    # TODO: fix pysimplegui correcting multiple spaces to just one space
                    cr_guide_next = f"NEX   -     →  "
                    cr_guide_selected = f"SEL   -     →  "

                window[f"cr_guide_next"].update(cr_guide_next)
                window[f"cr_guide_selected"].update(cr_guide_selected)

                # Update rod positions
                window["withdraw_block"].update(text_color="darkred" if glob.rod_withdraw_block != [] else "greenyellow")
                window["insert_block"].update(text_color="darkred" if glob.rod_insert_block != [] else "greenyellow")
                window["scram_active"].update(text_color="darkred" if self.scram_active else "greenyellow")
                window["half_scram"].update(text_color="darkred" if self.half_scram else "greenyellow")
                window["selected_rod"].update(f"Selected rod: {self.selected_cr}")
                window["current_group"].update(f"Current group: {glob.current_group}")
                window["withdraw_lt"].update(text_color="darkred" if self.cr_direction == 2 else "greenyellow")
                window["insert_lt"].update(text_color="darkred" if self.cr_direction == 1 else "greenyellow")
                window["settle_lt"].update(text_color="darkred" if self.cr_direction == 3 else "greenyellow")
                window["rod_select_error"].update(text_color="darkred" if glob.rod_select_error else "greenyellow")

                for rod_number, rod_info in glob.control_rods.items():
                    rod_insertion = int(rod_info["cr_insertion"])
                    # these colours are from kashiwazaki-kariwa/fukushima daini (toshiba RPIS), i'm not entirely sure how accurate this is, though
                    try:
                        next_rod = glob.current_group_rods[0]
                    except:
                        next_rod = ""
                    color = "aqua" if rod_number == self.selected_cr else "mediumpurple" if rod_number == next_rod else "yellow" if rod_number in glob.current_group_rods else "darkred" if rod_insertion == 48 or rod_insertion != 0 and self.scram_active else "yellowgreen" if rod_insertion == 0 else "black" if rod_insertion == 49 else "white"
                    #if rod_number in glob.moving_rods:
                        #rod_insertion = round(rod_info["cr_insertion"], 5)
                    font = ("monospace", 15)
                    # check if rod is selected
                    #if rod_number == self.selected_cr:
                        #font = ("monospace", 18)
                    
                    rod_insertion = int(rod_insertion)
                    
                    if rod_number in glob.moving_rods and not self.scram_active:
                        rod_insertion = int(self.previous_insertion)

                    if self.scram_active and rod_insertion != 0:
                        rod_insertion = "--"

                    elif rod_insertion == 48 and not rod_number in glob.moving_rods:
                        rod_insertion = "**"

                    if len(str(rod_insertion)) == 1:
                        rod_insertion = f"0{rod_insertion}"

                    window[f"ROD_DISPLAY_{rod_number}"].update(rod_insertion, text_color=color, font=font)

            elif len(event) == 5 and "-" in event:
                # we can assume it's a rod
                if glob.moving_rods == [] and glob.rod_select_block == False:
                    window.FindElement(self.selected_cr).Update(button_color=("white", "#283b5b"))
                    if event == next_rod:
                        glob.rod_select_error = False
                    else:
                        glob.rod_select_error = True
                        
                    self.selected_cr = event
                    window.FindElement(event).Update(button_color=("#283b5b", "white"))


            elif event == "Manual\nSCRAM\nTrip A":
                if self.half_scram == True:
                    self.scram_active = True
                else:
                    self.half_scram = True

            elif event == "Manual\nSCRAM\nTrip B":
                if self.half_scram == True:
                    self.scram_active = True
                else:
                    self.half_scram = True

            elif event == "Withdraw":
                threading.Thread(target=lambda: self.withdraw_selected_cr(), daemon=False).start()

            elif event == "Insert":
                threading.Thread(target=lambda: self.insert_selected_cr(), daemon=False).start()

            elif event == "Cont.\nWithdraw":
                threading.Thread(target=lambda: self.continuous_withdraw_selected_cr(), daemon=False).start()

            elif event == "Cont.\nInsert":
                threading.Thread(target=lambda: self.continuous_insert_selected_cr(), daemon=False).start()

            elif event == "Stop":
                self.continuous_mode = 0

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