# In Python 3.x the strings are unicode by default. When sending data to Arduino, they have to be converted to bytes.
# This can be done by prefixing the string with b:

# Things to keep in mind.

# Termonology:
# rgb_buffer	: Arduino compatible buffer with 3 bytes per LED, 768 bytes in total ( 16 * 16 * 3)
# led_buffer : the final 768 elemnt list we send to the arduino
# transmit_flag : flag that indicates if the transmit thread can send the screen_buffer to the Arduino or if it should wait


import serial
from time import sleep
import sys
import signal
import threading
from SuperLED_lib import *
import SuperLED_data
from datetime import datetime
import copy                     # Helps copying two-dimensional lists (deepcopy)


# Global variable definitions
serial_port = '/dev/tty.usbmodem411'
baud_rate = 400000                  # We get about 1B per 10baud, so with 500'000 we get about 50'000B/sec, which is a theoretical frame rate of 65 frames per second
NUM_LEDS = 256
transmit_flag = 0
abort_flag = 0

led_buffer = [None] * 256           # The list of bytes to be sent to curses or Arduino
for i in range(256):
	led_buffer[i] = [None] * 3      # 256 x 3 list

transmit_buffer = [None] * 256      # We need this copy of the led_buffer to avoid overwriting while we do effects and prepare to transmit the data
for i in range(256):
	transmit_buffer[i] = [None] * 3

line_buffer = [None] * 16           # Single line of LEDs to be used for reversing before sending
for i in range(16):
	line_buffer[i] = [None] * 3      # 256 x 3 list

DEBUG = 1       # Increase verbosity
OFFLINE = 0     # Don't write to serial port

ser = serial.Serial(timeout = None)   # Preparing the global serial object, ser. Also, no timeout will block serial.read until byte read


# noinspection PyUnusedLocal,PyUnusedLocal,PyShadowingNames
def signal_handler(signal, frame):
		print('Interrupted manually, aborting')
		if not OFFLINE: ser.close()
		if OFFLINE: curses.endwin()
		sys.exit(0)


def init_thread(thread_function):
	t = threading.Thread(target=thread_function)
	t.daemon = True  # thread dies when main thread (only non-daemon thread) exits.
	t.start()


def transmit_loop(): # TODO: Implement timer that checks for minimum intervall between transmissons
	global transmit_flag
	global led_buffer

	while True:
		if type(led_buffer[0][0]) is not int: transmit_flag = 0     # We skip if the led_buffer is not ready yet
		if transmit_flag:
			transmit_flag = 0   # Make sure we don't end up sending several times on top of eachother
								# Means we must actively set transmit_flag = 1 in outside code
			draw_screen()


def initialize():
	"""
	Initializes serial connection based on global variable to keep config in one place

	"""
	global ser
	global serial_port
	global baud_rate

	if OFFLINE: return()

	print("- Initializing at", baud_rate, " baud on ", serial_port)

	ser = serial.Serial(serial_port, baud_rate,timeout=1)    # This will cause the Arduino to reset. We need to give it two seconds
	sleep(2)    # Arduino really needs at least this before being able to receive
	response = b''
	while response != b'S':
		response = ser.read(size=1)
	#print (str(response), end="")

	# Ok, we got 'S' and are ready to start
	print("- Start code 'S' received from Arduino - ready!")

	if ser.write(b'G') == 1:
		print("- Go code 'G' sent successfully")
	else:
		print("- Go code 'G' failed")
		ser.close()
		sys.exit("Unable to send go code to Arduino")

	response = ser.read(size=1)
	if response != '':
		if response == b'A':
			print("- Go code acknowledged by Arduino - ready to rumble!")
		else:
			print("- Go code NOT acknowledged by Arduino - aborting...")
			ser.close()
			sys.exit()

	print("--- INITIALIZATION COMPLETE ---\n")


