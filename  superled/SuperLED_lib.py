""" This module contains all the supporting functions for SuperLED.py.
        Only functions that create the final effects for the LED display remain
        in SuperLED.py, the rest goes here.
        Some additional global variables are found in and imported from SuperLED_globals.py
        The font and image data are store in and imported from SuperLED_data.py
"""
import curses
import threading
from PIL import Image
import colorsys
import socket
from copy import deepcopy
from time import sleep, time
import random
import SuperLED_globals as glob
import SuperLED_data
from sys import exit


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
            if pixel != [0,0,0]: color = pixel              # Finding the monochrome pixel color

    if color == [None, None, None]: return buffer   # If the whole screen is black, we got nothing to do

    bright = rgb_get_brightness(color)          # Finding the color's default brightness value

    #       1)      For each real scrolled pixel we scroll 10 "virtual" pixels (between the real pixels)
    #       2)      We do this by a range(10) loop where we reduce brightness of the original pixel 10% each time IF AND ONLY IF the pixel to the right is black (we work monochrome here). Else skip to 3)
    #       3)      Similarly we in the same loop increase the brightness of the pixel to the left by 10% (same color)
    #       4)      After 10 iterations we have a fully saturated pixel on the left of our original pixel (and black pixel to the right if the real pixel to the right was black) and we exit loop to start
    #               over again after real pixels have been scrolled one position left

    # TODO: Fix the fact that thereis little *visible* difference between the highest brightness value (non-linear relationship)

    change = float((current_step + 1) / 10)

    for col in range(15):           # We go line by line - making a single step for all pixels
            for row in range(16):       # We iterate over each pixel in the visible_line except the last one (it doesn't have anything to the right)
                    cur_pixel = row * 16 + col

                    if original_buffer[cur_pixel + 1] == color and original_buffer[cur_pixel] == black:     # Pixel to the right is ON, and the current isn't --> [[0,0,0], [125,50,0]]
                            buffer[cur_pixel] = rgb_set_brightness(color, bright * change)                                          # We migrate ON pixel from the right onto this one (if it's already lit -> no change)

                    if original_buffer[cur_pixel + 1] == black and original_buffer[cur_pixel] == color:             # Pixel to the right is OFF, and the current isn't  --> [[125,50,0], [0,0,0]]
                            buffer[cur_pixel] = rgb_set_brightness(color, bright * (1 - change))                            # We migrate OFF pixel from the right onto this one (if it's already lit -> no change)

    return buffer


def convert_buffer():
    """
    Compensates for the display's zigzag pattern of LEDs (if LED active) and returns bytearray()
    Also changes all 0 1 (still off on LED, but we need the 0 to send control codes)
    @return: updated RGB led buffer ready to transmit
    """

    line_buffer = deepcopy(glob.led_buffer)

    """
        Note, depending on what the LED driver expects, we might need to enable this snippet which reverses every second line
    """

    # Due to the LEDs on this particular display being in a zigzag pattern, we need to reverse the orientation of
    # every second line. 1,3,5,7,9,11,13,15 to be precise. But *without* reversing the byte values.
    # Reversing the zigzag pattern
    for line in range(1,16,2):  # Every second line from 1 to and including 15
            for led in range(16 - 1, -1, -1):
                    line_buffer[(line * 16) + (15 - led)] = glob.led_buffer[line * 16 + led]

    # We convert the whole transmit_buffer list into a string of bytes that we can write to curses/Arduino
    byte_buffer = bytearray()

    for rgb in line_buffer: # For each led... 256 in total
            if rgb[0] == 0: rgb[0] = 1      # Zero is reserved for control codes
            if rgb[1] == 0: rgb[1] = 1
            if rgb[2] == 0: rgb[2] = 1

            """
                NOTE: The current set of the Adafruit NeoPixel is NOT set up with R,G,B, with with G, R, B! (I know!!) RGB would be too easy
            """

            byte_buffer.append(rgb[1])  # Green
            byte_buffer.append(rgb[0])  # Red
            byte_buffer.append(rgb[2])  # Blue

    return byte_buffer


