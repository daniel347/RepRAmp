import sounddevice as sd
import numpy as np
import math
import serial
import time
from scipy.signal.windows import hann
import matplotlib.pyplot as plt

duration = 60  # seconds
Fs = 48000
block_size = 4096

serial_enable = True

block_dur = block_size / Fs  # s
time_axis = np.linspace(0, block_size/Fs, block_size, endpoint=False)

print(sd.default.latency)

min_note_freq = 80
max_note_freq = 600

min_note_bin = round((min_note_freq / Fs) * block_size)
max_note_bin = round((max_note_freq / Fs) * block_size)

microstep = 16
steps_per_rev = 200
mm_per_rev = 8

num_axes = 3

hann_window = hann(block_size)

machine_pp_unit = microstep * steps_per_rev / mm_per_rev

machine_limits = np.array([50, 50, 25])
machine_safety = 10


data_freq_list = []
data_list = []
note_indices = []

pos = np.array([0, 0, 0])
move_dir = np.ones(3)

g_codes = []

freq_upscale_factor = 2

def get_setup_gcode():
    return [b"G21",
        b"G90",
        b"M82",
        b"M107",
        b"G28 X0 Y0",
        b"G28 Z0",
        b"G1 Z15.0 F9000",
        b"G92 E0",
        b"G1 F200 E3",
        b"G92 E0",
        b"G1 F9000"]


def update_move_dir(pos):
    global move_dir

    for i in range(num_axes):
        if pos[i] > (machine_limits[i]-machine_safety):
            move_dir[i] = -1
        elif pos[i] <= machine_safety:
            move_dir[i] = 1


def get_final_position_for_frequencies(pos, freq, move_dir):
    feedrate_vector = (freq / machine_pp_unit)
    final_pos = pos + move_dir * block_dur * feedrate_vector
    feedrate = math.sqrt(np.sum(feedrate_vector ** 2))

    print(f"feedrate: {feedrate * 60}  move dir {move_dir}   position {pos}")
    return final_pos, feedrate


def bin_to_note(bin):
    freq = (bin/block_size) * Fs
    midi_zero_freq = 8.18
    semitones_from_zero = round(12 * math.log2(freq/midi_zero_freq))

    return semitones_from_zero


def detect_main_notes(data):
    thresh = 0.1

    data_freq = np.fft.fft(data)
    main_notes = np.zeros(3)

    for i in range(num_axes):
        max_amp_bin = np.argmax(np.abs(data_freq[min_note_bin:max_note_bin])) + min_note_bin
        if np.abs(data_freq[max_amp_bin]) <= thresh:
            main_notes[i] = 0
        else:
            # Perform fine interpolation
            peak_data = data_freq[max_amp_bin-2:max_amp_bin+3] # 5 points
            coeff = np.polyfit(np.arange(max_amp_bin-2, max_amp_bin+3), peak_data, 2)
            true_peak = -np.real(coeff[1]/(2 * coeff[0]))
            print(f"Coarse peak: {max_amp_bin}, true peak: {true_peak}")

            if int(round(true_peak)) != max_amp_bin:
                note = (true_peak/block_size) * Fs
            else:
                note = (max_amp_bin/block_size) * Fs
            main_notes[i] = note

        data_freq[max_amp_bin-10:max_amp_bin+10] = 0



    return np.array(main_notes)


def callback(indata, outdata, frames, time, status):
    global pos
    global x_dir

    if status:
        print(status)

    if indata.shape[0] == 0:
        return

    outdata[:] = indata
    main_notes = detect_main_notes(np.clip(indata[:, 0] * hann_window, -1, 1))
    main_notes *= freq_upscale_factor
    print(f"Main freq: {main_notes}")


    if np.all(main_notes == 0):
        # Complete silence
        # A rest
        g_code = f"G04 P{int(block_dur * 1000)}\n"
        outdata[:, 0] = 0
        if serial_enable:
            ser.write(bytes(g_code + '\r\n', encoding='utf8'))
        else:
            print(g_code)
        return

    pos, feedrate = get_final_position_for_frequencies(pos, main_notes, move_dir)
    update_move_dir(pos)

    g_code = f"G1 X{pos[0]} Y{pos[1]} Z{pos[2]} F{feedrate * 60} E0"
    if serial_enable:
        ser.write(bytes(g_code + '\r\n', encoding='utf8'))
    else:
        print(g_code)


if serial_enable:
    com = "COM5"  # Change this to the COM port identified in Pronterface
    ser = serial.Serial(
        port=com,
        baudrate=250000,
    )
    time.sleep(1)
    ser.write(bytes('G1 X0 Y0 Z0 F1000' + '\r\n', encoding='utf8'))
    time.sleep(1)
    ser.write(bytes('G1 X10 Y0 Z0 F1000' + '\r\n', encoding='utf8'))
    time.sleep(1)
    ser.write(bytes('G1 X0 Y0 Z0 F1000' + '\r\n', encoding='utf8'))
    time.sleep(1)


if serial_enable:
    """
    for command in get_setup_gcode():
        ser.write(command)
        ser.write(b'\r\n')
    """
    ser.write(bytes(f"M92 X{machine_pp_unit} Y{machine_pp_unit} Z{machine_pp_unit}\r\n", encoding="utf8"))
    time.sleep(0.1)

with sd.Stream(samplerate=Fs, blocksize=block_size, latency="low", channels=1, callback=callback) as S:
    sd.sleep(int(duration * 1000))

time.sleep(1)
ser.write(bytes('G1 X0 Y0 Z0 F1000' + '\r\n', encoding='utf8'))
time.sleep(1)

ser.close()  # Close serial connection
print('done')


