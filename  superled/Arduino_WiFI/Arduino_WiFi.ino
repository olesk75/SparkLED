/*
	This program has a simple mission: display anything sent to it over the serial line on a 16x16 RGB led display
	Note that the rows zigzag, going from left to right, right to left, left to right etc.
	
*/
#include <Adafruit_CC3000.h>
//#include "utility/debug.h"
#include "utility/socket.h"
#include <FastLED.h>
#include <SPI.h>

#define NUM_LEDS 256					// yeah, we got a LOT
#define COLOR_BYTES 3					// 3 bytes required per led for full color
#define BUFFER_SIZE 786					// NUM_LED * COLOR_BYTES
#define DATA_PIN 6						// remember to verify before powering LED array
 #define BAUD_RATE 115200				// We no longer use serial for communication with client, only for error reporting
 
#define WLAN_SSID	"ShadowNETz"
#define WLAN_PASS	"********"

#define WLAN_SECURITY   WLAN_SEC_WPA2	// Security can be WLAN_SEC_UNSEC, WLAN_SEC_WEP, WLAN_SEC_WPA or WLAN_SEC_WPA2
#define LISTEN_PORT 2208				// What TCP port to listen on for connections.


// These are the interrupt and control pins
#define ADAFRUIT_CC3000_IRQ   3  		// MUST be an interrupt pin!
#define ADAFRUIT_CC3000_VBAT  5			// These can be any two pins
#define ADAFRUIT_CC3000_CS    10		// These can be any two pins
// Use hardware SPI for the remaining pins - on an UNO, SCK = 13, MISO = 12, and MOSI = 11

#define SPI_CLOCK_DIVIDER 2

Adafruit_CC3000 cc3000 = Adafruit_CC3000(ADAFRUIT_CC3000_CS, ADAFRUIT_CC3000_IRQ, ADAFRUIT_CC3000_VBAT, SPI_CLOCK_DIVIDER); // you can change the clock speed
CRGB leds[NUM_LEDS];					// the 256 led (786B) array - NOTE: 3 bytes per index

Adafruit_CC3000_Server LEDServer(LISTEN_PORT);	// Defining the server

void setup() { 
	FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);	// setting up pin 6 and the array 'leds' to work with FastLED library
	
	Serial.begin(BAUD_RATE);	// Initializing serial communication
	

	LEDS.setBrightness(16);		// maximum brightness

	Serial.println(F("- I LIVE AGAIN!"));
	//Serial.print(F("Free RAM: "));
	//Serial.print(getFreeRam(), DEC);
	//Serial.println(F("B"));

	Serial.println(F("\nInitializing WiFI shield ---> "));
	fill_screen(CRGB::Red);
	if (!cc3000.begin()) {
		Serial.println(F("Couldn't begin()! Check your wiring?"));
		while(1);
	}

	if (!cc3000.connectToAP(WLAN_SSID, WLAN_PASS, WLAN_SECURITY)) {
		Serial.println(F("Failed!"));
		while(1);
	}

	Serial.println(F("Connected!"));

	Serial.println(F("Request DHCP"));
	while (!cc3000.checkDHCP()) {
		delay(100); // ToDo: Insert a DHCP timeout!
	}  

	/* Display the IP address DNS, Gateway, etc. */  
	while (! displayConnectionDetails()) {
		delay(1000);
	}
	
	LEDServer.begin();	// Starting the server

	Serial.println("Server ready...");
	fill_screen(CRGB::Orange);
}


// Main loop, where we get our values form serial and display it
void loop() { 
	//delay(100);
	Adafruit_CC3000_ClientRef client = LEDServer.available();		// check if we have any connected clients - loops until we have a client
	if (client) {
		fill_screen(CRGB::Green);
		Serial.println(F("We have a new client"));
		client.write('S'); 	// Sending single byte ('S') to indicate start of communications
		//time = millis();	// Starting timer

		//if (millis() > time + 10000) break;	// we reset the connection if 10 seconds idle
		if (client.available() > 0) {
		
			uint8_t command = client.read();	// reads single byte from client
			
			//time = millis();	// we reset the timer as we have activity
			Serial.println(F("Command received: "));
			Serial.println(command);
  
			switch (command) {
				case 'G':	// 'G' means we are receiving a full screen buffer
					{		  
					client.write('A');	// GO code received - acknowledging
					Serial.println(F("- Command G received (full screen update), sending A back to client"));
					while(!client.available()) {}	// we need to wait for data available to read, or will get -1
					
					//client.read((char *)leds, NUM_LEDS * COLOR_BYTES,0);
					// Read definition: read(void *buf, uint16_t len, uint32_t flags = 0);
					// If it doesn't work, we need a loop, like so:
					for (int led = 0; led < NUM_LEDS; led++) {
						while(!client.available()) {Serial.print(F("- Ran out of data at position")); Serial.println(led * 3 + 0);}
						leds[led].r = client.read();
						while(!client.available()) {Serial.print(F("- Ran out of data at position")); Serial.println(led * 3 + 1);}
						leds[led].g = client.read();
						while(!client.available()) {Serial.print(F("- Ran out of data at position")); Serial.println(led * 3 + 2);}
						leds[led].b = client.read();
					}	// NOTE: SLOW AS HELL. DO WE REALLY NEED TO VERIFY EVERY SINGLE BYTE TRANSFERRED? START WITH THIS AND OPTIMIZE TO BREAKING POINT!
					
					
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
					byte readByte = client.read();
		
					int brightness = int(readByte);
											
					if (brightness > 0 && brightness < 256) {
						client.write('A');					// Brightness value received OK
						LEDS.setBrightness(brightness);
						FastLED.show();
						client.write('D');					// effect done
						Serial.println(F("Effect done - sending D back to client"));
						
					} 	else { 	// sending Error
						client.write('E'); 
						Serial.println(F("Effect ERROR - sending E back to client"));
						}
					break;
					}
				case 'T':	// 'T' means we are doing local tests of the pixels
					{
					client.write('A');	// Command code received - acknowledging
					Serial.println(F("Command T received (local test), sending A back to client"));
					test_pixelrun();
					//rainbow();
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


/**************************************************************************/
/*!
    @brief  Tries to read the IP address and other connection details
*/
/**************************************************************************/
bool displayConnectionDetails(void)
{
  uint32_t ipAddress, netmask, gateway, dhcpserv, dnsserv;
  
  if(!cc3000.getIPAddress(&ipAddress, &netmask, &gateway, &dhcpserv, &dnsserv))
  {
    Serial.println(F("Unable to retrieve the IP Address!\r\n"));
    return false;
  }
  else
  {
    Serial.print(F("\nIP Addr: ")); cc3000.printIPdotsRev(ipAddress);
    Serial.print(F("\nNetmask: ")); cc3000.printIPdotsRev(netmask);
    Serial.print(F("\nGateway: ")); cc3000.printIPdotsRev(gateway);
    Serial.print(F("\nDHCPsrv: ")); cc3000.printIPdotsRev(dhcpserv);
    Serial.print(F("\nDNSserv: ")); cc3000.printIPdotsRev(dnsserv);
    Serial.println();
    return true;
  }
}

void fill_screen(CRGB color) {

	for (int n = 0; n < NUM_LEDS; n++)
		leds[n] = color;
	FastLED.show();
}
