# In Python 3.x the strings are unicode by default. When sending data to Arduino, they have to be converted to bytes.
# This can be done by prefixing the string with b:

# Things to keep in mind.

# Termonology:
# rgb_buffer	: Arduino compatible buffer with 3 bytes per LED, 768 bytes in total ( 16 * 16 * 3)
# glob.led_buffer : the final 768 elemnt list we send to the arduino
# glob.transmit_flag : flag that indicates if the transmit thread can send the screen_buffer to the Arduino or if it should wait

from time import sleep
import signal
from datetime import datetime
from copy import deepcopy

import serial

from SuperLED_lib import *
import SuperLED_data


# Global variable definitions
glob.serial_port = '/dev/tty.usbmodem411'
glob.baud_rate = 400000                  # We get about 1B per 10baud, so with 500'000 we get about 50'000B/sec, which is a theoretical frame rate of 65 frames per second
glob.NUM_LEDS = 256

glob.DEBUG = 1       # Increase verbosity
glob.OFFLINE = 0     # Don't write to serial port


# noinspection PyUnusedLocal,PyUnusedLocal,PyShadowingNames
def signal_handler(signal, frame):
	global ser
	import sys
	print('- Interrupted manually, aborting')
	blank()
	if not glob.OFFLINE: ser.close()
	if glob.OFFLINE: curses.endwin()
	sys.exit(0)


def transmit_loop(): # TODO: Implement timer that checks for minimum intervall between transmissons
	"""
	The main LED update loop that runs perpetually.
	"""
	while True:
		if type(glob.led_buffer[0][0]) is not int: glob.transmit_flag = 0     # We skip if the glob.led_buffer is not ready yet

		if glob.transmit_flag:
			glob.transmit_flag = 0   # Make sure we don't end up sending several times on top of eachother
								# Means we must actively set glob.transmit_flag = 1 in outside code
			draw_screen()


def initialize():
	"""
	Initializes serial connection based on global variable to keep config in one place

	"""

	if glob.OFFLINE: return()

	print("- Initializing at", glob.baud_rate, " baud on ", glob.serial_port)

	try:
		glob.ser = serial.Serial(glob.serial_port, glob.baud_rate,timeout=1)    # This will cause the Arduino to reset. We need to give it two seconds
	except:
		print("ERROR: Opening of serial port ", glob.serial_port, "at", glob.baud_rate, "baud failed, aborting...")
		exit(-1)

	sleep(2)    # Arduino really needs at least this before being able to receive
	response = b''
	while response != b'S':
		response = glob.ser.read(size=1)
	#print (str(response), end="")

	# Ok, we got 'S' and are ready to start
	print("- Start code 'S' received from Arduino - ready!")

	if glob.ser.write(b'G') == 1:
		print("- Go code 'G' sent successfully")
	else:
		print("- Go code 'G' failed")
		glob.ser.close()
		sys.exit("Unable to send go code to Arduino")

	response = glob.ser.read(size=1)
	if response != '':
		if response == b'A':
			print("- Go code acknowledged by Arduino - ready to rumble!")
		else:
			print("- Go code NOT acknowledged by Arduino - aborting...")
			glob.ser.close()
			sys.exit()

	print("--- INITIALIZATION COMPLETE ---\n")


# noinspection PyShadowingNames,PyShadowingNames
def draw_screen():
	if glob.OFFLINE:
		curses_draw(effects())
	else:

		if glob.ser.write(b'G') != 1:
			print("- Go code 'G' failed")
			sys.exit("Unable to send go code to Arduino")

		response = glob.ser.read(size=1)
		if response == b'A':
			pass
			#print("Arduino: buffer read command received!")
		else:
			print("- Go code NOT acknowledged by Arduino - aborting...")
			sys.exit()

		glob.ser.write(effects())    # <--- there she goes, notice that even without active effect, we need this to compensate for zigzag LED display
		if glob.DEBUG:
			print("Display updates:\033[1m", draw_screen.updates, "\033[0m", end='\r')
			draw_screen.updates += 1

		response = glob.ser.read(size=1)

		if response == b'E':
			print("Arduino: ERROR - aborting...")
			sys.exit()


