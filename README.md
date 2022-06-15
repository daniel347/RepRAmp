# RepRAmp

The main goal of this project is to make a 3D printer (or similar device) operate as a guitar amplifier.
Both the guitar and printer are connected to a computer (which could be replaced with a raspberry pi later for portability).
The computer determines the dominant frequencies, and the corresponding stepper motor speeds required generate the same frequency. 
This gets transferred to GCode and sent to the printer via serial in real time.

Another idea (partially implemented in `AddMusicToGCode.py`) was to add music to a 3D print by modifying feed rates in 
the GCode based in notes from a Midi file. This code is partially borrowed/inspired by https://github.com/yeokm1/midi-to-simple-metal-gcode.