# noinspection PyShadowingNames,PyShadowingNames
def buffer_to_screen(server):
    try:
        server.sendall(b'\x00' + b'G')
    except:
        print("- Go code 'G' failed")
        exit()
    while True:
        try:
            glob.transmit_flag = False
            if server.recv(1) == b'A': break
        except socket.error as error:
            if format(error) == "timed out":
                print("ERROR: Timeout waiting for LED server to acknowledge ('A') having received Go code")
            else:
                print("ERROR: Connect failed:", format(error))

            exit(1)

    #print("DEBUG: 'A' from Spark Core")

    server.sendall(convert_buffer())
    glob.transmit_flag = False

    try:
        while True:
            if server.recv(1) == b'D': break
    except socket.error as error:
            if format(error) == "timed out":
                print("ERROR: Timeout waiting for LED server to send Done ('D') after receiving 768 bytes'")
                exit(1)
            else:
                print("ERROR: Connect failed:", format(error))
                exit(1)

    #print("DEBUG: 'D' from Spark Core")

    if glob.DEBUG:
        print("Display updates:\033[1m", buffer_to_screen.updates, "\033[0m", end='\r')
        buffer_to_screen.updates += 1


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

    # Reversing the zigzag pattern

    for line in range(1,16,2):  # Every second line from 1 to and including 15
            for led in range(16 - 1, -1, -1):
                    glob.line_buffer[15 - led] = transmit_buffer[line * 16 + led]

            transmit_buffer[line * 16:line * 16 + 16] = glob.line_buffer[0:16]


    if effects.active_effect == 'rain':     # Makes the screen "rain away"
            effects.iterations = 14
            effects.random_pixels = random.sample(range(16), 16)    # Randomly ordered pixels
            line = 14 - effects.progress    # We start with the seond line from the bottom
            for x in effects.random_pixels:
                    color = get_pixel(x, line)      # From led_buffer
                    transmit_buffer[x + (line + 1) * 16] = color
                    transmit_buffer[x + line * 16] = [0x00, 0x00, 0x00]

    else: effects.iterations = 0

    if effects.progress == effects.iterations:
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


def ext_effect(server, effect, effect_value = None):
    """
    Triggers an external effect (i.e. makes the Arduino perform the effect for us
    @param server: Server connection (Arduino)
    @param effect: Effect name
    @param effect_value: Effect value
    """
    glob.transmit_flag = 0

    if effect == 'brightness': hw_effect = b'B'
    if effect == 'hw_test': hw_effect = b'T'
    if effect == 'blank': hw_effect = b'Z'

    #if glob.DEBUG: print("\n---> Performing", effect)

    try: server.sendall(b'\x00' + hw_effect)
    except:
        print("- Sending of effect code,", hw_effect, "failed")
        exit()


    if effect_value:    # Could be None
            value_string = bytes([effect_value])
            #print(value_string)
            server.sendall(value_string)       # Send the 3 digits as bytes

    # Since some of these effects can take some time, we wait here until we get 'D'one from the Spark Core
    #while True:
    #		if server.recv(1) == b'D': break


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


def get_pixel(x, y):
    """
    get_pixel reads a single pixel color value from the display_buffer
    @param x: x coordinate (0-15)
    @param y: y coordinate (0-15)
    @param color: list [r, g, b]
    """
    return glob.led_buffer[x + y * 16]


def init_thread(thread_function, *args):
    t = threading.Thread(target=thread_function, args = args,)
    t.daemon = True  # thread dies when main thread (only non-daemon thread) exits.
    t.start()


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


def put_line(x1, y1, x2, y2):
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


