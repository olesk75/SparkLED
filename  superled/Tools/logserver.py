#!/usr/bin/env python3
"""     Python3 program which listens to sensor information over the network as port 2208.
		The purpose of this server is to collect data and serve queries from other clients.

		In the SuperLED project, this acts as a "syslog" server, listening for and recording
		data from sensors (access control, temperature, lights, heating etc.). SuperLED.py will
		query this server to see if there is anything it should put on the LED display. An
		example would be the image of a bell if someone rings the doorbell.

		Message format for sensors and other who want to log data:
		sensorname:level:value  (level is LOGLEVEL, normally info)

		Message format for clients who want to read data:
		req:sensorname  <- get last reading from sensor

		Message format for clients who want to check for priority messages:
		pri             <- pop last priority message from priority stack
"""
import logging
import socket
import sys
import signal

HOST = ''       # Symbolic name meaning all available interfaces
PORT = 2208     # Arbitrary non-privileged port
MAX_CONN = 10   # Maximum simultaneous connections

priority = []

# noinspection PyUnusedLocal,PyUnusedLocal,PyShadowingNames
def signal_handler(signal, frame):
	print('\n- Interrupted manually, aborting')
	logger.critical('Abort received, shutting down')
	server.shutdown()
	server.close()
	exit(1)


if __name__ == "__main__":  # Making sure we don't have problems if importing from this file as a module

	logging.basicConfig(level=logging.DEBUG,      # The lowest log level that will be printed to STDOUT (DEBUG < INFO <WARN < ERROR < CRITICAL)
	                    format='%(asctime)s:%(message)s',
	                    datefmt='%d%m%y:%H%M%S',
	                    filename='sensors.log')

	#logger = logging.getLogger(__name__)
	logger = logging.getLogger('msg_logger')

	signal.signal(signal.SIGINT, signal_handler)  # Setting up th signal handler to arrange tidy exit if manually interrupted

	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	print('Socket created')

	try:
		server.bind((HOST, PORT))
	except socket.error:
		print('Bind failed')
		sys.exit()

	print('Socket bind complete')

	server.listen(MAX_CONN)
	print('Socket now listening on port ' + str(PORT))

	while True:
		#wait to accept a connection - blocking call
		conn, addr = server.accept()
		#logger.debug('Connected with ' + addr[0] + ':' + str(addr[1]))
		data, client_address = conn.recvfrom(1024)
		data = data.decode()        # Converting from bytearray to string
		data = data.split(':')      # Converting string to list of strings, split by colon
		if data[0] == 'req':        # Information request
			sensor = data[1]

		else:                       # Data logging
			[sensor, level, value] = data
			logger.info(addr[0] + ':' + sensor + ':' + level + ':' + value)     # We log the info
			reply = 'ack ==> ' + sensor + ':' + level + ':' + value             # We confirm message, allowing the client to resend if it doesn't agree
			if level == 'CRIT': priority.append(sensor + ':' + level + ':' + value)
			conn.send(bytes(reply.encode(encoding='utf8')))        # sendall doesn't understand unicode strings (Python3 default strings) without encoding

		conn.close()