def blank():    # TODO: Rewrite to use same drawing functionality as other functions (don't send serial, update display_buffer instead
	global ser

	if OFFLINE: return()

	if ser.write(b'G') != 1:
		print("- Go code 'G' failed")
		sys.exit("Unable to send go code to Arduino")


	response = ser.read(size=1)

	if response == b'A':
		print("Arduino: ack!")
	else:
		print("- Go code NOT acknowledged by Arduino - aborting...")
		sys.exit()

	print("- Blanking screen - Sending 256 * 3 bytes of zero")

	ser.write(b'\x05' * NUM_LEDS * 3)

	response = ser.read(size=1)
	if response == b'R':
		print("Arduino: received!")
	if response == b'E':
		print("Arduino: ERROR - aborting...")
		sys.exit()


# noinspection PyShadowingNames,PyShadowingNames
def draw_screen():
	if OFFLINE:
		curses_draw(effects())
	else:

		if ser.write(b'G') != 1:
			print("- Go code 'G' failed")
			sys.exit("Unable to send go code to Arduino")

		response = ser.read(size=1)
		if response == b'A':
			pass
			#print("Arduino: buffer read command received!")
		else:
			print("- Go code NOT acknowledged by Arduino - aborting...")
			sys.exit()

		ser.write(effects())    # <--- there she goes, notice that even without active effect, we need this to compensate for zigzag LED display

		response = ser.read(size=1)
		#if response == b'R':
		#	print("Arduino: full buffer received!")
		if response == b'E':
			print("Arduino: ERROR - aborting...")
			sys.exit()


def scroller(scroll_text, red, green, blue, speed):
	global NUM_LEDS
	global transmit_flag
	global abort_flag
	global led_buffer

	font = SuperLED_data.font1

	# We "cheat" by adding a padding space at the beginning and end, which will allow us to smoothly scroll the last letter off the screen
	# with a 16x16 font and the first onto the screen
	scroll_text = " " + scroll_text + " "

	# We now build a large array of our text
	letter_counter = 0

	# We use 16 (one for each line) bytearrays to store the letter, and add new ones at the end
	msg_buffer = [bytearray()] * 16     # List of 16 bytearrays

	for letter in scroll_text:  # Letter loop
		font_index = (ord(letter) - 32) * 32    # ASCII - 32 is start of our fonts, and each font is 32 bytes (256 bits/monochrome pixels)
		text_buffer = font[font_index:(font_index + 32)]

		for line in range(16):    # Line loop
			msg_buffer[line] = msg_buffer[line] + text_buffer[line * 2: (line * 2) + 2]

		letter_counter += 1


	# msg_buffer is a LIST of bytearrays, each of 2 bytes

	display_buffer = []

	for msg_line in msg_buffer: # Each element in the msg_buffer is a bytearray line
		pixel_counter = 0
		for pixel in msg_line:
		# First we split each byte of pixels into separate pixels and adds a 1 or 0 three times (since we later will add 3 colors to each LED)
			for bin_pos in range(8):
				first = pixel >> 7 - bin_pos
				first &= 1
				display_buffer.append([first] * 3)    # 1 or 0 is added 3 times to make it easier to add colors later


	# display_buffer is a list of lists, each inner list consisting of 3 ints, each of these 1 or 0
	# We can now multiply all the inner lists with the right color values

	for led in display_buffer:
		led[0] *= red
		led[1] *= green
		led[2] *= blue


	values_per_line = len(display_buffer) / 16  # The number og LED value COLUMNS  we have to display, which must finally be compied to the led_buffer


	while not abort_flag:   # Runs until abort_flag gets set

		cutoff = values_per_line - 16  # how much we need to skip from each line to make the data fit into screen buffer TODO: PROBLEM? 15?

		transmit_flag = 0   # Disabling transmission of data while updating led_buffer

		for scroll_offset in range(len(scroll_text) * 16 - 16):
			for line in range(16):

				visible_start = int(line * (16 + cutoff)) + scroll_offset      # Start (in the display_buffer) of the visible line
				visible_end = int(line * (16 + cutoff) + 16) + scroll_offset   # End (in the display_buffer) of the visible line

				visible_line = display_buffer[visible_start: visible_end]

				#print("Visible line", visible_line)


				for rgb in range(16):
					led_buffer[line * 16 + rgb] = visible_line[rgb]

			transmit_flag = 1   # Ready to transmit through thread

			sleep(0.2  - 0.19 * (speed / 10))


