#!/usr/bin/env python3
""" Python3 program to connect to an SparkCore (server) connected to a LED display via a network socket.
        The program can either issue command for the SparkCore (change brightness, blank screen etc),
        or issue full screen updates (R,G,B values for all LEDs on display).

        The program will in its final form use input from sensors (networked and directly attached) to
        generate messages on the LED (doorbell, temperature sensors, clock, sound etc.).

        All supporting functions can be found in and are imported from SparkLED.lib
        Some additional global variables are found in and imported from SparkLED_globals.py
        The font and image data are store in and imported from SparkLED_data.py
"""
__author__ = 'Ole Jakob Skjelten'

from config import *  # This is the config file with your Spark Core variables, DEVICEID and ACCESS_TOKEN
from spyrk import SparkCloud

import signal
import sys
from datetime import datetime
import socket
from time import sleep
import requests
from SparkLED_lib import *
import SparkLED_data

# Global variable definitions
glob.NUM_LEDS = 256
glob.DEBUG = 1  # Increase verbosity


def initialize():
	"""
    Initializes network connection and returns socket object
    @rtype : Server object
    @param ip_address: IP address of Spark Core
    @param port_number: Port number of server running on Spark Core
    """

	# spark = SparkCloud(ACCESS_TOKEN)

	#serverIP = spark.devices[DEVICEID].localIP

	#print(serverIP)


	serverIP = "10.0.0.69"  # TODO: Make call  curl "https://api.spark.io/v1/devices/ DEVICEID /localIP?access_token= ACCESS_TOKEN"
	# For use with emulator only:
	#serverIP = "127.0.0.1"

	SparkCore = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	SparkCore.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
	                     1)  # Important in Windows to not block sockets (at least it is on a TCP server, not sure about client)

	print("- Contacting Spark Core server at", serverIP, "on port", glob.PORT)
	try:
		SparkCore.settimeout(10)
		SparkCore.connect((serverIP, glob.PORT))
	except socket.error as error:
		print("ERROR: Connect failed:", format(error))
		exit(1)
	print("- Connected to Spark Core server successfully")

	SparkCore.settimeout(5)  # No reason why it should take anywhere near even a second once connection is established

	glob.connected = True
	SparkCore.sendall(b'\x00' + b'K')  # This will initialize connection if first connect,
	# Will otherwise be treated as normal keepalive by core,
	# in case this program crashes and reconnects to a
	# normally running PI

	try:
		while True:
			if SparkCore.recv(1) == b'A': break  # We're stuck here until the SparkCore sends us the ack
	except socket.error as error:
		print("ERROR: Connect failed:", format(error))
		exit(1)

	print("- Acknowledgement (b'A') received from SparkCore - ready!")
	print("--- INITIALIZATION COMPLETE ---\n")

	return SparkCore


def scroll_display_buffer(string_length, speed, display_buffer, aa=True):
	"""
    Scrolls whatever is in display_buffer left until interrupted by a True glob.abort_flag
    NOTE: Only works for single color with anti-aliasing
    @param string_length: number of number of full 16x16 blocks (normally characters)
    @param speed: scroll speed (1 - 10)
    @param aa: anti-alias intermediate steps (True / False)
    """

	if speed < 1 or speed > 10:  # Sanity checking speed argument
		print("= Error: scroll speed must be an integer from 1 to 10")
		exit(1)

	speed = (11 - speed) * 2 / 100

	values_per_line = len(
		display_buffer) / 16  # The number og LED value COLUMNS  we have to display, which must finally be copied to the glob.led_buffer
	while not glob.abort_flag:  # Runs until glob.abort_flag gets set

		cutoff = values_per_line - 16  # how much we need to skip from each line to make the data fit into screen buffer

		for scroll_offset in range(string_length * 16 - 16):
			for line in range(16):
				visible_start = int(
					line * (16 + cutoff)) + scroll_offset  # Start (in the display_buffer) of the visible line
				visible_end = int(
					line * (16 + cutoff) + 16) + scroll_offset  # End (in the display_buffer) of the visible line
				visible_line = display_buffer[visible_start: visible_end]

				# After each "virtual scroll left" we need to update the screen
				# for rgb in range(16):          # We go through one full row at a time
				glob.led_buffer[line * 16: line * 16 + 16] = visible_line[:16]

			# Display has now been moved one step to the left, and we are ready to display
			glob.transmit_flag = 1

			if aa:
				glob.led_buffer_original = glob.led_buffer[:]  # We need to pass the unchanged buffer as well
				for anti_alias_step in range(
						10):  # We now anti-alias scroll everything one pixel to the left to make it smooth, in 10 steps
					glob.led_buffer = anti_alias_left_10(glob.led_buffer, glob.led_buffer_original, anti_alias_step)

					glob.transmit_flag = True  # We send the intermediate step to the screen

					sleep(
						speed / 10)  # 0.01 gives a reasonable speed, as weed need 10 of those per "real" left movement

			# The glob.led_buffer is now scrolled one step to the left - we then repeat the loop. This replaces the anti-alias scrolled buffer with the "real" one,
			# which is identical except it also adds a new column to the right from the display_buffer (where we keep our text / graphics)
			if not aa: sleep(speed)


