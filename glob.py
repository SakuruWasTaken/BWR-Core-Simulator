from constants import rod_groups

control_rods = {}
    
# you can change this value to set the group you'll be on when the sim is run
current_group = 70

current_group_info = rod_groups.groups.get(current_group)
current_group_rods = rod_groups.group_rods.get(current_group_info["rod_group"])

#next_group_info = rod_groups.groups.get(current_group + 1)

#next_group_rods = rod_groups.groups.get(next_group_info["rod_group"])

moving_rods = []

rod_withdraw_block = []
rod_insert_block = []

rod_select_block = False

rod_select_error = True

mode_switch_position = 3
# 0: shutdown
# 1: refuel
# 2: startup
# 3: run
