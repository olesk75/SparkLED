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
import colorsys
from math import ceil

# Global variable definitions
serial_port = '/dev/tty.usbmodem411'
baud_rate = 500000                  # We get about 1B per 10baud, so with 500'000 we get about 50'000B/sec, which is a theoretical frame rate of 65 frames per second
NUM_LEDS = 256
LEDoff = bytes([0x0c, 0x0c, 0x0c])  # black led
transmit_flag = 0

led_buffer = [None] * 256           # The list of bytes to be sent to curses or Arduino
for i in range(256):
	led_buffer[i] = [None] * 3      # 256 x 3 list

DEBUG = 1       # Increase verbosity
OFFLINE = 0     # Don't write to serial port

ser = serial.Serial()   # Preparing the global serial object, ser

def signal_handler(signal, frame):
		print('Interrupted manually, aborting')
		ser.close()
		sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)



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
		response = ser.read(1)
	#print (str(response), end="")

	# Ok, we got 'S' and are ready to start
	print("- Start code 'S' received from Arduino - ready!")

	if ser.write(b'G') == 1:
		print("- Go code 'G' sent successfully")
	else:
		print("- Go code 'G' failed")
		sys.exit("Unable to send go code to Arduino")

	response = ser.read(1);
	if response != '':
		if response == b'A':
			print("- Go code acknowledged by Arduino - ready to rumble!")
		else:
			print("- Go code NOT acknowledged by Arduino - aborting...")
			sys.exit()

	print("--- INITIALIZATION COMPLETE ---\n")


def blank():
	if OFFLINE: return()
	print("- Blanking screen - Sending 256 * 3 bytes of zero")
	ser.write(LEDoff * NUM_LEDS)

	response = ser.read(3)
	if response != '':
		if int(response) == (NUM_LEDS * 3):
			print("- Full screen update acknowledged")
		else:
			print("Error, in stead of '768', Arduino said:", int(response))


def draw_screen():
	screen_buffer = [0,0,0]   # BOGUS! REPLACE THIS WITH THE led_buffer list ([256][3])

	if OFFLINE:
		curses_draw(effects())
	else:


		# Starting the inversion of every second line due to HW layout of LED board
		temp_buffer = [None] * 16           # One line of leds
		for i in range(16):
			temp_buffer[i] = [None] * 3      # 16 x 3 list

		for n in range(1, 16, 2):   # Every second line, starting at the second from the top
			led_buffer[n*16:n*16+16] = reversed(led_buffer[n*16:n*16+16])

		ser.write(effects())

		response = ser.read(3)
		if response != b'':
			if int(response) != (NUM_LEDS * 3):
				print("Error, in stead of '768', Arduino said:", int(response.decode('ascii')))


def scroller(scroll_text, red, green, blue, speed):
	import SuperLED_data
	global NUM_LEDS
	global transmit_flag
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


	while 1:    # TODO: Need to be interrupted somehow with a flag set by a threaded process

		cutoff = values_per_line - 16  # how much we need to skip from each line to make the data fit into screen buffer

		transmit_flag = 0   # Disabling transmission of data while updating led_buffer

		for scroll_offset in range(len(scroll_text) * 16 - 16):

			screen_buffer = bytearray()     # Resetting the screen buffer # DELETE
			for line in range(16):

				visible_start = int(line * (16 + cutoff)) + scroll_offset      # Start (in the display_buffer) of the visible line
				visible_end = int(line * (16 + cutoff) + 16) + scroll_offset   # End (in the display_buffer) of the visible line

				visible_line = display_buffer[visible_start: visible_end]

				#print("Visible line", visible_line)


				for rgb in range(16):
					led_buffer[line * 16 + rgb] = visible_line[rgb]


			#draw_screen()  # Not called manually anymore - done in separate thread
			transmit_flag = 1   # Ready to transmit through thread
			#print(led_buffer)
			sleep(1 - speed / 10)   # Without this Arduino goes berserk


def init_thread(thread_function):
	t = threading.Thread(target=thread_function)
	t.daemon = True  # thread dies when main thread (only non-daemon thread) exits.
	t.start()


def transmit_data():
	global transmit_flag
	while True:
		if transmit_flag:
			transmit_flag = 0   # Make sure we don't end up sending several times on top of eachother
			draw_screen()


# noinspection PyUnresolvedReferences
def effects():
	global led_buffer

	if effects.active_effect == 'down' and effects.progress < 16:
		for n in range(effects.progress):
			#led_buffer[(15-n) * 16 : ]


	if effects.active_effect == 'up' and effects.progress < 16:
		for n in range(effects.progress):
			buffer = buffer[16 * 3:] + bytes([0] * 16 * 3)


	if effects.active_effect == 'fade' and effects.progress < 16:
		n = 0
		while n < len(buffer):
			hls = colorsys.rgb_to_hls(buffer[n] / 256, buffer[n+1] / 256, buffer[n+2] / 256)    # Converting first from 0-256 to 0-1 values (floats)
			if hls[1] > 0:  # Only dimming the "lightness" 10% each turn
				[h, l, s] = [hls[0], hls[1] * 0.01, hls[2]]
				[red, green, blue] = colorsys.hls_to_rgb(h, l, s)
				[buffer[n], buffer[n+1], buffer[n+2]] = [ceil(red * 256), ceil(green * 256), ceil(blue * 256)]
			n += 3

	if effects.progress == 16:
		effects.progress = 0    # We're done, making ready for another run/effect
		effects.active_effect = 'none'
	else: effects.progress += 1

	buffer = bytearray()

	# Finally, we convert the whole led_buffer list into a strong of bytes that we can write to curses/Arduino
	for rgb in led_buffer:          # For each led... 256 in total
		buffer.append(rgb[0])
		buffer.append(rgb[1])
		buffer.append(rgb[2])

	return buffer

effects.active_effect = 'none'      # Static variable that contains the active effect - stays between funtion calls
effects.progress = 0                # Static variable that measures the progress of the active effect - stays between funtion calls

initialize()
blank()
init_thread(transmit_data)

effects.active_effect = 'none'

scroller("heyjpq", 55, 25, 15, 9)     # Message in a orangeish color scrolling at speed 1

ser.close()
