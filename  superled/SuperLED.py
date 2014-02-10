# In Python 3.x the strings are unicode by default. When sending data to Arduino, they have to be converted to bytes.
# This can be done by prefixing the string with b:

# Things to keep in mind.

# Termonology:
# rgb_buffer	: Arduino compatible buffer with 3 bytes per LED, 768 bytes in total ( 16 * 16 * 3)
# led_buffer : the final 768 elemnt list we send to the arduino
# transmit_flag : flag that indicates if the transmit thread can send the screen_buffer to the Arduino or if it should wait

from SuperLED_lib import *

import serial
from time import sleep
import signal
from datetime import datetime
from copy import deepcopy


# Global variable definitions
serial_port = '/dev/tty.usbmodem411'
baud_rate   = 400000                  # We get about 1B per 10baud, so with 500'000 we get about 50'000B/sec, which is a theoretical frame rate of 65 frames per second
NUM_LEDS    = 256

DEBUG = 1       # Increase verbosity
OFFLINE = 0     # Don't write to serial port


# noinspection PyUnusedLocal,PyUnusedLocal,PyShadowingNames
def signal_handler(signal, frame):
	global ser
	import sys
	print('- Interrupted manually, aborting')
	blank(ser)
	if not OFFLINE: ser.close()
	if OFFLINE: curses.endwin()
	sys.exit(0)


def transmit_loop(): # TODO: Implement timer that checks for minimum intervall between transmissons
	"""
	The main LED update loop that runs perpetually.
	"""
	global transmit_flag

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

	if OFFLINE: return()

	print("- Initializing at", baud_rate, " baud on ", serial_port)

	try:
		ser = serial.Serial(serial_port, baud_rate,timeout=1)    # This will cause the Arduino to reset. We need to give it two seconds
	except:
		print("ERROR: Opening of serial port ", serial_port, "at", baud_rate, "baud failed, aborting...")
		exit(-1)

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
		if DEBUG:
			print("Display updates:\033[1m", draw_screen.updates, "\033[0m", end='\r')
			draw_screen.updates += 1

		response = ser.read(size=1)

		if response == b'E':
			print("Arduino: ERROR - aborting...")
			sys.exit()


def text_to_buffer(display_text, red, green, blue):     # TODO: We need to reduce space between letters
	"""
	Creates a buffer (in display_buffer) that contains the full text
	@rtype : length of text string (letters)
	@param display_text: The text we will put in the display_buffer (which can be of arbitrary size, unlike the led_buffer (which is always 16*16*3)
	@param red: red value (0-255)
	@param green: green value (0-255)
	@param blue: blue value (0-255)
	"""
	global display_buffer		# Global since we update it

	font = SuperLED_data.font1

	# We "cheat" by adding a padding space at the beginning and end, which will allow us to smoothly scroll the last letter off the screen
	# with a 16x16 font and the first onto the screen
	display_text = " " + display_text + " "

	# We now build a large array of our text
	letter_counter = 0

	# We use 16 (one for each line) bytearrays to store the letter, and add new ones at the end
	msg_buffer = [bytearray()] * 16     # List of 16 bytearrays

	for letter in display_text:  # Letter loop
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

	return len(display_text)


def scroll_display_buffer(string_length, speed, aa = True):
	"""
	Scrolls whatever is in display_buffer left until interrupted by a True abort_flag
	NOTE: Only works for single color with anti-aliasing
	@param string_length: number of number of full 16x16 blocks (normally characters)
	@param speed: scroll speed (1 - 10)
	@param aa: anti-alias intermediate steps (True / False)
	"""
	global led_buffer
	global transmit_flag

	values_per_line = len(display_buffer) / 16  # The number og LED value COLUMNS  we have to display, which must finally be compied to the led_buffer
	while not abort_flag:   # Runs until abort_flag gets set

		cutoff = values_per_line - 16  # how much we need to skip from each line to make the data fit into screen buffer


		for scroll_offset in range(string_length * 16 - 16):
			for line in range(16):

				visible_start = int(line * (16 + cutoff)) + scroll_offset      # Start (in the display_buffer) of the visible line
				visible_end = int(line * (16 + cutoff) + 16) + scroll_offset   # End (in the display_buffer) of the visible line
				visible_line = display_buffer[visible_start: visible_end]

				# After each "virtual scroll left" we need to update the screen
				for rgb in range(16):		# We go through one full row at a time
					led_buffer[line * 16 + rgb] = visible_line[rgb]

			# Display has now been moved one step to the left, and we are ready to display
			transmit_flag = 1

			if aa:
				led_buffer_original = led_buffer[:]     # We need to pass the unchanged buffer as well
				for anti_alias_step in range(10):       # We now anti-alias scroll everything one pixel to the left to make it smooth, in 10 steps
					led_buffer = anti_alias_left_10(led_buffer, led_buffer_original, anti_alias_step)

					transmit_flag = 1   # We send the intermediate step to the screen

					sleep(0.01)          # TODO: link to speed argument

			# The led_buffer is now scrolled one step to the left - we then repeat the loop
			# This replaces the anti-alias scrolled buffer with the "real" one, which is identical except it also adds a new column to the right
			# from the display_buffer (where we keep our text / graphics)

			if not aa: sleep(0.1)      # TODO: Link to speed argument
	return




