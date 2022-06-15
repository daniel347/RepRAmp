import sounddevice as sd
import numpy as np
import serial
import time

serial_enable = True

microstep = 16
steps_per_rev = 200
mm_per_rev = 8
machine_pp_unit = microstep * steps_per_rev / mm_per_rev

block_dur = 1

def get_final_position_for_frequency(pos, freq, move_dir):
    feedrate = (freq / machine_pp_unit)
    print(f"feedrate: {feedrate}  move dir {move_dir}   move dir {pos}")
    x_final = pos[0] + move_dir * block_dur * feedrate
    return x_final, feedrate

com = "COM5"  # Change this to the COM port identified in Pronterface
ser = serial.Serial(port=com, baudrate=250000)
time.sleep(1)
"""
for command in get_setup_gcode():
    ser.write(command)
    ser.write(b'\r\n')
    time.sleep(0.1)
    """

ser.write(bytes(f"M92 X{machine_pp_unit} Y{machine_pp_unit} Z{machine_pp_unit}\r\n", encoding="utf8"))
time.sleep(0.1)

# A C8 note
final_pos, feedrate = get_final_position_for_frequency([0,0,0], 4096, 1)
print(final_pos)
print(feedrate * 60)

ser.write(bytes(f"G1 X{final_pos} Y0 Z0 F{feedrate * 60}\r\n", encoding='utf8'))
time.sleep(1)

# ser.close()  # Close serial connection
print('done')