def show_img(image, brightness=-1):
	"""
    Displays an image (16x16) on the LED display. Will blend with black if alpha. Supports animated images
    TODO: Support animated GIFs with offsets
    @param image: File name (relative or abs path)
    """
	animated = False
	run = True  # We set this flag to False after first run if there is no animation

	# What we have learned so far:
	# PNG: No problem! 256 tuples of rgb translates easy into led_buffer
	# GIF: First we seek() the first image (even if there is only one), wich gives us a grayscale version of the image,
	# then we have to perform some magic to get the color in. This because GIFs store their color palette data in a
	# palette table, with each pixel value a reference to this table. So to get to led_buffer we need to convert this

	try:
		img = Image.open(image)
	except FileNotFoundError:
		print("Unable to load image ", image, "- file not found")
		sys.exit(1)

	if not (img.size[0] == img.size[1] == 16):
		sys.exit("ERROR: Only accept 16x16 images")

	if brightness != - 1: ext_effect(glob.sparkCore, 'brightness',
	                                 brightness)  # The default is to not mess with brightness

	if 'duration' in img.info:
		animated = True

	if img.mode in ('RGBA', 'LA'):  # Image has alpha channel - which we merge with black
		img = pure_pil_alpha_to_color_v2(img, color=(0, 0, 0))  # Note, this destroys the img.info data

	while run:
		if not animated: run = False  # No animation -> only one run

		# TODO: img = img.filter(ImageFilter.GaussianBlur(radius=1))

		# We convert the list of RGB tuples into a list of RGB lists
		if img.format == "GIF":
			converted_img = img.convert()  # This adds palette data to GIFs (otherwise monochrome), BUT DESTROYS SEEK FUNCTIONALITY
			rgb_pixels = list(converted_img.getdata())
		else:
			rgb_pixels = list(img.getdata())

		# TODO: THIS IS WHERE IT FAILS!!!! rgb_pixels is not a list of lists and must be converted!!!
		# I don't get why, but instead of getting what we want, we get a list of tuples with R,G,B,A, so we make a list of lists and strip the A
		for n in range(16 * 16):
			if len(rgb_pixels[n]) == 4:
				rgb_pixels[n] = list(rgb_pixels[n][:-1])
			else:
				rgb_pixels[n] = list(rgb_pixels[n])

		glob.led_buffer = rgb_pixels
		glob.transmit_flag = True

		if animated:
			sleep(img.info['duration'] / 1000)  # Waiting for time stipulated in GIF

			try:
				img.seek(img.tell() + 1)  # Seeking to next frame in animated gif
			except EOFError:  # We've read the last frame
				run = False


