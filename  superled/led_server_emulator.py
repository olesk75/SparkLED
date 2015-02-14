#!/usr/bin/env python3
# __author__ = 'olesk'
import pygame, sys
from pygame.locals import *
import socket
from pygame.locals import *
import time

WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
BLUE = (0, 0, 128)

TCP_IP = '127.0.0.1'
TCP_PORT = 2208
BUFFER_SIZE = 1024  # Normally 1024, but we want fast response

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # Important to not block sockets in Windows
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

displayUpdates = 0
start = time.clock()    # resetting timer
#print ('Connection from:', addr)


pygame.init()

DISPLAYSURF = pygame.display.set_mode((16*50, 16*50))
pygame.display.set_caption('LED Server Emulator')
#fontObj = pygame.font.Font('freesansbold.ttf', 32)

print("Listening for connections - no timeout")
conn, addr = s.accept()
s.settimeout(2)
while True: # main game loop

    while True:
        try:
            data = conn.recv(BUFFER_SIZE)
            break
        except socket.error as e:
            err = e.args[0]
            # this next if/else is a bit redundant, but illustrates how the
            # timeout exception is setup
            print("Error: ", err)
            print("Listening for connections - no timeout")
            s.settimeout(60*60)     # 1 hour timeout
            conn, addr = s.accept()
            s.settimeout(2)
            displayUpdates = 0      # resetting counter

    #if not data: break
    if data == b'\x00K':
        print("Received proper connection request (b'\\x00K')", end='')
        conn.send(b'A')
        print(" <= ACK sent\n\n")

    elif data == b'\x00G':
        #print("Received proper go! code (b'\\x00G')", end='')
        conn.send(b'A')
        #print(" <= ACK sent back to client - ready to receive screen update")

        try:
            data = conn.recv(BUFFER_SIZE)
        except socket.error as e:
            err = e.args[0]
            # this next if/else is a bit redundant, but illustrates how the
            # timeout exception is setup
            print("Error: ", err)
            print("Listening for connections - no timeout")
            s.settimeout(60*60)     # 1 hour timeout
            conn, addr = s.accept()
            s.settimeout(2)
            displayUpdates = 0      # resetting counter


        if len(data) == 768:
            #print("Got full screen update (768) bytes)", end='')

            x = 0
            y = 0
            for n in range(0, 768, 3):
                for event in pygame.event.get(): pass

                pygame.draw.rect(DISPLAYSURF, (data[n], data[n + 1] ,data[n + 2]), (x * 50, y * 50, 50, 50))   # (x,y, width, height)
                x += 1
                if x == 16:
                    x = 0
                    y += 1

            pygame.display.update()
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    s.close()
                    sys.exit()

            conn.send(b'D')     # We are Done!
            #print(" <= ACK ('D') ready for next")
            fps = int(1 / (time.clock() - start))
            print("Display updates: ", displayUpdates, " fps: ", fps)
            start = time.clock()    # resetting timer
            displayUpdates += 1


        else:
            print("ERROR: Expected 768 bytes of data, got ", len(data))
            print("Data received: ", data)


    else:
        print("Got malformed data, exiting: ", data)
        pygame.quit()
        s.close()
        sys.exit()

