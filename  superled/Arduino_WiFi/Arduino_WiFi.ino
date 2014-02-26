/*
	Arduino_WiFi
	This program has a simple mission: transfer anything sent to it over WiFi to Arduino connected to the LED via SPI and reverse.
	This Arduino is WiFi server and SPI master
	
*/
#include <Adafruit_CC3000.h>
//#include "utility/debug.h"
#include "utility/socket.h"
#include <SPI.h>
#include "pins_arduino.h"	// Mostly just for readability


#define NUM_LEDS 256					// yeah, we got a LOT
#define COLOR_BYTES 3					// 3 bytes required per led for full color
#define BUFFER_SIZE 786					// NUM_LED * COLOR_BYTES
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

Adafruit_CC3000 cc3000 = Adafruit_CC3000(ADAFRUIT_CC3000_CS, ADAFRUIT_CC3000_IRQ, ADAFRUIT_CC3000_VBAT, SPI_CLOCK_DIVIDER); // you can change the clock speed

Adafruit_CC3000_Server LEDServer(LISTEN_PORT);	// Defining the server

void setup() { 
	FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);	// setting up pin 6 and the array 'leds' to work with FastLED library
	
	Serial.begin(BAUD_RATE);	// Initializing serial communication
	
	Serial.println(F("- WIFI ARDUINO (SPI MASTER) LIVE AGAIN!"));
	//Serial.print(F("Free RAM: "));
	//Serial.print(getFreeRam(), DEC);
	//Serial.println(F("B"));

	Serial.println(F("\nInitializing WiFI shield ---> "));
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
}


/* 	I am making one huge assumption here: the Adafruit CC3000 library initializes SPI properly with this Arduino as master.
	If not, it won't work.... ;)
*/

// Main loop, where we get our values form serial and display it
void loop() { 
	//delay(100);
	Adafruit_CC3000_ClientRef client = LEDServer.available();		// check if we have any connected clients - loops until we have a client
	if (client) {
		Serial.println(F("We have a new client"));
		client.write('S'); 	// Sending single byte ('S') to indicate start of communications
		if (client.available() > 0) {
		
			uint8_t command = client.read();	// reads single byte from client
			
			digitalWrite(SS, LOW);    			// SS is pin 10, which is connected to pin 10 on Arduino_Serial
  
			// send test string
			//for (const char * p = "Fab" ; c = *p; p++)
			SPI.transfer(command);

			// disable Slave Select
			digitalWrite(SS, HIGH);				// SS is pin 10, which is connected to pin 10 on Arduino_Serial
			
			//time = millis();	// we reset the timer as we have activity
			Serial.println(F("Command received: "));
			Serial.println(command);

		} else {
		// DEBUGGING
		delay(1000);
		digitalWrite(SS, LOW);
		SPI.transfer('A');
		digitalWrite(SS, HIGH);
	}
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

