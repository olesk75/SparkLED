/*
	This program has a simple mission: display anything sent to it over the serial line on a 16x16 RGB led display
	Note that the rows zigzag, going from left to right, right to left, left to right etc.
	
*/
#include <WiFi.h>
#include <FastLED.h>
#define NUM_LEDS 256	// yeah, we got a LOT
#define LED_LINE 48		// bytes per line (we read line by line)
#define COLOR_BYTES 3	// 3 bytes required per led for full color
#define BUFFER_SIZE 786	// NUM_LED * COLOR_BYTES
#define DATA_PIN 6		// remember to verify!
#define ledPin 13		// on-board LED for Arduino UNO

// We no longer use serial for communication with client, only for error reporting
//#define	BAUD_RATE 400000	// We should be able to do 500'000 over USB serial link with Raspberry PI
#define BAUD_RATE 115200
#define PORT 2208
 
 
CRGB leds[NUM_LEDS];			// the 256 led (786B) array, we write to this from the serial port. NOTE: 3 bytes per index

char ssid[] = "ShadowNETz";		//  your network SSID (name) 
char pass[] = "LoveSHADOWNET";			// your network password
int status = WL_IDLE_STATUS;	// the WiFi radio's status

WiFiServer server(PORT);		// server port number

bool alreadyConnected = false;
char command;
byte readByte;
String stringOne;
unsigned long time;

void setup() { 
	FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);	// setting up pin 6 and the array 'leds' to work with FastLED library
	
	Serial.begin(BAUD_RATE);	// Initializing serial communication
	
	/* DISABLED - we now only user serial for debugging, and leave LED updates to WiFi	
	Serial.write('S');
	while (Serial.read() != 'G') {}	// Waiting for "G" to continue
	Serial.write('A');		// "G" received - ack'ing
	*/

	LEDS.setBrightness(255);	// maximum brightness

	Serial.println(F("- I LIVE AGAIN!"));
	Serial.print(F("Connecting to WiFi network..."));
	  // check for the presence of the shield:
	if (WiFi.status() == WL_NO_SHIELD) {
		Serial.println(F("ERROR: WiFi shield not present")); 
		// don't continue:
		while(true);
	} 
	
	status = WiFi.begin(ssid, pass);

  	// if you're not connected, stop here:
  	if ( status != WL_CONNECTED) { 
    		Serial.println(F("failed!!!"));
    		while(true);		// Hanging here forever and ever and ever ...
	} 
	// if you are connected, print out info about the connection:
	else {
		server.begin();
    		Serial.print(F("done!. My address:"));
    		IPAddress myAddress = WiFi.localIP();
    		Serial.println(myAddress);

	}
	
	

	// We need a server that clients can connect to 
	
}

