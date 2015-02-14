// This #include statement was automatically added by the Spark IDE.
#include "FastLED/FastLED.h"
FASTLED_USING_NAMESPACE

#include "application.h"

#define NUM_LEDS 256
#define DATA_PIN D2

#define int_led D7

CRGB leds[NUM_LEDS];

TCPServer server = TCPServer(2208);
TCPClient client;
char myIpAddress[24];

void setup()
{

    FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
    LEDS.setBrightness(128);

    pinMode(int_led, OUTPUT);
    digitalWrite(int_led, LOW);

    server.begin();

    Spark.variable("localIP", myIpAddress, STRING);
    IPAddress myIp = WiFi.localIP();
    sprintf(myIpAddress, "%d.%d.%d.%d", myIp[0], myIp[1], myIp[2], myIp[3]);

}


void loop()
{

    digitalWrite(int_led, LOW);     // Internal led OFF to verify visually

    client = server.available();

    if (client.connected()) {
        digitalWrite(int_led, HIGH);     // Internal led ON to verify visually

        while(client.read() != 0x00 && client.read() != 'K') Spark.process();   // EXPERIMENTAL: We do this to ensure that we remain connected to the cloud
        client.write('A'); // We ack connection and are ready to go


        while(client.connected()) {
            while (client.read() != 0x00) Spark.process();      // It is possible that this will slow things down too much. In which case we need to drop it and
                                                                // possibly live with a lost cloud conection. For re-flashing we need to reset the Spark Core

            uint8_t code = client.read();

            if (code == 'G') {      // getting screen update ("Go code" - \x00G)
                client.write('A'); // We ack connection

                for (uint16_t pixel = 0; pixel < 255; pixel++)
                    {
                        while (client.available() < 3) Spark.process(); // We need at least 3 bytes read to fill RGB for a single pixel

                        client.read(&leds[pixel][0] , 3); // Reading 3 bytes directly into struct
                    }

                FastLED.show();
                client.write('D'); // We tell the client we are Done
                //
            } else if (code == 'T') {
                // Hardware test pattern

            }
        }
    }
}
