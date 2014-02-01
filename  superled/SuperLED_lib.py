__author__ = 'olesk'

import curses
import time

def bin_print(x):

	print("x is:", type (x), "value:",x)
	print()
	#print(int(x))
	#left = x >> 4
	#left &= 0xff       # Masking out all but first 4 bits
	#right = x & 0xff
	#print(left)
	#print(right)

	#print(bytes("{0:08b}".format(x), 'ascii'))

	return bytes("{0:08b}".format(x), 'ascii')


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