/*
	Arduino_WiFi
	This program has a simple mission: transfer anything sent to it over WiFi to Arduino connected to the LED via SPI and reverse.
	This Arduino is WiFi server and SPI master (TWBR: 12 == 400 KHz)

	
	IMPORTANT NOTE TO SELF: When using the 5V regulated PSU, connect to Arduino 5V pin and NOT vin!
*/
#include <Adafruit_CC3000.h>
#include "utility/socket.h"
#include <Wire.h>

#include <SPI.h>
#include "pins_arduino.h"				// Mostly just for readability


#define NUM_LEDS 256					// yeah, we got a LOT
#define COLOR_BYTES 3					// 3 bytes required per led for full color
#define BUFFER_SIZE 786					// NUM_LED * COLOR_BYTES - we need speed so we remove the need for arithmetic in loops

#define TWI_slave  42
 
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
	Serial.begin(115200);		// Initializing serial communication
	Wire.begin();				// Joins the I2C/TWI bus. Master doesn't need address
	TWBR = 12; 					// 400KHz I2C/TWI - fastest we can go without messing up the WiFi shield
	
	Serial.println(F("- WIFI ARDUINO (I2C/TWI MASTER) LIVE AGAIN!"));

	wifiSetup();
	LEDServer.begin();	// Starting the server
	Serial.println("Server ready...");
}


/* 	I am making one huge assumption here: the Adafruit CC3000 library initializes SPI properly with this Arduino as master.
	If not, it won't work.... ;)
*/

// Main loop, where we get our values form serial and display it
void loop() { 	

	Adafruit_CC3000_ClientRef client = LEDServer.available();
	
	if(client) {	
		Serial.println(F("We have a new client"));
		client.write('S'); 	// Sending single byte ('S') to indicate start of communications
	}
	while (client) {

		if (client.available() > 0) {
			uint8_t command = client.read();	// reads single byte from client
			
			Serial.println(F("Command received: "));
			Serial.println(command);
			
			writeSlave(command);				// we pass on the byte to Arduino_Serial
			
			// Here we deal with commands that require more data to follow
			if (command == 'G') {				// this is the tricky part, as we will now get a NUM_LEDS * COLOR_BYTES buffer
				for (int counter = 0; counter < BUFFER_SIZE; counter++) {
					while(!client.available()) {};	// we wait for the brightness value
					writeSlave(client.read());		// we send brightness value directly to Arduino_Serial
				}
				Serial.println(F("Full buffer received and sent"));
				
			} else if (command == 'B') {
				while(!client.available()) {};	// we wait for the brightness value NOTE: do we need this?
				writeSlave(client.read());		// we send brightness value directly to Arduino_Serial
				Serial.println(F("New brightness value received and sent"));
			}
		}
	} 
}

void writeSlave(uint8_t sendbyte) {
	Wire.beginTransmission(TWI_slave);	// transmit to device #4
	Wire.write(sendbyte);			// put single byte in send buffer
	switch (Wire.endTransmission()) {	// transmit buffer
		case 0: return;		// success
		case 1: Serial.println(F("data too long to fit in transmit buffer")); break;
		case 2: Serial.println(F("received NACK on transmit of address")); break;
		case 3: Serial.println(F("received NACK on transmit of data")); break;
		case 4: Serial.println(F("unknown error")); break;
	}
	//Serial.print(F("Wrote '")); Serial.print(sendbyte); Serial.println(F("' to slave"));
}

void writeSlaveBuffer(uint8_t buffer[]) {
	for (uint8_t counter = 0; counter < 12; counter++) {	// We need to split it in 64 byte portions (256 * 3 / 64 = 12)
		Wire.beginTransmission(TWI_slave);	// transmit to device #4
		Wire.write(&buffer[counter * 64], 64);
		Wire.endTransmission(); 
	}	
}


/*
	Basic setup of WiFi
*/
void wifiSetup() {
	Serial.println(F("\nInitializing WiFI shield..."));
	if (!cc3000.begin()) {
		Serial.println(F("Couldn't begin()! Check your wiring?"));
		while(1);
	}

	if (!cc3000.connectToAP(WLAN_SSID, WLAN_PASS, WLAN_SECURITY)) {
		Serial.println(F("Failed!"));
		while(1);
	}

	Serial.println(F("Connected!"));

	Serial.print(F("Requesting DHCP..."));
	while (!cc3000.checkDHCP()) {
		delay(100); // ToDo: Insert a DHCP timeout!
	} 
	Serial.println(F("done!"));

	/* Display the IP address DNS, Gateway, etc. */  
	while (! displayConnectionDetails()) {
		delay(1000);
	}
}

/*
	Tries to read the IP address and other connection details
*/
bool displayConnectionDetails(void) {
  uint32_t ipAddress, netmask, gateway, dhcpserv, dnsserv;
  
  if(!cc3000.getIPAddress(&ipAddress, &netmask, &gateway, &dhcpserv, &dnsserv)) {
    Serial.println(F("Unable to retrieve the IP Address!\r\n"));
    return false;
  }
  else {
    Serial.print(F("\nIP Addr: ")); cc3000.printIPdotsRev(ipAddress);
    Serial.print(F("\nNetmask: ")); cc3000.printIPdotsRev(netmask);
    Serial.print(F("\nGateway: ")); cc3000.printIPdotsRev(gateway);
    Serial.print(F("\nDHCPsrv: ")); cc3000.printIPdotsRev(dhcpserv);
    Serial.print(F("\nDNSserv: ")); cc3000.printIPdotsRev(dnsserv);
    Serial.println();
    return true;
  }
}