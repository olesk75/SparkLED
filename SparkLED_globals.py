""" This file contains global variables used in the SparkLED project
	The objective is to shrink this file as much as possible and use
	function arguments in stead wherever possible.
"""

# Global variables
transmit_flag = False
abort_flag = None
connected = False

OFFLINE = None
DEBUG = True
NUM_LEDS = None

sparkCore = None

PORT = 2208     # Port number for rasberryPI

settings = {
	'OFFLINE': False,
	'DISPLAY_MODE': 'LED',
	'DEBUG': False
}

led_buffer = [''] * 256  # The list of bytes to be sent to curses or Arduino
for i in range(256):
	led_buffer[i] = [0, 0, 0]  # 256 x 3 list

transmit_buffer = [None] * 256  # We need this copy of the led_buffer to avoid overwriting while we do effects and prepare to transmit the data
for i in range(256):
	transmit_buffer[i] = [None] * 3


### Test project - going OOP
class SparkLED:
	def setdata(self, value):
		self.data = value

	def display(self):
		print(self.data)
