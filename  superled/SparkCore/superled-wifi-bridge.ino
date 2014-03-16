/*
	SuperLED WiFi Bridge (Spark Core)
	This program has a simple mission: transfer anything sent to it over WiFi to Arduino connected to the LED via SPI and reverse.
	This Arduino is WiFi server and SPI master (TWBR: 12 == 400 KHz)

	
	IMPORTANT NOTE TO SELF: When using the 5V regulated PSU, connect to Arduino 5V pin and NOT vin!
*/

#define COLOR_BYTES 3					// 3 bytes required per led for full color
#define BUFFER_SIZE 768					// NUM_LED * COLOR_BYTES - we need speed so we remove the need for arithmetic in loops
#define WLAN_SSID	"ShadowNETz"
#define WLAN_PASS	"xxxxx"
#define BAUD_RATE0 115200               // Debug serial baud rate
#define BAUD_RATE1 400000               // Data serial baud rate
#define LISTEN_PORT 2208				// What TCP port to listen on for connections.

uint8_t screenBuffer[BUFFER_SIZE];      // The byte buffer - one full screen
uint8_t command;                        // The command we get from the python client
char myIpString[24];                    // IP-adresse of Spark Core

TCPServer LEDserver = TCPServer(LISTEN_PORT);
TCPClient client;


void setup() {
    pinMode(7, OUTPUT); // onboard led
    digitalWrite(7, HIGH);
    delay(3000);    // experience shows that this is helpful to make sure we can re-flash the core
    digitalWrite(7, LOW);
    
    // Sends the IP address of the Spar Core to the cloud. Can be retrieved manually with :
	// curl "https://api.spark.io/v1/devices/48ff74065067555037201287/ipAddress?access_token=xxxxxxx"
    IPAddress myIp = Network.localIP();
    sprintf(myIpString, "%d.%d.%d.%d", myIp[0], myIp[1], myIp[2], myIp[3]);
    Spark.variable("ipAddress", myIpString, STRING);

	Serial.begin(BAUD_RATE0);		// Initializing serial communication
	//while(!Serial.available()) {delay(100);} // Wait here until the user presses something in the Serial Terminal, for debugging

	Serial.println("- WIFI SPARK CORE LED MASTER LIVE AGAIN!");
	Serial1.begin(BAUD_RATE1);		// 
    Serial.println("--> Started serial communications, establishning connection to LEDslave");
    while(true) {   // We keep bombarding LEDslave with keepalives until we get an ack -> ready to go
        Serial1.write(0);   // sending 0 (not "0" but binary zero) to indicate command incoming
        delay(100); 
        Serial1.write('K'); // sending keepalive to get ack from LEDslave (ASCII 75 = 'K')
        delay(1000);        // we wait a second between each one
        if(Serial1.read() == 'A') break;
    }
    digitalWrite(7, HIGH);
    
    Serial.println("--> LEDslave acknowledges - serial data connection ready");

	LEDserver.begin();	// Starting the server
	Serial.print("--> Server ready at ");
	Serial.print(Network.localIP());
	Serial.print(" port: ");
	Serial.println(LISTEN_PORT);
	digitalWrite(7, LOW);
}




// Main loop, where we get our values form serial and display it
void loop() {


    client = LEDserver.available();
    
	if(client) {
	    digitalWrite(7, HIGH);
		Serial.println("--> We have a new client");
		client.write('S'); 	// Sending single byte ('S') to indicate start of communications
	}
	while (client) {
		if (client.available() > 0) {
			uint8_t command = client.read();	// reads single byte from client

			// Here we deal with commands that require more data to follow
			if (command == 'G') {
			    Serial1.write(0);                           // letting the Arduino know a command is coming
			    Serial1.write(command);	                   	// we pass on the one byte command to Arduino
			    while (Serial1.read() != 'A');              // wait for ack

				// slow version, to make sure we don't have buffer overruns
				for (int i=0; i < BUFFER_SIZE; i++) {
				    screenBuffer[i] = client.read();
				}
				
				Serial1.write(&screenBuffer[0], BUFFER_SIZE / 2);
                Serial1.write(&screenBuffer[BUFFER_SIZE / 2], BUFFER_SIZE / 2);
				while (Serial1.read() != 'D');
				    client.write('D');      // we let the client know we're done
				Serial.println("--> Full buffer received and sent");
				
			} else if (command == 'B') {
			    Serial1.write(0);                           // letting the Arduino know a command is coming
			    Serial1.write(command);	                   	// we pass on the one byte command to Arduino
			    
			    while (Serial1.read() != 'A');              // wait for ack
				while(!client.available()) {};	// we wait for the brightness value NOTE: do we need this?
				Serial1.write(client.read());		// we send brightness value directly to Arduino_Serial
				Serial.println("--> New brightness value received and sent");
				while (Serial1.read() != 'D');
				    client.write('D');      // we let the client know we're done
				
			} else if (command == 'T') {
			    Serial1.write(0);                           // letting the Arduino know a command is coming
			    Serial1.write(command);	                   	// we pass on the one byte command to Arduino
			    
			    while (Serial1.read() != 'A');              // wait for ack
				Serial.println("--> HW test received and sent");
				while (Serial1.read() != 'D');
				    client.write('D');      // we let the client know we're done
				    
			} else if (command == 'K') {    // Keep-alive from Python client. We respond to show we're alive.
				    client.write('D'); 
				
			} else if (command == 'Q') {
				client.stop();                              // Disconnecting the network client
				Serial1.write(0);                           // letting the Arduino know a command is coming
			    Serial1.write('Z');	                   	    // we zero the display when network client disconnects
			    while (Serial1.read() != 'A');              // wait for ack
				Serial.println("--> Display zeroed");
				while (Serial1.read() != 'D');              // await for "done" from Arduino
				digitalWrite(7, LOW);
			}
		}
	} 
}
