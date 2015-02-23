#SuperLED

This is a client/server suite for controlling a LED display. 

## Main components

![Diagram](https://github.com/olesk75/SuperLED/blob/gh-pages/illustrations/setup.png)

**LED display** : array ([16x16 in my case](http://rgb-123.com/product/1616-16-x-16-rgb-led-matrix/)) of Neopixel WS2812B RGB leds

**Spark Core**: The [Spark Core](http://spark.io) is a wifi and cloud enabled development platform that controls the leds and acts as server, programmed in C (Arduino)

**"SuperLED" scripts**: python client that connects to the Spark Core over wifi and sends commands and animations/pictures for it to display on the LED display

**FastLED**: [FastLED](http://fastled.io) is an excellent library for controlling a range of LED strips and displays. For now, using the [Spark Core branch](https://github.com/FastLED/FastLED/tree/sparkcore) until it gets merged into master

## How does it work?
Just a few simple steps to get it to work:

1. Get a Spark Core and wire it up to your LED display. Some [instructions here](https://community.spark.io/t/adafruit-neopixel-library-ported/1143/160), but don't get confused by mentions of the Neopixel library. We will use FastLED instead - it's significantly more feature rich and faster. Alternatively, skip both LEDs and Spark Core (see below)
2. Flash the [SparkLED.ino file](https://github.com/olesk75/SuperLED/blob/master/SparkCore/SparkLED.ino) to your Spark Core ([and find it's IP address](http://blog.spark.io/2014/03/11/spark-publish/))
- Replace my internal IP address in *serverIP* in the initialize() function in [SuperLED.py](https://github.com/olesk75/SuperLED/blob/master/SuperLED.py) with yours
3. Run SuperLED.py to test, and tweak __main__ in SuperLED to include the animations/scrollers/images you want

**Note:** You can test this script without a LED display or SparkCore by running the [led_server_emulator.py](https://github.com/olesk75/SuperLED/blob/master/Tools/led_server_emulator.py) script. Just rememer to set the IP address in *serverIP* in the initialize() function in SuperLED.py to 127.0.0.1 (localhost) if you run both SuperLED and the emulator on the same machine

**Also note**: It is my intention to automatically find the IP adress of the Spark Core using the [Spyrk](https://github.com/Alidron/spyrk) library, though this is not complete. It needs some data in a file called config.py, two lines to be exact, like so:
```
DEVICEID = '555555555555555555555555'
ACCESS_TOKEN = '6666666666666666666666666666666666666666'
```

Both deviceid and access token can be found at [spark.io](spark.io) once you have registered the core. If you're using the emulator, just put some dummy values here, like the ones in this example.

**And finally note**: The Python is all written in Python 3.4. Pthon 2.x will not work without a rewrite
