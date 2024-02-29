import os
import sys

import common
import pickle
import getpass
import random
import platform
import socket
import time
import struct

SERVER_IP = '127.0.0.1'
SERVER_PORT = 1069


def connectToServer(server_details):
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((server_details[0], server_details[1]))
    return clientSocket


def clearScreen():
    os_name = platform.system()
    if os_name == 'Windows':
        os.system('cls')
    else:
        os.system('clear')


def checkSendError(status: list, clientSocket: socket.socket) -> None:
    if not status[0]:
        clientSocket.close()
        print('There was some error in sending the message to the server')
        print('Please try again later...')
        sys.exit(1)


def checkReceiveError(status: list, clientSocket: socket.socket) -> None:
    if not status[0]:
        clientSocket.close()
        print('There was some error in receiving data from the server')
        print('Please try again later...')
        sys.exit(1)


def displayText(request: str, start: int, end='') -> None:
    print(request[start:], end=end)
    sys.stdout.flush()


def main():
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print('Trying to connect to the server...')
        clientSocket.connect((SERVER_IP, SERVER_PORT))
        print('Connection was successful!')
        time.sleep(3)
        key = random.randint(0, 255)
        status = common.sendEncryptedMessage(clientSocket, str(key), 0)
        checkSendError(status, clientSocket)
        while True:
            reply = None
            status = common.recvEncryptedMessage(clientSocket, key)
            checkReceiveError(status, clientSocket)

            response = status[1]
            if response.startswith('@EXIT'):
                displayText(response, 6, '\n')
                clientSocket.close()
                sys.exit(0)
            if response.startswith('@REDIRECT'):
                break

            if response.startswith('@PASS'):
                displayText(response, 6)
                reply = getpass.getpass('')
            else:
                if response.startswith('@CLEAR'):
                    clearScreen()
                    displayText(response, 7)
                else:
                    displayText(response, 0)
                reply = input('')

            if reply == '':
                reply = ' '

            status = common.sendEncryptedMessage(clientSocket, reply, key)
            checkSendError(status, clientSocket)
    except ConnectionRefusedError:
        print('\nCould not connect to the banking server. Please try again later')
    size_data = clientSocket.recv(4)
    size = struct.unpack("!I", size_data)[0]
    data = b''
    while len(data) < size:
        chunk = clientSocket.recv(min(size - len(data), 1024))
        if not chunk:
            break
        data += chunk
    admin_details = pickle.loads(data)
    server_IP, server_Port, accountNumber = admin_details
    clientSocket.close()
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((server_IP, server_Port))
    data_to_specialisedserver = (key, accountNumber)
    print(key, accountNumber)
    clientSocket.sendall(pickle.dumps(data_to_specialisedserver))
    while True:
        reply = None
        status = common.recvEncryptedMessage(clientSocket, key)
        checkReceiveError(status, clientSocket)
        response = status[1]
        if response.startswith('@EXIT'):
            displayText(response, 6, '\n')
            clientSocket.close()
            sys.exit(0)
        if response.startswith('@PASS'):
            displayText(response, 6)
            reply = getpass.getpass('')
        else:
            if response.startswith('@CLEAR'):
                clearScreen()
                displayText(response, 7)
            else:
                displayText(response, 0)
            reply = input('')

        if reply == '':
            reply = ' '

        status = common.sendEncryptedMessage(clientSocket, reply, key)
        checkSendError(status, clientSocket)


if __name__ == '__main__':
    main()
