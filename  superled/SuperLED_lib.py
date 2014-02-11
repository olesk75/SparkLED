__author__ = 'olesk'

import SuperLED_globals as glob
import curses
import sys
import threading
from PIL import Image
import colorsys






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
	while True:
		if type(glob.led_buffer[0][0]) is not int: glob.transmit_flag = 0     # We skip if the glob.led_buffer is not ready yet
		if glob.transmit_flag:
			glob.transmit_flag = 0   # Make sure we don't end up sending several times on top of eachother
								# Means we must actively set glob.transmit_flag = 1 in outside code


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
	if glob.OFFLINE: return()

	glob.transmit_flag = 0   # We need to make sure we don't mess with the normal screen update

	if ser.write(b'Z') != 1:
		print("- Zero code 'G' failed in Blank()")
		sys.exit("Unable to send go code to Arduino in Blank()")

	response = ser.read(size=1)

	if response == b'A':
		print("Arduino >> Zero code acknowledged!")
	else:
		print("- Zero code NOT acknowledged by Arduino in Blank() - aborting...")
		sys.exit()


def rgb_adjust_brightness(rgb_values, bright_change):
	"""
	Adjusts "lightness" of r,g,b values
	@param rgb_values: list of [r, g, b]
	@param bright_change: change in brightness (-1 .. +1)
	@return: rgb_values: list of [r, g, b]
	"""
	hls_values = list(colorsys.rgb_to_hls(rgb_values[0] / 255, rgb_values[1] / 255, rgb_values[2] / 255))

	hls_values[1] = hls_values[1] + bright_change * hls_values[1]
	if hls_values[1] > 1: hls_values[1] = 1
	if hls_values[1] < 0: hls_values[1] = 0

	rgb_values = list(colorsys.hls_to_rgb(hls_values[0], hls_values[1], hls_values[2]))
	rgb_values = [int(x * 255) for x in rgb_values]            # Converting from 0-1 (float) to 0-255 (int)
	return rgb_values


def rgb_set_brightness(rgb_values, brightness):
	"""
	Adjusts "lightness" of r,g,b values
	@param rgb_values: list of [r, g, b]
	@param brightness: brightness (0-1)
	@return: rgb_values: list of [r, g, b]
	"""
	hls_values = list(colorsys.rgb_to_hls(rgb_values[0] / 255, rgb_values[1] / 255, rgb_values[2] / 255))

	hls_values[1] = brightness

	rgb_values = list(colorsys.hls_to_rgb(hls_values[0], hls_values[1], hls_values[2]))
	rgb_values = [int(x * 255) for x in rgb_values]            # Converting from 0-1 (float) to 0-255 (int)
	return rgb_values


def rgb_get_brightness(rgb_values):
	hls_values = list(colorsys.rgb_to_hls(rgb_values[0] / 255, rgb_values[1] / 255, rgb_values[2] / 255))
	return hls_values[1]


def anti_alias_left_10(buffer, original_buffer, current_step):      # TODO: Convert to LVS and average, to make it work on non-monochrome
		"""
		Takes one full screen of pixels and scroll them one pixel left with steps using anti-aliasing. Local variables only. No screen updates, only returns buffer.
		@param original_buffer: the screen buffer, unchanged by this function
		@param buffer: the screen buffer (normally display_buffer passed as argument)
		@param current_step: number og intermediate steps to take between pixel fully on and pixel fully off or vice versa
		@return: the updated screen buffer
		"""
		black = [0,0,0]                             # Setting the black pixel color
		color = [None, None, None]

		for pixel in original_buffer:
			if pixel != [0,0,0]: color = pixel		# Finding the monochrome pixel color

		if color == [None, None, None]: return buffer   # If the whole screen is black, we got nothing to do

		bright = rgb_get_brightness(color)          # Finding the color's default brightness value

		#	1)	For each real scrolled pixel we scroll 10 "virtual" pixels (between the real pixels)
		#	2)	We do this by a range(10) loop where we reduce brightness of the original pixel 10% each time IF AND ONLY IF the pixel to the right is black (we work monochrome here). Else skip to 3)
		#	3)	Similarly we in the same loop increase the brightness of the pixel to the left by 10% (same color)
		#	4)	After 10 iterations we have a fully saturated pixel on the left of our original pixel (and black pixel to the right if the real pixel to the right was black) and we exit loop to start
		# 		over again after real pixels have been scrolled one position left

		# TODO: Fix the fact that thereis little *visible* difference between the highest brightness value (non-linear relationship)

		change = float((current_step + 1) / 10)

		for col in range(15):           # We go line by line - making a single step for all pixels
			for row in range(16):       # We iterate over each pixel in the visible_line except the last one (it doesn't have anything to the right)
				cur_pixel = row * 16 + col

				if original_buffer[cur_pixel + 1] == color and original_buffer[cur_pixel] == black:     # Pixel to the right is ON, and the current isn't --> [[0,0,0], [125,50,0]]
					buffer[cur_pixel] = rgb_set_brightness(color, bright * change)						# We migrate ON pixel from the right onto this one (if it's already lit -> no change)

				if original_buffer[cur_pixel + 1] == black and original_buffer[cur_pixel] == color:		# Pixel to the right is OFF, and the current isn't  --> [[125,50,0], [0,0,0]]
					buffer[cur_pixel] = rgb_set_brightness(color, bright * (1 - change))				# We migrate OFF pixel from the right onto this one (if it's already lit -> no change)

		return buffer



def get_line(x1, y1, x2, y2):
	"""
	Bresenham's Line Algorithm
	@param x1: x1
	@param y1: y1
	@param x2: x2
	@param y2: y2
	@return: points list
	"""
	points = []
	is_steep = abs(y2 - y1) > abs(x2 - x1)
	if is_steep:
		x1, y1 = y1, x1
		x2, y2 = y2, x2
	rev = False
	if x1 > x2:
		x1, x2 = x2, x1
		y1, y2 = y2, y1
		rev = True
	delta_x = x2 - x1
	delta_y = abs(y2 - y1)
	error = int(delta_x / 2)
	y = y1
	y_step = None
	if y1 < y2:
		y_step = 1
	else:
		y_step = -1
	for x in range(x1, x2 + 1):
		if is_steep:
			points.append((y, x))
		else:
			points.append((x, y))
		error -= delta_y
		if error < 0:
			y += y_step
			error += delta_x
	# Reverse the list if the coordinates were reversed
	if rev:
		points.reverse()
	return points


def draw_line(x1, y1, x2, y2):
	for coordinate in get_line(x1,y1,x2,y2):
		put_pixel(coordinate[0], coordinate[1], [255,0,0])


def put_pixel(x, y, color):
	"""
	put_pixel injects a single pixel into the display_buffer
	@param x: x coordinate (0-15)
	@param y: y coordinate (0-15)
	@param color: list [r, g, b]
	"""
	glob.led_buffer[x + y * 16] = color