// Main loop, where we get our values form serial and display it
void loop() { 
	// wait for a new client:
  WiFiClient client = server.available();	// listen for incoming clients

	if (client) {
		Serial.println(F("We have a new client"));
		client.write('S'); 	// Sending single byte ('S') to indicate start of communications
		//time = millis();	// Starting timer
		
		
		while (client.connected()) {	// loop while the client's connected
			Serial.println(F("Spinning around the connected loop"));
			//if (millis() > time + 10000) break;	// we reset the connection if 10 seconds idle
			if (client.available()) {
				command = client.read();	// reads single byte from client
				//time = millis();	// we reset the timer as we have activity
				Serial.println(F("Command received: "));
				Serial.println(command);
	  
				switch (command) {
					case 'G':	// 'G' means we are receiving a full screen buffer
						{		  
						client.write('A');	// GO code received - acknowledging
						Serial.println(F("- Command G received (full screen update), sending A back to client"));
						while(!client.available()) {}	// we need to wait for data available to read, or will get -1
						
						client.read((byte *)leds[0], NUM_LEDS * COLOR_BYTES);
						/*
							for (int pixel = 0; pixel < NUM_LEDS / 4; pixel++)
								{
									leds[pixel].r = client.read();
									leds[pixel].g = client.read();
									leds[pixel].b = client.read();
								}
							delay(10);
							for (int pixel = 0; pixel < NUM_LEDS / 4; pixel++)
								{
									leds[pixel + 64].r = client.read();
									leds[pixel + 64].g = client.read();
									leds[pixel + 64].b = client.read();
								}
							delay(10);
							for (int pixel = 0; pixel < NUM_LEDS / 4; pixel++)
								{
									leds[pixel + 128].r = client.read();
									leds[pixel + 128].g = client.read();
									leds[pixel + 128].b = client.read();
								}
							delay(10);
							for (int pixel = 0; pixel < NUM_LEDS / 4; pixel++)
								{
									leds[pixel + 192].r = client.read();
									leds[pixel + 192].g = client.read();
									leds[pixel + 192].b = client.read();
								}
							delay(10);
						/*	
						time = millis();	// we reset the timer as we have activity
						CRGB *ptr;
    					ptr = &leds[0];       /* point our pointer at the first
                                 integer in our array 
						
						
						client.read((CRGB *)ptr, NUM_LEDS);	// undocumented Arduino socket read to get all 768 bytes in one go
						ptr = &leds[256];
						client.read(*ptr, NUM_LEDS);
						ptr = &leds[512];
						client.read(*ptr, NUM_LEDS);
						
						Serial.print("Read 768 bytes from socket in");
						Serial.print(millis() - time);
						Serial.println("ms");
						*/
						//int read_bytes = Serial.readBytes( (char*)leds, NUM_LEDS * COLOR_BYTES);	// Full screen read
						client.write('R');			// Sending Received
						Serial.println(F("- Screen update OK"));
						FastLED.show();
						}	  
						break;
					case 'B':	// 'B' means we are receiving a new brightness value
						{
						client.write('A');	// Command code received - acknowledging
						Serial.println(F("- Command B received (set brightness), sending A back to client"));
						while(!client.available()) {}
						readByte = client.read();
			
						int brightness = int(readByte);
												
						if (brightness > 0 && brightness < 256) {
							client.write('A');					// Brightness value received OK
							LEDS.setBrightness(brightness);
							FastLED.show();
							client.write('D');					// effect done
							Serial.println(F("Effect done - sending D back to client"));
							
						} 	else { 	// sending Error
							server.write('E'); 
							Serial.println(F("Effect ERROR - sending E back to client"));
							}
						break;
						}
					case 'T':	// 'T' means we are doing local tests of the pixels
						{
						client.write('A');	// Command code received - acknowledging
						Serial.println(F("Command T received (local test), sending A back to client"));
						//test_pixelrun();
						rainbow();
						client.write('D');					// effect done	
						Serial.println(F("Effect done - sending D back to client"));
						break;
						}
					case 'Z':	// 'Z' means we are zeroing the LEDs (blanking the display)
						{
						client.write('A');	// Command code received - acknowledging
						Serial.println(F("Command Z received (zero display), sending A back to client"));
						memset(leds, 0,  NUM_LEDS * sizeof(struct CRGB));
						FastLED.show();
						client.write('D');					// effect done
						Serial.println(F("Effect done - sending D back to client"));
						break;
						}
					case 'N':	// 'N' is a simple keepalive - no action required
						{
						// Update timer later
						}
					default: // no command code received - loop() repeats itself
					break;
				}
			}
		}
		// close the connection:
		client.stop();
		Serial.println(F("Client disconnected"));
	}
}



void fader() {
	int brightness = LEDS.getBrightness();
	
	for (int fade = 0; brightness - fade > 0; fade+=2) {
		LEDS.setBrightness(brightness - fade);
		FastLED.show();
		
	}
}

void test_pixelrun() { 

	for(int dot = 0; dot < NUM_LEDS; dot++) { 
		leds[dot] = CRGB::Blue;
		FastLED.show();
		leds[dot] = CRGB::Black;
	}

	FastLED.show();
      
}

void rainbow() {
	byte red = 0;
	byte green = 0;
	byte blue = 0;
	
	CRGB led_row[16];
	
	 fill_rainbow( &(leds[0]), 256 /*led count*/, 0 /*starting hue*/);
	 
	 FastLED.show();
	 
	/*
	// Copy ten led colors from leds[src .. src+9] to leds[dest .. dest+9]
  	//memmove( &leds[dest], &leds[src], 10 * sizeof( CRGB) )
  	for (int row = 0; row < 16; row++) { 
				if (row > 10) red = 0;
				if (row > 5) red = 255 - (row * 32);
				if (row <= 5) red = 96 + (row * 32);
								
				//green = 128 - row * 32;
				//blue = row * 32;
		
			for (int col = 0; col < 16; col++) {
				leds[row * 16 + col].setRGB(red, green, blue);
			}
		FastLED.show();
	}
	*/
	for (int iterations = 0; iterations < 32; iterations++)  {	
		memmove( &led_row[0], &leds[0], 16 * sizeof( CRGB) );	
		memmove( &leds[0], &leds[16], (255 - 16) * sizeof( CRGB) );
		memmove( &leds[256 - 16], &led_row[0], 16 * sizeof( CRGB) );
		LEDS.setBrightness(256 - ((iterations + 1) * 8));
		FastLED.show();
		delay(100);	
	}
	for (int n = 0; n < 256; n++) leds[n] = 0x000000;
	FastLED.show();
	LEDS.setBrightness(255);
	
	
}

void printWifiStatus() {
	// print the SSID of the network you're attached to:
	Serial.print(F("SSID: "));
	Serial.println(WiFi.SSID());

	// print your WiFi shield's IP address:
	IPAddress ip = WiFi.localIP();
	Serial.print(F("IP Address: "));
	Serial.println(ip);

	// print the received signal strength:
	long rssi = WiFi.RSSI();
	Serial.print(F("signal strength (RSSI):"));
	Serial.print(rssi);
	Serial.println(F(" dBm"));
}