def rgb_get_brightness(rgb_values):
    hls_values = list(colorsys.rgb_to_hls(rgb_values[0] / 255, rgb_values[1] / 255, rgb_values[2] / 255))
    return hls_values[1]


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


# noinspection PyUnusedLocal,PyUnusedLocal,PyShadowingNames
def signal_handler(signal, frame):
    glob.transmit_flag = False
    print('\n- Interrupted manually, aborting')

    ext_effect(glob.sparkCore, 'blank')
    print('- Sent screen blank code')
    glob.sparkCore.sendall(b'\x00' + b'Q')     # Telling Spark Core to hang up connection
    print("- Requested network disconnect")

    glob.sparkCore.close()
    print("- Local network disconnect")

    print("Exiting...")
    exit(0)

def text_to_buffer(display_text, red, green, blue):
    """
    Creates a buffer (in display_buffer) that contains the full text
    @rtype : length of text string (letters)
    @param display_text: The text we will put in the display_buffer (which can be of arbitrary size, unlike the glob.led_buffer (which is always 16*16*3)
    @param red: red value (0-255)
    @param green: green value (0-255)
    @param blue: blue value (0-255)
    """

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

    for msg_line in msg_buffer:             # Each element in the msg_buffer is a bytearray line
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

    return len(display_text), display_buffer


def transmit_loop(server):  # TODO: Reinitialize the connection if the keep-alive is not ack'ed by the Spark Core
    """
    The main LED update loop that runs perpetually.

    An important aspect is the transmit_loop.start variable, which is a local persistent variable that counts the seconds between each execution
    This allows us to cap the frame rate in order to avoid drowning the Spark Core in requests.
    Similarly the transmit_loop.idle variable checks how long since we last transmitted something, and if the time is more that 10 seconds, we
    send a keep-alive to the Spark Core to avoid a network timeout.

    """

    while True:
        if type(glob.led_buffer[0][0]) is not int: glob.transmit_flag = 0     # We skip if the glob.led_buffer is not ready yet

        # try: transmit_loop.start                        # Time since last iteration (persistent variable)
        # except: transmit_loop.start = time()            # First iteration, assigning current time to variable
        #
        # try: transmit_loop.idle                         # Time since last transmission (persistent variable)
        # except: transmit_loop.idle = time()            # First iteration, assigning current time to variable
        #
        # if time() - transmit_loop.start < 0.0033:        # We cap transfers at about 30 frames/second
        #     #print("DEBUG: Too quick. Time elapsed since last: " + str('{0:.10f}'.format(time() - transmit_loop.start)))
        #     #print(".", end='')
        #     glob.transmit_flag = 0                      # We simply avoid calling buffer_to_screen() until enough time has passed
        #     transmit_loop.start = time()                    # Resetting execution timer

        """
        if time() - transmit_loop.idle > 10:            # We have been idle for 10 seconds or more
            print("\nDEBUG: Idle for 10 seconds, sending keep-alive to Spark Core")
            server.sendall(b'K')                           # Sending keepalive
            while True:                                 # We keep trying until either: conection breaks or connection times out or we get a 'D' response
                try: answer = server.recv(1)
                except ConnectionResetError:
                    print("DEBUG: Lost connection")
                    glob.connected = False
                    glob.transmit_flag = 0
                    break
                if time() - transmit_loop.idle > 15:    # We haven't received an acknowledge for 5 seconds (10 + 5)
                    print("ERROR: Connection with Spark Core timed out")
                    glob.connected = False
                    glob.transmit_flag = 0
                if answer == b'D': break
                transmit_loop.idle = time()                 # Resetting idle timer every time we send a screen update
        """

        if glob.transmit_flag:
            glob.transmit_flag = 0                      # Make sure we don't end up sending several times on top of eachother
                                                                                                    # Means we must actively set glob.transmit_flag = 1 in outside code
            #transmit_loop.start = time()                # Resetting exceution timer
            buffer_to_screen(server)