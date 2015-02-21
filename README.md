# SuperLED

This is a client/server suite for controlling a LED display. 


## Main components
**LED display** : array ([16x16 in my case](http://rgb-123.com/product/1616-16-x-16-rgb-led-matrix/)) of Neopixel WS2812B RGB leds

**[Spark Core](http://spark.io)**: a wifi and cloud enabled development platform that controls the leds and acts as server, programmed in C (Arduino)

**Python script**: client that connects to the Spark Core over wifi and sends commands and animations/pictures for it to display on the LED display

**[FastLED](http://fastled.io)**: excellent library for controlling a range of LED strips and displays. Using the [Spark Core branch](https://github.com/FastLED/FastLED/tree/sparkcore)

## How does it work?
Just a few simple steps to get it to work:

- Get a Spark Core and wire it up to your LED display. Some [instructions here](https://community.spark.io/t/adafruit-neopixel-library-ported/1143/160), but don't get confused by mentions of the Neopixel library. We will use FastLED instead - it's significantly more feature rich and faster.
- Flash the SparkLED.ino file to your Spark Core ([and find it's IP address](http://blog.spark.io/2014/03/11/spark-publish/))
- Replace my internal IP address in *serverIP* in the initialize() function in SuperLED.py with yours
- Run SuperLED.py to test, and tweak __main__ in SuperLED to include the animations/scrollers/images you want

**Note:** You can test this script without a LED siaply or SparkCore by running the *led_server_emulator.py* script. Just rememer to set the IP address in *serverIP* in the initialize() function in SuperLED.py to 127.0.0.1 (localhost) if you run both SuperLED and the emulator on the same machine