def clock(): # WIP
	font_tiny = SuperLED_data.font3x5
	n = [None] * 10           # The list of bytes to be sent to curses or Arduino
	num = [None] * 10
	for i in range(10 + 1):
		num[i] = [None] * 3      # 10 x 3 list

	for j in range(11):
		n[j] = font_tiny[j * 5: j * 5 + 5]

		# n[0..10] now has the
		print (n[j])

		for bin_pos in range(8):
			first = pixel >> 7 - bin_pos
			first &= 1
			display_buffer.append([first] * 3)    # 1 or 0 is added 3 times to make it easier to add colors later

	# Got all the numbers in their respective lists - must find time

	date_time = datetime.today()
	date_time = date_time.timetuple()
	print(date_time[0])
	print(date_time[1])
	print(date_time[2])
	print(date_time[3])

	return
# noinspection PyUnresolvedReferences


def effects():
	"""
	Adds fancy effects and is responsible to compensating for the display's zigzag pattern of LEDs
	@param led_buffer: the full RGB led buffer
	@return: updated RGB led buffer ready to transmit
	"""
	transmit_buffer = deepcopy(led_buffer) # Required, otherwise led_buffer can get modified by other thread while we're working here

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


def show_img(image, led_buffer):
	try:
		img = Image.open(image)
	except:
		sys.exit("Unable to load image")

	if not (img.size[0] == img.size[1] == 16):
		sys.exit("ERROR: Only accept 16x16 images")


	if img.mode in ('RGBA', 'LA'):		# Image has alpha channel - which we merge with black
		if DEBUG: print("Image", img, "had alpha layer - converted to black")
		img = pure_pil_alpha_to_color_v2(img, color=(0, 0, 0))

	pixels = list(img.getdata())

	print(pixels)

	rgb_pixels = []

	for pixel in pixels:
		rgb_pixels.append(list(pixel))

	print(len(rgb_pixels))

	led_buffer = rgb_pixels

	transmit_flag = 1

	return


def ext_effect(effect, effect_value = None):
	global transmit_flag
	transmit_flag = 0

	if effect == 'brightness': hw_effect = b'B'
	if effect == 'hw_test': hw_effect = b'T'

	if DEBUG: print("\n---> Changing", effect, "to", effect_value, "!")

	if effect_value:
		value = bytes([effect_value])

	if not OFFLINE:

		if ser.write(hw_effect) != 1:
			print("- Sending of effect code,", hw_effect, "failed")
			sys.exit()

		response = ser.read(size=1)
		if response == b'A':
			if DEBUG: print("Arduino >>", effect, "command acknowledged!")
		else:
			print("- Effect code", effect, " (code: '", hw_effect, ") NOT acknowledged by Arduino - aborting...")
			sys.exit()

		if effect_value:    # Could be None
			# Ok, initial handshake and command is fine, let's send the value
			if ser.write(value) == -1:
					print("- Unable to send '", effect, "' value", value, "to Arduino")
					sys.exit()

			response = ser.read(size=1)
			if response == b'A':    # Value acknowledged
				if DEBUG: print("Arduino >>", effect, "value acknowledged!")
			if response == b'E':    # Error reported by Arduino
					print("Arduino >> ERROR: value not received")
					sys.exit()
			if response == -1:      # Unable to send value to Arduino
				print("ERROR: Nothing read from Arduino")
				sys.exit()

		# Since some of these effects can take some time, we wait here until we get 'D'one from the Arduino
		waiting = True
		while waiting:
			if ser.read(size=1) == b'D': waiting = False

		print("Arduino >> Effect completed successfully")




"""
	Main code block
"""
if __name__ == "__main__":  # Making sure we don't have problems if importing from this file as a module


	signal.signal(signal.SIGINT, signal_handler)    # Setting up th signal handler
	
	effects.active_effect = 'none'                  # Static variable that contains the active effect - stays between funtion calls
	effects.progress = 0                            # Static variable that measures the progress of the active effect - stays between funtion calls
	draw_screen.updates = 0                         # We need to set this variable AFTER the funtion definition
	abort_flag = 0                                  # True if we want to abort current execution
	
	initialize()                            # Setting up serial connection if not OFFLINE
	#blank(ser)                              # Blanks the LED display if not OFFLINE
	transmit_flag = 0
	init_thread(transmit_loop)              # Starts main transmit thread - to LED if not OFFLINE, curses otherwise

	#effects.active_effect = 'down'         # Sets the currently active effect

	text_length = text_to_buffer("Scrolling is fun!?!", 100, 10, 10)   # This runs until abort_flag is set

	scroll_display_buffer(text_length, 1)

	#clock()

	#show_img('images/clock_ringing.png', led_buffer)
	#show_img('images/bell.png', led_buffer)

	sleep(1)

	#ext_effect('brightness', 64)

	#ext_effect('hw_test')
	#scroller("Scrolling is fun!", 100, 10, 10, 5)
	print("\n####################################\nAt END - shouldn't be here ... ever!")

	#while 1: pass   # We only exit via signal
