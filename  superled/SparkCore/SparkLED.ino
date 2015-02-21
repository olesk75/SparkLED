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
#include <math.h>

#define NUM_LEDS 256
#define DATA_PIN 2

#define int_led D7

CRGB leds[NUM_LEDS];

TCPServer server = TCPServer(2208);
TCPClient client;
char myIpAddress[24];
bool connected;

uint8_t readBuffer[2];
int readStatus;

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
    
    client = server.available();
    
    if (client.connected()) {
        
        connected = true;
        
        // TODO: Check if we can get out of sync here, reading the two bytes backwards
        while ( readBuffer[0] != 0x00 ||    // where the first one is 0x00...
                readBuffer[1] != 'K') {     // and the second one is b'K'
            Spark.process();
            if (!connected) break;
            readStatus = readByte(&readBuffer[0], 2);
        }   
        
        if (connected) client.write('A'); // We ack connection and are ready to go
        
        
        while(connected) {
            
            while(true) {
                readStatus = readByte(&readBuffer[0], 2);           // we keep reading byte pairs until...
                
                if ((readBuffer[0] == 0x00 && readStatus == 2) || !connected) break;
                
            }

            if (!connected) break;      // if we've lost connection we break all the way back to root
            
            if (readBuffer[1] == 'G') {      // getting screen update ("Go code" - \x00G)
                client.write('A'); // We ack connection
                
            
                uint8_t *ptr = &leds[0][0];
                
                for (uint16_t pixel = 0; pixel < 768; pixel++) {
                    do {
                        readStatus = readByte((uint8_t *) ptr++, 1);
                    } while (readStatus == 0 && connected);
                    
                    if(!connected) break;
                }
                
                FastLED.show();
                client.write('D'); // We tell the client we are Done
            } 
            
            if (readBuffer[1] == 'T') {   // Hardware test pattern
                boot_screen();
                if (connected) client.write('D'); // We tell the client we are Done
            } 
            
            if (readBuffer[1] == 'B') {   // Set brightness (0-225)
                uint8_t brightness;
                
                readByte(&brightness, 1);
                LEDS.setBrightness(brightness);
                if (connected) client.write('D'); // We tell the client we are Done
            }
        }
    }
}



/* 
    Reads a byte from the network client socket
*/
int readByte(uint8_t *destination, int bytesRead) {
    long startTime = millis();
    while(!client.available() && millis() - startTime < 1000) 
        Spark.process();
    
    int statusCode = client.read((uint8_t *) destination, bytesRead);
                
    if (statusCode ==  -1) {        // client disconnected
        no_connetion_warning();
        client.flush();
        client.stop();
        connected = false;
        Spark.process();
        
    }
    return(statusCode);
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

/*
    Gets complicated by the fact that we have a zig-zag pattern, so we need to flip every second line
*/
void no_connetion_warning() {
    
    uint16_t img_no_link[16] = {
        0x1cF0, 0x1290, 0x1290, 0x1290, 0x12F0, 0x0000, 0x85C9, 0x852A, 0x852C, 0x852A, 0xF529, 0x0000, 0x0240, 0xFE7F, 0x0240, 0x0000
        };
        
    for (uint8_t line = 0; line < 16; line++ ){
        
        if ( (line % 2) != 0) {    // every odd line...
            img_no_link[line] = reverseBits(img_no_link[line]);
        }
        
        for (uint8_t horis_led = 0; horis_led < 16; horis_led++) {
            
            if (img_no_link[line] & (uint16_t) pow(2, 15 - horis_led)) {
                leds[(line * 16) + horis_led].red = 255;
            } else {
                leds[(line * 16) + horis_led].red = 0;
            }  
            
            leds[(line * 16) + horis_led].green = 0;
            leds[(line * 16) + horis_led].blue = 0;
        }
        
    }
        
    
    FastLED.show();
}

/* Function to reverse bits of num */
uint16_t reverseBits(uint16_t num)
{
    uint8_t  NO_OF_BITS = sizeof(num) * 8;
    uint16_t reverse_num = 0, temp;
 
    for (uint8_t i = 0; i < NO_OF_BITS; i++)
    {
        temp = (num & (1 << i));
        if(temp)
            reverse_num |= (1 << ((NO_OF_BITS - 1) - i));
    }
  
    return reverse_num;
}