/*
	LED_slave

	Arduino code to display anything sent to it over serial on a 16x16 RGB led display,
	and perform some basic functions based on control commands (screen blanking, dimming, test screens etc.)
	
	Some conventions in the code:
	uint8_t is the preferred unsigned byte data type. byte and unsigned char are avoided 
		
	About 50 frames / second should be the result at 16MHz, more than the 30fps we need to be fluid

	TODO: Once we got next release of FastLED (2.1?), include zigzag functionality fro library 		
*/


#include <FastLED.h>		// The main library to help us control the LEDs - much faster than Adafruit's
#include <MemoryFree.h>

#define NUM_LEDS 256		// Total number of LEDs
#define COLOR_BYTES 3		// 3 bytes required per led for full color
#define BUFFER_SIZE 768
#define DATA_PIN 6			// Pin on the Arduino used to communicate with LED display
							// For the status lights.
#define RED 0				// RED : no contact with Spark Core
#define ORANGE 1			// YELLOW: serial open
#define GREEN 2				// GREEN: serial connection established



#define BAUD_RATE0 115200	// For logging
#define BAUD_RATE1 230400	// For data - we should try 1'000'000 - supposed to work!
							// 400000 does work, but with some corruptions - possibly *not* due to serial?
							// TO solve corruption issue, try scaling back to 115200
							// OR, try 230400 which should be the sweet spot really (30fps)

CRGB leds[NUM_LEDS];		// FastLED class with .r .g and .b for each pixel - size: 3 bytes * NUM_LEDS
uint8_t command;			// the command character we get from serial/WiFi	

boolean firstRun = true;


void setup() {
	Serial.begin(BAUD_RATE0);								// initializing serial communication for debugging
	Serial.println(F("-> ARDUINO LEDSLAVE LIVE AGAIN!"));
	FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);	// setting up pin 6 and the array 'leds' to work with FastLED library
	Serial.println(F("-> FastLED library enabled"));
	Serial.println(F("-> Showing boot screen"));
	boot_screen();											// showing boot screen to show we're alive
	LEDS.setBrightness(128);
	traffic_light(RED);
	Serial1.begin(BAUD_RATE1);								// initializing serial communication for data
	Serial.println(F("-> Serial data communication enabled"));
	Serial.println(F("-> Running main loop"));
	traffic_light(ORANGE);
}

void loop() { 

	
	delay(10);

  	while(!Serial1.available());	// Wait here until we have serial traffic
	while(Serial1.read() != 0);		// Wait here until we receive a binary zero, which indicates command is coming
	while(!Serial1.available());	// Wait here until we have serial traffic
    command = Serial1.read();		// Read the actual command
    
    if(firstRun) {
		traffic_light(GREEN);
		firstRun = false;
		Serial.println(F("-> Serial contact with Spark Core established"));
		Serial.print(F("-> Command received: "));
		Serial.println(command);
		}
    /* DEBUG
    if (command > 65 && command < 90) {	// ASCII
    	Serial.print((char) command); 
    	} else {
    	Serial.print(command);
    		}
    		
    Serial.print(", "); */
	
	switch (command) {	
		case 'G':	// 'G' means we are receiving a full screen buffer to display
			{			  
			Serial1.write('A');	// GO code received - acknowledging
			int read_bytes = Serial1.readBytes( (char*)leds, BUFFER_SIZE);	// Full screen read
			FastLED.show();
			if (read_bytes != BUFFER_SIZE) {	// We didn't get right number of bytes
				Serial.print("Error, only got "); Serial.println(read_bytes); // Sending Error
			} else { Serial.println(">");}
			Serial1.write('D');	// Confirming full screen update
			
			break;
			}
		case 'B':	// 'B' means we are receiving a new brightness value
			{
			Serial1.write('A');	// Command code received - acknowledging
			while (!Serial1.available()) { }
			int bright = Serial1.read();
			if (bright > 0 && bright < 256) {
				Serial1.write('A');						// Brightness value received OK
				LEDS.setBrightness(bright);
				FastLED.show();							// Showing new LED values
				Serial1.write('D');						// Confirming effect Done
				Serial.print("New brightness: "); Serial.println(bright);
				
			} 	else { Serial1.write('E'); }				// Sending Error
			break;
			}
		case 'T':	// 'T' means we are doing local tests of the pixels
			{
			Serial1.write('A');	// Command code received - acknowledging
			//test_pixelrun();
			rainbow();
			Serial1.write('D');							// Confirming effect Done
			Serial.println("HW test complete");
			break;
			}
		case 'Z':	// 'Z' means we are zeroing the LEDs (blanking the display)
			{
			Serial1.write('A');	// Command code received - acknowledging
			memset(leds, 0,  NUM_LEDS * sizeof(struct CRGB));
			FastLED.show();
			Serial1.write('D');							// Confirming effect Done
			break;
			}
		case 'K':	// 'T' means keep-alive, we just ack it, nothing else
			{
			Serial1.write('A');	// Command code received - acknowledging
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
		delay(10);
	}
	
}
			
void fill_screen(CRGB color) {

	for (int n = 0; n < NUM_LEDS; n++)
		leds[n] = color;
	FastLED.show();
}

void traffic_light(uint8_t status) {
	if (status == RED) {
		for(uint8_t y = 0; y < 5; y++)
			for (uint8_t x = 6; x < 11; x++)
				leds[y*16 + x] = CRGB(255,0,0);
	}
	
	if (status == ORANGE) {
		for(uint8_t y = 6; y < 11; y++)
			for (uint8_t x = 6; x < 11; x++)
				leds[y*16 + x] = CRGB(255,165,0);
	}
				
	if (status == GREEN) {
		for(uint8_t y = 12; y < 16; y++)
			for (uint8_t x = 6; x < 11; x++)
				leds[y*16 + x] = CRGB(0,255,0);
	}
				
	FastLED.show();
}