def text_to_buffer(display_text, red, green, blue):
	"""
	Creates a buffer (in display_buffer) that contains the full text
	@rtype : length of text string (letters)
	@param display_text: The text we will put in the display_buffer (which can be of arbitrary size, unlike the glob.led_buffer (which is always 16*16*3)
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

	for msg_line in msg_buffer:		# Each element in the msg_buffer is a bytearray line
		for pixel in msg_line:
		# First we split each byte of pixels into separate pixels and adds a 1 or 0 three times (since we later will add 3 colors to each LED)
			for bin_pos in range(8):
				first = pixel >> 7 - bin_pos
				first &= 0x01
				display_buffer.append([first] * 3)    # 1 or 0 is added 3 times to make it easier to add colors later


	# display_buffer is a list of lists, each inner list consisting of 3 ints, each of these 1 or 0

	# We iterate through the display_buffer. We can cheat, as we know each letter in the standard for is 16x16 pixels (with plenty of space on both side).
	# Thus we simply remove the two first and last colums for each letter.
	# TODO: Remove columns here to reduce space between letters

	# We can now multiply all the inner lists with the right color values

	for led in display_buffer:
		led[0] *= red
		led[1] *= green
		led[2] *= blue

	return len(display_text)


def scroll_display_buffer(string_length, speed, aa = True):
	"""
	Scrolls whatever is in display_buffer left until interrupted by a True glob.abort_flag
	NOTE: Only works for single color with anti-aliasing
	@param string_length: number of number of full 16x16 blocks (normally characters)
	@param speed: scroll speed (1 - 10)
	@param aa: anti-alias intermediate steps (True / False)
	"""

	values_per_line = len(display_buffer) / 16  # The number og LED value COLUMNS  we have to display, which must finally be compied to the glob.led_buffer
	while not glob.abort_flag:   # Runs until glob.abort_flag gets set

		cutoff = values_per_line - 16  # how much we need to skip from each line to make the data fit into screen buffer


		for scroll_offset in range(string_length * 16 - 16):
			for line in range(16):

				visible_start = int(line * (16 + cutoff)) + scroll_offset      # Start (in the display_buffer) of the visible line
				visible_end = int(line * (16 + cutoff) + 16) + scroll_offset   # End (in the display_buffer) of the visible line
				visible_line = display_buffer[visible_start: visible_end]

				# After each "virtual scroll left" we need to update the screen
				for rgb in range(16):		# We go through one full row at a time
					glob.led_buffer[line * 16 + rgb] = visible_line[rgb]

			# Display has now been moved one step to the left, and we are ready to display
			glob.transmit_flag = 1

			if aa:
				glob.led_buffer_original = glob.led_buffer[:]     # We need to pass the unchanged buffer as well
				for anti_alias_step in range(10):       # We now anti-alias scroll everything one pixel to the left to make it smooth, in 10 steps
					glob.led_buffer = anti_alias_left_10(glob.led_buffer, glob.led_buffer_original, anti_alias_step)

					glob.transmit_flag = 1   # We send the intermediate step to the screen

					sleep(0.01)          # TODO: link to speed argument

			# The glob.led_buffer is now scrolled one step to the left - we then repeat the loop
			# This replaces the anti-alias scrolled buffer with the "real" one, which is identical except it also adds a new column to the right
			# from the display_buffer (where we keep our text / graphics)

			if not aa: sleep(0.1)      # TODO: Link to speed argument
	return


def effects():
	"""
	Adds fancy effects and is responsible to compensating for the display's zigzag pattern of LEDs
	@param glob.led_buffer: the full RGB led buffer
	@return: updated RGB led buffer ready to transmit
	"""
	transmit_buffer = deepcopy(glob.led_buffer) # Required, otherwise glob.led_buffer can get modified by other thread while we're working here

	"""
		Due to the LEDs on this particular display being in a zigzag pattern, we need to reverse the orientation of
		every second line. 1,3,5,7,9,11,13,15 to be precise. But *without* reversing the byte values.
	"""
	if not glob.OFFLINE:
		for line in range(1,16,2):  # Every second line from 1 to and including 15
			for led in range(16 - 1, -1, -1):
				glob.line_buffer[15 - led] = transmit_buffer[line * 16 + led]

			transmit_buffer[line * 16:line * 16 + 16] = glob.line_buffer[0:16]



	# if effects.active_effect == 'down' and effects.progress < 16:
	# 	for n in range(effects.progress):
	# 		#transmit_buffer[(15-n) * 16 : ]
	# 		pass
	#
	#
	# if effects.active_effect == 'up' and effects.progress < 16:
	# 	for n in range(effects.progress):
	# 		buffer = buffer[16 * 3:] + bytes([0] * 16 * 3)

	#if effects.progress == 32:
	#	effects.progress = 0    # We're done, making ready for another run/effect
	#	effects.active_effect = 'none'
	#else: effects.progress += 1

	#
	# Finally, we convert the whole transmit_buffer list into a string of bytes that we can write to curses/Arduino
	#
	buffer = bytearray()


	for rgb in transmit_buffer:          # For each led... 256 in total
		buffer.append(rgb[0])
		buffer.append(rgb[1])
		buffer.append(rgb[2])

	return buffer


def show_img(image, brightness = 128, animate = False):
	"""
	Displays an image (16x16) on the LED display. Will blend with black if alpha. Supports animated images
	@param image: File name (relative or abs path)
	"""
	alpha_channel = bool
	animated = bool
	run = True      # We set this flag to False after first run if there is no animation

	# What we have learned so far:
	# PNG: No problem! 256 tuples of rgb translates easy into led_buffer
	# GIF: First we seek() the first image (even if there is only one), wich gives us a grayscale version of the image,
	#       then we have to perform some magic to get the color in. This because GIFs store their color palette data in a
	#       palette table, with each pixel value a reference to this table. So to get to led_buffer we need to convert this

	try:
		img = Image.open(image)
	except FileNotFoundError:
		sys.exit("Unable to load image - file not found")

	if not (img.size[0] == img.size[1] == 16):
		sys.exit("ERROR: Only accept 16x16 images")

	ext_effect('brightness', brightness)


	if 'duration' in img.info: animated = True



	if img.mode in ('RGBA', 'LA'):		# Image has alpha channel - which we merge with black
		if glob.DEBUG: print("Image", img, "had alpha layer - converted to black")
		img = pure_pil_alpha_to_color_v2(img, color=(0, 0, 0))

	while run:
		if not animated: run = False        # No animation -> only one run
		final_img = img

		if img.format == "GIF":
			final_img = img.convert()     # This adds palette data to GIFs (otherwise monochrome)

		# TODO: img = img.filter(ImageFilter.GaussianBlur(radius=1))

		pixels = list(final_img.getdata())    # Returns single list of 256 rgb tuples



		#if animated: print("Image duration is",  img.info)
			#print("pixels are datatype:", type(pixels), "of", len(pixels), "length, each a", type(pixels[0]),". Content:\n", pixels)

		# We convert the list of RGB tuples into a list of RGB lists
		rgb_pixels = [None] * 256

		for n in range(256):
			rgb_pixels[n] = list(pixels[n])

		glob.led_buffer = rgb_pixels
		glob.transmit_flag = 1

		if animated:
			sleep(img.info['duration'] / 1000)      # Waiting for time stipulated in GIF

			try:
				img.seek(img.tell() + 1)        # Seeking to next frame in animated gif
			except EOFError:        # We've read the last frame
				run = False


def ext_effect(effect, effect_value = None):
	glob.transmit_flag = 0

	if effect == 'brightness': hw_effect = b'B'
	if effect == 'hw_test': hw_effect = b'T'

	if glob.DEBUG: print("\n---> Changing", effect, "to", effect_value, "!")

	if effect_value:
		value = bytes([effect_value])

	if not glob.OFFLINE:

		if glob.ser.write(hw_effect) != 1:
			print("- Sending of effect code,", hw_effect, "failed")
			sys.exit()

		response = glob.ser.read(size=1)

		if response == b'A':
			if glob.DEBUG: print("Arduino >>", effect, "command acknowledged!")
		else:
			print("- Effect code", effect, " (code: '", hw_effect, ") NOT acknowledged by Arduino - aborting...")
			sys.exit()

		if effect_value:    # Could be None
			# Ok, initial handshake and command is fine, let's send the value
			if glob.ser.write(value) == -1:
					print("- Unable to send '", effect, "' value", value, "to Arduino")
					sys.exit()

			response = glob.ser.read(size=1)
			if response == b'A':    # Value acknowledged
				if glob.DEBUG: print("Arduino >>", effect, "value acknowledged!")
			if response == b'E':    # Error reported by Arduino
					print("Arduino >> ERROR: value not received")
					sys.exit()
			if response == -1:      # Unable to send value to Arduino
				print("ERROR: Nothing read from Arduino")
				sys.exit()

		# Since some of these effects can take some time, we wait here until we get 'D'one from the Arduino
		waiting = True
		while waiting:
			if glob.ser.read(size=1) == b'D': waiting = False

		print("Arduino >> Effect completed successfully")


def clock_digital(color):
	"""
	Displays real-time clock on display using tiny 3x5 font
	@param color: font color
	@return:
	"""


	font_tiny = list(SuperLED_data.numfont3x5)
	black = [0,0,0]


	n = [None] * 10
	for j in range(10):
		n[j] = [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],
				[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],
				[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]

	for number in range(10):
		for byte_value in range(5):
				if font_tiny[byte_value + number * 5] & 0b0100:
					n[number][0 + byte_value * 3] = color
				else:
					n[number][0 + byte_value * 3] = black

				if font_tiny[byte_value + number * 5] & 0b0010:
					n[number][1 + byte_value * 3] = color
				else: n[number][1 + byte_value * 3] = black

				if font_tiny[byte_value + number * 5] & 0b0001:
					n[number][2 + byte_value * 3] = color
				else:
					n[number][2 + byte_value * 3] = black


	# TODO: We got all the numbers in place now. Next is placing them on the display.


	# For debugging
	while not glob.abort_flag:

		# Got all the numbers in their respective lists - must find time

		date_time = datetime.today()
		date_time = date_time.timetuple()

		month = list(map(int, str(date_time[1])))
		day	= list(map(int, str(date_time[2])))
		hour =list(map(int, str(date_time[3])))
		minute = list(map(int, str(date_time[4])))

		minute = [8]

		if len(month) == 1: month = [0] + month
		if len(day) == 1: day = [0] + day
		if len(hour) == 1: hour = [0] + hour
		if len(minute) == 1: minute = [0] + minute

		# Screen layout:
		# 	16 x 16: we need 3 leds per number, with 1 led in between each, four numbers across: xxx0 xxx0 0xxx 0xxx - in the double zeron in the middle we have : or / for presentation
		#	Vertically we have 5 lines per number: 3 rows with only one space. Probably better to only do two rows (hh:mm and dd:MM), perhaps with a line between: 0NNN NN0L 0NNN NN00
		# TODO: Anti-aliasing to be considered lates
		glob.transmit_flag = 0 	# To avoid flicker

		# First 5 rows of numbers (hh:mm)
		glob.led_buffer[0:16] = [black] * 16		# First we add one blank line
		offset = 1

		for line in range(offset, 6):
			glob.led_buffer[line * 16 + 0:line * 16 + 3] = n[hour[0]][(line - offset) * 3:(line - offset) * 3 + 3]
			glob.led_buffer[line * 16 + 3] = black
			glob.led_buffer[line * 16 + 4:line * 16 + 7] = n[hour[1]][(line - offset) * 3:(line - offset) * 3 + 3]
			glob.led_buffer[line * 16 + 7] = black

			glob.led_buffer[line * 16 + 8] = black
			glob.led_buffer[line * 16 + 9:line * 16 + 12] = n[minute[0]][(line - offset) * 3:(line - offset) * 3 + 3]
			glob.led_buffer[line * 16 + 12] = black
			glob.led_buffer[line * 16 + 13:line * 16 + 16] = n[minute[1]][(line - offset) * 3:(line - offset) * 3 + 3]

		glob.led_buffer[6 * 16:9 * 16] = [black] * 16 * 3		# Three blank lines

		offset = 9

		for line in range(offset, 14):
			glob.led_buffer[line * 16 + 0:line * 16 + 3] = n[day[0]][(line - offset) * 3:(line - offset) * 3 + 3]
			glob.led_buffer[line * 16 + 3] = black
			glob.led_buffer[line * 16 + 4:line * 16 + 7] = n[day[1]][(line - offset) * 3:(line - offset) * 3 + 3]
			glob.led_buffer[line * 16 + 7] = black

			glob.led_buffer[line * 16 + 8] = black
			glob.led_buffer[line * 16 + 9:line * 16 + 12] = n[month[0]][(line - offset) * 3:(line - offset) * 3 + 3]
			glob.led_buffer[line * 16 + 12] = black
			glob.led_buffer[line * 16 + 13:line * 16 + 16] = n[month[1]][(line - offset) * 3:(line - offset) * 3 + 3]

		glob.led_buffer[16 * 14:16 * 16] = [black] * 16 * 2

		glob.transmit_flag = 1 	# To avoid flicker

		#print(len(glob.led_buffer)/16)
		#print(glob.led_buffer)
		sleep(1)
	return




if __name__ == "__main__":  # Making sure we don't have problems if importing from this file as a module


	signal.signal(signal.SIGINT, signal_handler)    # Setting up th signal handler

	effects.active_effect = 'none'                  # Static variable that contains the active effect - stays between funtion calls
	effects.progress = 0                            # Static variable that measures the progress of the active effect - stays between funtion calls
	draw_screen.updates = 0                         # We need to set this variable AFTER the funtion definition
	glob.abort_flag = 0                                  # True if we want to abort current execution

	initialize()                            # Setting up serial connection if not glob.OFFLINE
	glob.transmit_flag = 0
	init_thread(transmit_loop)              # Starts main transmit thread - to LED if not glob.OFFLINE, curses otherwise

	#effects.active_effect = 'down'         # Sets the currently active effect

	#text_length = text_to_buffer("Scrolling is fun!?!", 100, 10, 10)   # This runs until glob.abort_flag is set
	#scroll_display_buffer(text_length, 1)

	#clock_digital([128,0,0])
	blank()


	#show_img('images/bell.png', 30, False)
	show_img('images/walking.gif', 30, True)
	#show_img('images/bubble.gif', 30, False)
	while True:
		show_img('images/alarm.gif', 30, True)


	#ext_effect('brightness', 64)

	#ext_effect('hw_test')
	#scroller("Scrolling is fun!", 100, 10, 10, 5)
	print("\n####################################\nAt END - shouldn't be here ... ever!")

#	while 1: pass   # We only exit via signal