# noinspection PyUnresolvedReferences
def effects():
	global led_buffer
	global transmit_buffer
	global line_buffer

	transmit_buffer = copy.deepcopy(led_buffer) # Required, otherwise led_buffer can get modified by other thread while we're working here

	"""
		Due to the LEDs on this particular display being in a zigzag pattern, we need to reverse the orientation of
		every second line. 1,3,5,7,9,11,13,15 to be precise. But *without* reversing the byte values.
	"""

	for line in range(1,16,2):  # Every second line from 1 to and including 15
		for led in range(16-1, -1, -1):
			line_buffer[15 - led] = transmit_buffer[line * 16 + led]

		transmit_buffer[line * 16:line * 16 + 16] = line_buffer[0:16]



	# if effects.active_effect == 'down' and effects.progress < 16:
	# 	for n in range(effects.progress):
	# 		#transmit_buffer[(15-n) * 16 : ]
	# 		pass
	#
	#
	# if effects.active_effect == 'up' and effects.progress < 16:
	# 	for n in range(effects.progress):
	# 		buffer = buffer[16 * 3:] + bytes([0] * 16 * 3)

	if effects.progress == 32:
		effects.progress = 0    # We're done, making ready for another run/effect
		effects.active_effect = 'none'
	else: effects.progress += 1

	#
	# Finally, we convert the whole transmit_buffer list into a string of bytes that we can write to curses/Arduino
	#
	buffer = bytearray()

	for rgb in transmit_buffer:          # For each led... 256 in total
		buffer.append(rgb[0])
		buffer.append(rgb[1])
		buffer.append(rgb[2])

	return buffer


def tester():   # Simple tester to verify that led_buffer[][] translate correctly to LEDs on the dislay
	global transmit_flag
	global led_buffer

	# First we zero out the whole display buffer
	for led in led_buffer:
		led[0] = int(0)
		led[1] = int(0)
		led[2] = int(0)
	transmit_flag = 1
	time.sleep(2)


	while True:
		for row in range(16):     # Going row by row
			#print("Row:", row)
			for col in range(16):  # Going column by column

				led_buffer[row * 16 + col] = [0, int(col * 16), 0]

				#print("Col:", col)
				#print("Value:", col * 16)
				transmit_flag = 1
				#time.sleep(0.1)
		time.sleep(2)
		for led in led_buffer:
			led[0] = int(0)
			led[1] = int(0)
			led[2] = int(0)
		blank()
		time.sleep(2)

def clock():
	font_tiny = SuperLED_data.font3x5
	n = [None] * 10           # The list of bytes to be sent to curses or Arduino
	for i in range(10):
		n[i] = [None] * 5      # 10 x 5 list

	for j in range(10):
		n[j] = font_tiny[j * 5: j * 5 + 5]

	# Got all the numbers in their respective lists - must find time

	date_time = datetime.today()
	date_time = date_time.timetuple()
	print(date_time[0])
	print(date_time[1])
	print(date_time[2])
	print(date_time[3])


	return

"""
	Main code block
"""

signal.signal(signal.SIGINT, signal_handler)    # Setting up th signal handler
effects.active_effect = 'none'          # Static variable that contains the active effect - stays between funtion calls
effects.progress = 0                    # Static variable that measures the progress of the active effect - stays between funtion calls

initialize()                            # Setting up serial connection if not OFFLINE
blank()                                 # Blanks the LED display if not OFFLINE
init_thread(transmit_loop)              # Starts main transmit thread - to LED if not OFFLINE, curses otherwise

#effects.active_effect = 'down'         # Sets the currently active effect

#tester()

scroller("Amelie rocks!", 10, 10, 10, 5)   # This runs until abort_flag is set

#clock()


print("\n####################################\nAt END - shouldn't be here ... ever!")
while 1: pass   # We only exit via signal
