/*
	This program has a simple mission: display anything sent to it over I2C/TWI on a 16x16 RGB led display
	This Arduino is I2C/TWI slave
	
	Some conventions in the code:
	uint8_t is the preferred unsigned byte datatype.byte and unsigned char are avoided 
	
	To get maximum speed (which we need), we must tweak the Wire-library in file hardware/libraries/Wire/utility/twi.h. 
		Near the top of the file you see :
		Code:
		#define TWI_FREQ 100000L
		...CHANGE TO:...
		#define TWI_FREQ 400000L

		(restart Arduino UI for effect)
		
	Also, set TWBR = 2 (which should have same effect as above change)
	
	About 50 frames / second should be the result at 16MHz, more than the 30fps we need to be fluid
	
*/
#include <FastLED.h>		// The main library to help us control the LEDs - much faster than Adafruit's
#include <Wire.h>			// To communicate with Arduino_WiFi

#define NUM_LEDS 256		// Total number of LEDs
#define COLOR_BYTES 3		// 3 bytes required per led for full color
#define DATA_PIN 6			// Pin on the Arduino used to communicate with LED display (digital 6)

#define BAUD_RATE 115200	// For logging

#define TWI_slave  42

CRGB leds[NUM_LEDS];		// FastLED class with .r .g and .b for each pixel - size: 3 bytes * NUM_LEDS
uint8_t command = ' ';		// the command character we get from serial/WiFi (' ' means unset)		

uint8_t *ptr;				// Pointer used to traverse 2D array leds[][]

void setup() {
	Wire.begin(TWI_slave);									// Join I2C/TWI bus as slave
	TWBR = 12;												// We need faster I2C/TWI...
	Wire.onReceive(receiveEvent);							// register receive event handler - not used but must be present 
	FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);	// setting up pin 6 and the array 'leds' to work with FastLED library
	boot_screen();											// showing boot screen to test connection
	
	Serial.begin(BAUD_RATE);								// initializing serial communication
	Serial.println(F("- SERIAL (I2C/TWI SLAVE) ARDUINO LIVE AGAIN!"));
	LEDS.setBrightness(128);	
}

void loop() { 
	
	while(Wire.available()) {	// we got data waiting for us
		command = Wire.read();
		
		switch (command) {	
			// 'G' is a special case, as in all other cases, the buffer is not really being used.
			// But for G, we now will get one screen-full of data, 3 bytes per LED = 768 bytes
			// However, to avoid RAM running out, we only do a quarter at a time
			case 'G':	// 'G' means we are receiving a full screen buffer to display
				{
				//Serial.println("Getting full screen buffer");	// GO code received - acknowledging
				uint8_t *ptr = (uint8_t *)&leds[0][0];			// pointer to CRGB array
				for (int led_number = 0; led_number < NUM_LEDS * COLOR_BYTES; led_number++) {
					while(!Wire.available()); 
					*ptr = Wire.read();
					ptr++;
					}				
				FastLED.show();					// Showing new LED values

				break;
				}
			case 'B':	// 'B' means we are receiving a new brightness value
				{
				Serial.println(F("Setting new brightness value"));	// Command code received - acknowledging
				while(!Wire.available()); 
				LEDS.setBrightness(Wire.read());
				FastLED.show();					// Showing new LED values
				Serial.println(F("Done"));							// Confirming effect Done
				break;
				}
			case 'T':	// 'T' means we are doing local tests of the pixels
				{
				Serial.println(F("Hardware test requested from master"));	// Command code received - acknowledging
				test_pixelrun();
				//rainbow();
				Serial.println(F("Hardware test complete"));							// Confirming effect Done
				break;
				}
			case 'Z':	// 'Z' means we are zeroing the LEDs (blanking the display)
				{
				Serial.println(F("Zeroing display"));	// Command code received - acknowledging
				memset(leds, 0,  NUM_LEDS * sizeof(struct CRGB));
				FastLED.show();
				Serial.println(F("Done"));							// Confirming effect Done
				break;
				}
			//default: // if nothing else matches, do this (for later)
		}
	}
}

// Empty request handler - as we take care of this manually and ignore the interrupt
void receiveEvent(int howMany) {}


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
	uint8_t red = 0;
	uint8_t green = 0;
	uint8_t blue = 0;

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
	uint8_t stripes = sqrt(NUM_LEDS);		// Finding number of rows/columns - NOTE: *assuming* square display
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
