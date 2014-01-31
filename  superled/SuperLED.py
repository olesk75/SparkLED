# In Python 3.x the strings are unicode by default. When sending data to Arduino, they have to be converted to bytes.
# This can be done by prefixing the string with b:

# Things to keep in mind.

# Termonology:
# rgb_buffer	: Arduino compatible buffer with 3 bytes per LED, 768 bytes in total ( 16 * 16 * 3)
# screen_buffer : the final 768 byte buffer we send to the arduino
# transmit_flag : flag that indicates if the transmit thread can send the screen_buffer to the Arduino or if it should wait


import serial
from time import sleep
import sys
import signal

from SuperLED_lib import *

serial_port = '/dev/tty.usbmodem411'
baud_rate = 500000      # We get about 1B per 10baud, so with 500'000 we get about 50'000B/sec, which is a theoretical frame rate of 65 frames per second
NUM_LEDS = 256
LEDoff = bytes([0x0f, 0x0f, 0x0f])  # black led

transmit_flag = 0
screen_buffer = bytearray()     # An array of bytes

DEBUG = 1       # Increase verbosity
OFFLINE = 1     # Don't write to serial port

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
	global screen_buffer

	if OFFLINE:
		curses_draw(screen_buffer)
	else:
		if len(screen_buffer) != 768:
			print('Error: screen_buffer size :', len(screen_buffer), 'should be 768 (16*16*3)')

		for line in range(16):
			if line % 2: screen_buffer[line * 16:line * 16 + 16] = reversed(screen_buffer[line * 16:line * 16 + 16])  # We need to reverse every second line (1,3,5 etc)


		ser.write(screen_buffer)
		response = ser.read(3)
		if response != b'':
			if int(response) != (NUM_LEDS * 3):
				print("Error, in stead of '768', Arduino said:", int(response.decode('ascii')))


def compress(buffer, factor):
	# buffer is a list of lists, each inner list consisting of 3 ints, each of these 1 or 0
	length = len(buffer)

	# TODO: SIMPLY ITERATE THROUGH THE LIST AND REMOVE ELEMENT        LINE *(0 - FACTOR) : LINE *(0 - FACTOR) errrrrR, you GET THE PONT


	return buffer


def scroller(scroll_text, red, green, blue, speed):
	import SuperLED_data
	global NUM_LEDS
	global screen_buffer

	font = SuperLED_data.font1
	font_compress = 1   # How many empty columns on each side of the letter we want to remove for readability

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
				#if DEBUG: print(first, end="")

		#print()

	#time.sleep(1) # DEBUG: Gives us time to see the text


	# display_buffer is a list of lists, each inner list consisting of 3 ints, each of these 1 or 0
	# We can now multiply all the inner lists with the right color values
	for led in display_buffer:
		led[0] *= red
		led[1] *= green
		led[2] *= blue

	values_per_line = len(display_buffer) / 16  # The number og LED value COLUMNS  we have to display, which must finally be compied to the screen_buffer

	#print('We have ', values_per_line, 'columns of text data to display')
	#print(display_buffer)

	#display_buffer = compress(display_buffer, font_compress)

	while 1:    # TODO: Need to be interrupted somehow with a flag set by a threaded process

		cutoff = values_per_line - 16  # how much we need to skip from each line to make the data fit into screen buffer

		for scroll_offset in range(len(scroll_text) * 16 - 16):
			#print(scroll_offset)
			screen_buffer = bytearray()     # Resetting the screen buffer
			for line in range(16):

				visible_start = int(line * (16 + cutoff)) + scroll_offset      # Start (in the display_buffer) of the visible line
				visible_end = int(line * (16 + cutoff) + 16) + scroll_offset   # End (in the display_buffer) of the visible line

				visible_line = display_buffer[visible_start: visible_end]



				pos_counter = 0
				for led_rgb in visible_line:
					screen_buffer.append(int(str(led_rgb[0]).encode(encoding="ascii")))
					screen_buffer.append(int(str(led_rgb[1]).encode(encoding="ascii")))
					screen_buffer.append(int(str(led_rgb[2]).encode(encoding="ascii")))


			draw_screen()  # Uses global screen_buffer to help threads later
			sleep(1 - speed / 10)

		#print("DEBUG: drawn")
		#exit(0)



initialize()
blank()
scroller("heyjpq", 100, 0, 0, 9)     # Message in a orangeish color scrolling at speed 1

ser.close()