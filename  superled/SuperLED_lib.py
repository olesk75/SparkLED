__author__ = 'olesk'

import curses
import sys
import threading
from PIL import Image
import SuperLED_data

from SuperLED_globals import *



def curses_draw(buffer):
	"""
	Draws the 768byte buffer on the console with curses
	This allows off-line testing of functionality without an Arduino handy

	@param buffer: the 16x16*3 byte buffer to display
	"""

	screen = curses.initscr()
	curses.start_color()
	screen.clear()

	# Pre-defined color pairs that we will use
	curses.init_pair(1, curses.COLOR_RED, curses.COLOR_RED)   # Default color pair, the first is ignored
	curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_GREEN)   # Default color pair, the first is ignored
	curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLUE)   # Default color pair, the first is ignored
	curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_BLACK)   # Default color pair, the first is ignored
	curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_WHITE)   # Default color pair, the first is ignored

	for line in range(16):
		for row in range(16):
			# We have to cheat, with only 8 colors in curses we only use red/green/blue,
			# depending on which color in the byte triplet that has the highest value
			# If all the same, we do white, unless all zero, tahen we do black
			red = buffer[line * 16 *3 + row * 3]
			green = buffer[line * 16 *3 + row * 3 + 1]
			blue = buffer[line * 16 *3 + row * 3 + 2]

			#print('Got:', red, green, blue,'-')
			if red > green and red > blue: bytecolor = 1
			if green > red and green > blue: bytecolor = 2
			if blue > green and blue > red: bytecolor = 3

			if red == green == blue == 0: bytecolor = 4
			if red == green == blue: bytecolor = 5


			# IMPORTANT: The curses lib uses (y,x) coordinate system  (yeah, I know!)
			screen.addstr(line, row, " ", curses.color_pair(bytecolor))

	screen.refresh()
	#time.sleep(0.1)

	return





def init_thread(thread_function):
	t = threading.Thread(target=thread_function)
	t.daemon = True  # thread dies when main thread (only non-daemon thread) exits.
	t.start()


def transmit_loop(): # TODO: Implement timer that checks for minimum intervall between transmissons
	"""
	The main LED update loop that runs perpetually.
	"""
	#global transmit_flag
	#global led_buffer

	while True:
		if type(led_buffer[0][0]) is not int: transmit_flag = 0     # We skip if the led_buffer is not ready yet
		if transmit_flag:
			transmit_flag = 0   # Make sure we don't end up sending several times on top of eachother
								# Means we must actively set transmit_flag = 1 in outside code
			draw_screen()


def pure_pil_alpha_to_color_v2(image, color=(255, 255, 255)):
	"""Alpha composite an RGBA Image with a specified color.

	Simpler, faster version than the solutions above.

	Source: http://stackoverflow.com/a/9459208/284318

	Keyword Arguments:
	image -- PIL RGBA Image object
	color -- Tuple r, g, b (default 255, 255, 255)

	"""
	image.load()  # needed for split()
	background = Image.new('RGB', image.size, color)
	background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
	return background

def blank(ser):
	"""
	Blanks the LED display by sending a zero ('Z') code to the Arduino
	@param ser: serial link
	"""
	global transmit_flag

	if OFFLINE: return()

	transmit_flag = 0   # We need to make sure we don't mess with the normal screen update

	if ser.write(b'Z') != 1:
		print("- Zero code 'G' failed in Blank()")
		sys.exit("Unable to send go code to Arduino in Blank()")

	response = ser.read(size=1)

	if response == b'A':
		print("Arduino >> Zero code acknowledged!")
	else:
		print("- Zero code NOT acknowledged by Arduino in Blank() - aborting...")
		sys.exit()
