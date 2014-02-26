/*
	This program has a simple mission: display anything sent to it over the serial line on a 16x16 RGB led display
	Note that the rows zigzag, going from left to right, right to left, left to right etc.

*/
#include <FastLED.h>		// The main library to help us control the LEDs - much faster than Adafruit's
#define NUM_LEDS 256		// Total number of LEDs
#define COLOR_BYTES 3		// 3 bytes required per led for full color
#define DATA_PIN 6			// Pin on the Arduino used to communicate with LED display
#define ledPin 13			// On-board LED for Arduino UNO - used for debugging mostly - not required

#define BAUD_RATE 400000	// Trial and error maximum

CRGB leds[NUM_LEDS];		// FastLED class with .r .g and .b for each pixel - size: 3 bytes * NUM_LEDS
char command;				// the command character we get from serial/WiFi		


void setup() { 
	FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);	// setting up pin 6 and the array 'leds' to work with FastLED library
	
	boot_screen();					// Showing boot screen to test connection
	
	Serial.begin(BAUD_RATE);		// Initializing serial communication
	
	Serial.write('S');				// Writing 'S' to indicate start of communications
	while (Serial.read() != 'G') {}	// Waiting for 'G' to continue
	LEDS.setBrightness(128);	
	Serial.write('A');				// Acknowledging with 'A'
	
}

void loop() { 
	char command = Serial.read();	// Each iteration we check for a command

	switch (command) {
	
		case 'G':	// 'G' means we are receiving a full screen buffer to display
			{		  
			Serial.write('A');	// GO code received - acknowledging
			int read_bytes = Serial.readBytes( (char*)leds, NUM_LEDS * COLOR_BYTES);	// Full screen read
		
			if (read_bytes != NUM_LEDS * COLOR_BYTES) {	// We didn't get right number of bytes
				Serial.write('E');						// Sending Error
			} else {
				Serial.write('R');						// Sending Received
				FastLED.show();							// Showing new LED values
				}
			}	  
			break;
		case 'B':	// 'B' means we are receiving a new brightness value
			{
			Serial.write('A');	// Command code received - acknowledging
			while (Serial.available() == 0) { }
			int bright = Serial.read();
			if (bright > 0 && bright < 256) {
				Serial.write('A');						// Brightness value received OK
				LEDS.setBrightness(bright);
				FastLED.show();							// Showing new LED values
				Serial.write('D');						// Confirming effect Done
				
			} 	else { Serial.write('E'); }				// Sending Error
			break;
			}
		case 'T':	// 'T' means we are doing local tests of the pixels
			{
			Serial.write('A');	// Command code received - acknowledging
			//test_pixelrun();
			rainbow();
			Serial.write('D');							// Confirming effect Done
			break;
			}
		case 'Z':	// 'Z' means we are zeroing the LEDs (blanking the display)
			{
			Serial.write('A');	// Command code received - acknowledging
			memset(leds, 0,  NUM_LEDS * sizeof(struct CRGB));
			FastLED.show();
			Serial.write('D');							// Confirming effect Done
			break;
			}
		//default: // if nothing else matches, do this (for later)
	}
}

/*
	Fades all the pixels to zero, step by step
*/
void fader() {
	int brightness = LEDS.getBrightness();

	for (int fade = 0; brightness - fade > 0; fade+=2) {
		LEDS.setBrightness(brightness - fade);
		delay(10);
		FastLED.show();

	}
}

/*
	Sends a pixel "running" down the display
*/
void test_pixelrun() {

	for(int dot = 0; dot < NUM_LEDS; dot++) {
		leds[dot] = CRGB::Blue;
		FastLED.show();
		leds[dot] = CRGB::Black;
	}
	FastLED.show();		// Showing the last pixel before returning

}

/*
	Shows a rainbow pattern
*/
void rainbow() {
	byte red = 0;
	byte green = 0;
	byte blue = 0;

	CRGB led_row[16];

	fill_rainbow( &(leds[0]), NUM_LEDS /*led count*/, 0 /*starting hue*/);
	LEDS.setBrightness(255);
	FastLED.show();
	
	for (int iterations = 0; iterations < 32; iterations++)  {
		memmove( &led_row[0], &leds[0], 16 * sizeof( CRGB) );
		memmove( &leds[0], &leds[16], (255 - 16) * sizeof( CRGB) );
		memmove( &leds[256 - 16], &led_row[0], 16 * sizeof( CRGB) );
		LEDS.setBrightness(256 - ((iterations + 1) * 8));
		FastLED.show();
		delay(50);
	}
	for (int n = 0; n < NUM_LEDS; n++) leds[n] = 0x000000;
	FastLED.show();

}

/*
	Boot screen - shows a sweeping line from left to right
*/
void boot_screen() {
	int real_x;
	int multiplier;
	char stripes = sqrt(NUM_LEDS);		// Finding number of rows/columns - NOTE: *assuming* square display
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
		delay(20);
	}
	
}
			
void fill_screen(CRGB color) {

	for (int n = 0; n < NUM_LEDS; n++)
		leds[n] = color;
	FastLED.show();
}