def clock_digital(color):
	"""
    Displays real-time clock on display using tiny 3x5 font
    @param color: font color
    @return:
    """

	font_tiny = list(SparkLED_data.numfont3x5)
	black = [0, 0, 0]

	n = [None] * 10
	for j in range(10):
		n[j] = [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
		        [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
		        [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]

	for number in range(10):
		for byte_value in range(5):
			if font_tiny[byte_value + number * 5] & 0b0100:
				n[number][0 + byte_value * 3] = color
			else:
				n[number][0 + byte_value * 3] = black

			if font_tiny[byte_value + number * 5] & 0b0010:
				n[number][1 + byte_value * 3] = color
			else:
				n[number][1 + byte_value * 3] = black

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
		day = list(map(int, str(date_time[2])))
		hour = list(map(int, str(date_time[3])))
		minute = list(map(int, str(date_time[4])))

		if len(month) == 1: month = [0] + month
		if len(day) == 1: day = [0] + day
		if len(hour) == 1: hour = [0] + hour
		if len(minute) == 1: minute = [0] + minute

		# Screen layout:
		# 16 x 16: we need 3 leds per number, with 1 led in between each, four numbers across: xxx0 xxx0 0xxx 0xxx - in the double zeron in the middle we have : or / for presentation
		# Vertically we have 5 lines per number: 3 rows with only one space. Probably better to only do two rows (hh:mm and dd:MM), perhaps with a line between: 0NNN NN0L 0NNN NN00
		# TODO: Anti-aliasing to be considered lates
		glob.transmit_flag = 0  # To avoid flicker

		# First 5 rows of numbers (hh:mm)
		glob.led_buffer[0:16] = [black] * 16  # First we add one blank line
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

		glob.led_buffer[6 * 16:9 * 16] = [black] * 16 * 3  # Three blank lines

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

		glob.transmit_flag = 1  # To avoid flicker

		# print(len(glob.led_buffer)/16)
		#print(glob.led_buffer)
		sleep(1)
	return


if __name__ == "__main__":  # Making sure we don't have problems if importing from this file as a module

	buffer_to_screen.updates = 0  # We need to set this variable AFTER the function definition
	glob.abort_flag = 0  # True if we want to abort current execution
	glob.transmit_flag = False  # No screen updates until requested by a function

	glob.sparkCore = initialize()

	# signal.signal(signal.SIGINT, signal_handler)  # Setting up th signal handler to arrange tidy exit if manually interrupted

	init_thread(transmit_loop,
	            glob.sparkCore)  # Starts main transmit thread - to LED if not glob.OFFLINE, curses otherwise
	# Does nothing until a function sets glob.transmit_flag = True

	#ext_effect(glob.sparkCore, 'brightness', 10)

	#################################################################################################################################################
	# This is the main loop - it processes sensor inputs and timers and controls what goes on the display and when                                #
	#       It never exists unless there is an error.                                                                                                   #
	#################################################################################################################################################

	sleep(1)
	while True:
		if not glob.connected: glob.sparkCore = initialize()  # If we loose the connection we try reconnecting

		#clock_digital([255,128,0])

		"""
        (text_length, text_buffer) = text_to_buffer("Scrolling is fun!?!", 100, 10, 5)  # Put text message in large (16 row high) buffer
        init_thread(scroll_display_buffer, text_length, 10, text_buffer, True)

        while True: pass        # NOTE: If you do not stop it here, there will be 1000000 scrollers on top of each other!!!
		"""


		#while True: print("I am free")
		#clock_digital([128,0,0])


		#effects.active_effect = 'rain'
		#while True: show_img('images/fractal.gif')rrrrr22rrrrr22222rrrrrrrrrrrrrrrrrrrrrrrrrrrrr

		#ext_effect(glob.sparkCore,'hw_test')             # Test LED display using SparkCore function
		#sleep(1)
		#show_img('images/sunmoon.gif')  #ext_effect(glob.sparkCore,'hw_test')             # Test LED display using SparkCore function
		#sleep(5)
		#print("SHOWING IMAGE(s)")
		#show_img('images/bell.png')
		#show_img('images/Bubble.gif')

		#ext_effect(glob.sparkCore,'hw_test')             # Test LED display using SparkCore function
		#while True: pass
		#sleep(0)
		#while True: show_img('images/skull.png')
		#sleep(1)
		#ext_effect(SparkCore,'hw_test')             # Test LED display using SparkCore function
		#ext_effect(SparkCore,'brightness', 30)
		#ext_effect(SparkCore,'hw_test')             # Test LED display using SparkCore function

		show_img('images/fractal.gif')  # "Cheat" to show colorful fractal using animated gif
		#ext_effect(glob.sparkCore, 'brightness', 1)
		#show_img('images/ajax_loader_bar.gif')
		#while True: pass

		#show_img('images/fractal.gif')
		#sleep(2)
		#show_img('images/spinner2.gif')
		#sleep(2)
		#show_img('images/spinner3.gif')
		#sleep(2)
		#show_img('images/skull.png')
		#sleep(2)
		#show_img('images/ajax_loader_bar.gif')

		#show_img('images/padlock.png')
