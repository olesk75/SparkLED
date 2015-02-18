/*
    SuperLED-server.ino
    
    This program is intended to run on the original Spark Core and uses the FastLED library.
    Its purpose it to run a minimal TCP server, which listens for connections that provides
    it with data to display on a 16x16 LED matrix.
    
    The incoming data format is 0x00 followed by a command code (both bytes). If the command
    code is 'G' ("go code"), the next 768 bytes is expected to be red, green and blue byte
    triplets for each of the 256 leds (or "screen pixels").
    
    Other command codes can be used to trigger actions on the LED matric, such as setting 
    brightness, blank display etc.
    
    The program tries to be robust in assuming that the connection can break at any time.
    
    The key issue to watch is speed. If the network read loop is not fast enough when reading
    a "screenfull" (768 bytes), we will not be able to maintain a framerate fast enough for
    animations. 
    
    For this program to do anything useful, it must be paired with a client - in this case
    "SuperLED" - a python client that feeds this program with data.
    
    The IP-adress of the Spark Core, can be found manually using curl as follows:
    curl "https://api.spark.io/v1/devices/ DEVICEID /localIP?access_token= ACCESS TOKEN"
    where DEVICEID and ACCESS TOKEN are availble at the spark.io web site.
    
*/


#include "FastLED/FastLED.h"
FASTLED_USING_NAMESPACE

#include "application.h"

#define NUM_LEDS 256
#define DATA_PIN 2

#define int_led D7

CRGB leds[NUM_LEDS];

TCPServer server = TCPServer(2208);
TCPClient client;
char myIpAddress[24];

void setup() 
{

    FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
    
    boot_screen(); //showing boot screen to show we're alive
    LEDS.setBrightness(255);
    
    pinMode(int_led, OUTPUT);
    digitalWrite(int_led, LOW);
    
    server.begin();
    
    Spark.variable("localIP", &myIpAddress, STRING);
    IPAddress myIp = WiFi.localIP();
    sprintf(myIpAddress, "%d.%d.%d.%d", myIp[0], myIp[1], myIp[2], myIp[3]);

}


void loop() 
{
    Spark.process();
    
    digitalWrite(int_led, LOW);     // Internal led OFF to verify visually
    
    client = server.available();
    
    if (client.connected()) {
        digitalWrite(int_led, HIGH);     // Internal led ON to verify visually
        
        while(client.read() != 0x00 && client.read() != 'K') { 
            Spark.process();
            if (!client.connected()) client = server.available();   // and if we've lost connection, we try to reconnect
        }
        
        client.write('A'); // We ack connection and are ready to go
        
        while(client.connected()) {
            while (client.read() != 0x00) {                             // Until we get the opening 0x00....
                Spark.process();                                        // we check the cloud ...
                if (!client.connected()) client = server.available();   // and if we've lost connection, we try to reconnect
            }
                
            uint8_t code = client.read();
            
            if (code == 'G') {      // getting screen update ("Go code" - \x00G)
                client.write('A'); // We ack connection

                
                uint8_t *ptr = &leds[0][0];
                
                for (uint16_t pixel = 0; pixel < 768; pixel++) {
                    while (client.available()<1) Spark.process(); 
                    *ptr++ = client.read();
                }
                
                FastLED.show();
                if (client.connected()) client.write('D'); // We tell the client we are Done
                
            } else if (code == 'T') {
                // Hardware test pattern
            
            }   
        }
    }
}


/*
	Boot screen - shows a sweeping line from left to right
*/
void boot_screen() {
	int real_x;
	int multiplier;
	uint8_t stripes = 16;		
	LEDS.setBrightness(255);		// Maximum brightness by default
	
	for (int x = 0; x < stripes + 5; x++) {
		for (int y = 0; y < stripes; y++) {
			real_x = x;
			multiplier = 1;
			if (y % 2) {
				real_x = stripes - 1 - x;	// we reverse every second line 
				multiplier = -1;
				}
				
			if (real_x < stripes && real_x >= 0) leds[y * stripes + real_x] = CRGB(255,255,255);							// main line
			if (real_x - 1 * multiplier < stripes && real_x - 1 * multiplier >= 0) leds[(real_x - 1 * multiplier) + stripes * y] = CRGB(192,192,192);	// second line
			if (real_x - 2 * multiplier < stripes && real_x - 2 * multiplier >= 0) leds[(real_x - 2 * multiplier) + stripes * y] = CRGB(64,64,64);		// third line
			if (real_x - 3 * multiplier < stripes && real_x - 3 * multiplier >= 0) leds[(real_x - 3 * multiplier) + stripes * y] = CRGB(32,32,32);		// fourth line
			if (real_x - 4 * multiplier < stripes && real_x - 4 * multiplier >= 0) leds[(real_x - 4 * multiplier) + stripes * y] = CRGB(16,16,16);		// fifth line
			if (real_x - 5 * multiplier < stripes && real_x - 5 * multiplier >= 0) leds[(real_x - 5 * multiplier) + stripes * y] = CRGB(0,0,0);			// sixth line
		}
		FastLED.show();
		delay(10);
	}
	
}