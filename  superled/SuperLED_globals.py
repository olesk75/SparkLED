__author__ = 'olesk'

# Global variables
transmit_flag = None
abort_flag = None

ser = None

DISPLAY_MODE = 'LED'		# One of 'curses', 'LED' or 'tkinter' - defaults to 'LED'
OFFLINE = None
DEBUG = False

led_buffer = [''] * 256           # The list of bytes to be sent to curses or Arduino
for i in range(256):
	led_buffer[i] = [0,0,0]       # 256 x 3 list

transmit_buffer = [None] * 256      # We need this copy of the led_buffer to avoid overwriting while we do effects and prepare to transmit the data
for i in range(256):
	transmit_buffer[i] = [None] * 3

line_buffer = [None] * 16           # Single line of LEDs to be used for reversing before sending
for i in range(16):
	line_buffer[i] = [None] * 3      # 256 x 3 list