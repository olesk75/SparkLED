    SparkLED - C code for the Spark Core LED-connected TCP server
    
    This program is intended to run on the original Spark Core and uses the FastLED library.
    Its purpose it to run a minimal TCP server, which listens for connections that provides
    it with data to display on a 16x16 LED matrix.
    
    The incoming data format is 0x00 followed by a command code (both byte values). If the 
    command code is 'G' ("go code"), the next 768 bytes is expected to be red, green and blue 
    byte triplets for each of the 256 leds (or "screen pixels").
    
    Other command codes can be used to trigger actions on the LED matric, such as setting 
    brightness, blank display etc. Also, as the initial connection is being made, the 
    expected initial command gode is 'K' to establish connection - this needs to happen
    before any other commmand. 
    
    The program tries to be robust in assuming that the connection can break at any time.
    It will also assume that if no data is received before a 3 second timeout, the connection
    has gone down, and will procedd to flush and close the connection, sho a "no link"
    warning on the LED, and proceed to wait for a new connection to be established.
    
    The key issue to watch is speed. If the network read loop is not fast enough when reading
    a "screenfull" (768 bytes), we will not be able to maintain a framerate fast enough for
    animations. 
    
    For this program to do anything useful, it must be paired with a client - in this case
    "SparkLED" - a python client that feeds this program with data.
    
    The IP-adress of the Spark Core, can be found manually using curl as follows:
    curl "https://api.spark.io/v1/devices/ DEVICEID /localIP?access_token= ACCESS TOKEN"
    where DEVICEID and ACCESS TOKEN are availble at the spark.io web site.
