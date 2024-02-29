import os
import sys
import pickle

import common
import dbs_view as dbv
import dbs_exec as dbe

import socket
import threading
SERVER_IP = '127.0.0.1'
SERVER_PORT = 1069
IP = '127.0.0.1'
PORT = 1070


def connectToServer():
    AdminSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    AdminSocket.connect((SERVER_IP, SERVER_PORT))
    return AdminSocket


def handleClient(clientSocket, address):
    data = clientSocket.recv(1024)
    key, accountNumber = pickle.loads(data)
    dbv.adminMenu(clientSocket, key, address)
    clientSocket.close()


def main():
    try:
        AdminSocket = connectToServer()
        dbv.loadMenus()
        port = AdminSocket.recv(1024)
        Port = pickle.loads(port)
        status = dbe.createDatabase("database_admin")
        if not status[0]:
            print('Creation of DBS failed due to {}, program will be terminated...'.format(
                status[1]))
            sys.exit(1)
        print('Databases initialized...')

        AdminSocket.close()
        AdminServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        AdminServerSocket.bind((IP, Port))
        AdminServerSocket.listen(5)
        print('Admin server is now listening for client connections...')
        while True:
            clientSocket, address = AdminServerSocket.accept()
            print('Accepted connection from client:', address)
            threading.Thread(target=handleClient, args=(
                clientSocket, address)).start()
    except Exception as e:
        print("An error occurred:", e)
    finally:
        AdminServerSocket.close()


if __name__ == '__main__':
    main()
