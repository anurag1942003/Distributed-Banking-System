import threading
import socket
import dbs_exec as dbe
import dbs_view as dbv
import common
import os
import sys
import pickle


SERVER_IP = '127.0.0.1'
SERVER_PORT = 1069
IP = '127.0.0.1'



def connectToServer():
    CustomerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    CustomerSocket.connect((SERVER_IP, SERVER_PORT))
    return CustomerSocket


def handleClient(clientSocket, address):
    try:
        data = clientSocket.recv(1024)
        key, accountNumber = pickle.loads(data)
        dbv.customerMenu(accountNumber, clientSocket, key, address)
    except Exception as e:
        print("An error occurred while handling client:", e)
    finally:
        clientSocket.close()


def main():
    try:
        CustomerSocket = connectToServer()
        dbv.loadMenus()
        port = CustomerSocket.recv(1024)
        Port = pickle.loads(port)
        status = dbe.createDatabase("database_customer")
        if not status[0]:
            print('Creation of DBS failed due to {}, program will be terminated...'.format(
                status[1]))
            sys.exit(1)
        print('Databases initialized...')
        CustomerSocket.close()
        CustomerServerSocket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        CustomerServerSocket.bind((IP, Port))
        CustomerServerSocket.listen(5)
        print('Customer server is now listening for client connections...')
        while True:
            clientSocket, address = CustomerServerSocket.accept()
            print('Accepted connection from client:', address)
            threading.Thread(target=handleClient, args=(
                clientSocket, address)).start()
    except Exception as e:
        print("An error occurred:", e)
    finally:
        CustomerServerSocket.close()


if __name__ == '__main__':
    main()
