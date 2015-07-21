""" This file contains global variables used in the SparkLED project
	The objective is to shrink this file as much as possible and use
	function arguments in stead wherever possible.
"""

# Global variables
transmit_flag = False	# Set when we're ready to let the transmit thread tranmit the transmit_buffer, which then unsets flag
abort_flag = None	# Set when we want to terminate connection between server and client. Sets server in listening mode.
connected = False	# Set when client is connected to server

OFFLINE = None		# For debugging: do not transmit transmit_buffer (offline debugging)
DEBUG = True		# Dump debug output to terminal from client scripts
NUM_LEDS = None

sparkCore = None

PORT = 2208		# Port number to connect to server

settings = {
	'OFFLINE': False,
	'DISPLAY_MODE': 'LED',
	'DEBUG': False
}

led_buffer = [''] * 256  # The list RGB colors for the LED
for i in range(256):
	led_buffer[i] = [0, 0, 0]  # 256 x 3 list

transmit_buffer = [None] * 256  # We need this copy of the led_buffer to avoid overwriting while we do effects and prepare to transmit the data
for i in range(256):
	transmit_buffer[i] = [None] * 3
