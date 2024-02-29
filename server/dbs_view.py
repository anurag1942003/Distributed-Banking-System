import pickle
import os
import common
import tabulate
import socket
import datetime
import sys
import struct
import dbs_exec as dbe


# A global dictionary that contains various menus
MENU_LIST = {}


def menuReader(menuName):
    with open(menuName, 'r') as file:
        content = file.read()
    return content


def loadMenus():
    menus = ['adminMenu', 'loginMenu', 'customerMenu']
    for menu in menus:
        MENU_LIST[menu] = menuReader('menu/' + menu + '.txt')


def checkConnectionError(status: list, clientSocket: socket.socket, details: tuple) -> None:
    if not status[0]:
        clientSocket.close()
        ip, port = details
        print('Due to {}, connection with {}:{} was closed'.format(
            status[1], ip, port))
        sys.exit(1)


def safeSend(clientSocket: socket.socket, message: str, key: int, details: tuple) -> None:
    status = common.sendEncryptedMessage(clientSocket, message, key)
    checkConnectionError(status, clientSocket, details)


def safeReceive(clientSocket: socket.socket, key: int, details: tuple) -> str:
    status = common.recvEncryptedMessage(clientSocket, key)
    checkConnectionError(status, clientSocket, details)
    return status[1]


def invalidOption(clientSocket: socket.socket, key: int, details: tuple):
    prompt = '\nInvalid option was entered. Press any key to continue...'
    safeSend(clientSocket, prompt, key, details)
    _ = safeReceive(clientSocket, key, details)


def loginMenu(clientSocket: socket.socket, key: int, details, specialServerSocket: dict) -> None:
    try:
        while True:
            safeSend(clientSocket, MENU_LIST['loginMenu'], key, details)

            data = safeReceive(clientSocket, key, details)

            choice = data.casefold()
            if choice == 'a':
                prompt = '\nEnter your account number: '
                safeSend(clientSocket, prompt, key, details)
                data = safeReceive(clientSocket, key, details)

                try:
                    accountNumber = int(data)
                    prompt = '@PASS\nEnter your password: '
                    safeSend(clientSocket, prompt, key, details)
                    password = safeReceive(clientSocket, key, details)
                    if dbe.isUserAdmin(accountNumber, password):
                        prompt = '@REDIRECT'
                        safeSend(clientSocket, prompt, key, details)
                        adminServerSocket, adminAddress = specialServerSocket["admin"]
                        admin_details = (adminAddress[0], adminAddress[1], 0)
                        data = pickle.dumps(admin_details)
                        size = struct.pack("!I", len(data))
                        try:
                            clientSocket.sendall(size)
                            clientSocket.sendall(data)
                        except Exception as e:
                            print("Error while sending admin details:", e)
                        finally:
                            clientSocket.close()
                            break

                    else:
                        if dbe.authenticate(accountNumber, password):
                            prompt = '@REDIRECT'
                            safeSend(clientSocket, prompt, key, details)
                            customerServerSocket, customerAddress = specialServerSocket["customer"]
                            customer_details = (
                                customerAddress[0], customerAddress[1], accountNumber)
                            try:
                                clientSocket.sendall(
                                    struct.pack("!I", len(pickle.dumps(customer_details))))
                                clientSocket.sendall(
                                    pickle.dumps(customer_details))
                            except Exception as e:
                                pass
                            finally:
                                clientSocket.close()
                                break

                        else:
                            prompt = '\nInvalid credentials. Press any key to continue...'
                            safeSend(clientSocket, prompt, key, details)
                            _ = safeReceive(clientSocket, key, details)

                except ValueError as ve:
                    prompt = '\nAccount number must be an integer. Press any key to continue...'
                    safeSend(clientSocket, prompt, key, details)
                    _ = safeReceive(clientSocket, key, details)
            elif choice == 'b':
                prompt = '@EXIT\n\nThank you for using MIT Bank\n'
                safeSend(clientSocket, prompt, key, details)
                ip, port = details
                clientSocket.close()
                print('{}:{} has exited'.format(ip, port))
                break
            else:
                invalidOption(clientSocket, key, details)
    except Exception as e:
        pass


def addAccount(clientSocket: socket.socket, key: int, details: tuple) -> None:
    prompt = '@CLEAR\nEnter Aadhar number: '
    safeSend(clientSocket, prompt, key, details)
    aadhar = safeReceive(clientSocket, key, details)
    exists = dbe.doesValueExist('aadhar_num', aadhar)
    if exists:
        prompt = '\nError: The Aadhar number is already in use. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)
        _ = safeReceive(clientSocket, key, details)
        return

    prompt = '\nEnter phone number: '
    safeSend(clientSocket, prompt, key, details)
    phone = safeReceive(clientSocket, key, details)
    exists = dbe.doesValueExist('phone_num', phone)
    if exists:
        prompt = '\nError: The Phone number is already in use. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)
        _ = safeReceive(clientSocket, key, details)
        return

    prompt = '\nEnter first name: '
    safeSend(clientSocket, prompt, key, details)
    firstName = safeReceive(clientSocket, key, details)

    prompt = '\nEnter last name: '
    safeSend(clientSocket, prompt, key, details)
    lastName = safeReceive(clientSocket, key, details)

    prompt = '\nActivate SMS service for user? (Y or N): '
    safeSend(clientSocket, prompt, key, details)
    data = safeReceive(clientSocket, key, details).casefold()
    sms = 'Y' if (data == 'y' or data == 'yes') else 'N'

    prompt = '\nEnter password: '
    safeSend(clientSocket, prompt, key, details)
    password = safeReceive(clientSocket, key, details).casefold()

    passhash = dbe.sha256Hash(password)

    status = dbe.executeQuery('''
		INSERT INTO CUSTOMERS(
			first_name, last_name, aadhar_num, phone_num, balance, sms
		) VALUES(
			'{}', '{}', '{}', '{}', {}, '{}'
		)
	'''.format(firstName, lastName, aadhar, phone, 100000, sms), 'database_admin')

    inserted = status[0]
    if inserted:
        status = dbe.executeQuery('''
			SELECT account_num
			FROM CUSTOMERS
			WHERE aadhar_num='{}'
		'''.format(aadhar), 'database_admin')

        data = status[1]
        accountNumber = data[0][0]

        status = dbe.executeQuery('''
			INSERT INTO AUTH(
				account_num, password
			) VALUES(
				'{}', '{}'
			)
		'''.format(accountNumber, passhash), 'database_admin')

        prompt = '\nAccount added successfully. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)
    else:
        prompt = '\nAccount could not be added. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)

    _ = safeReceive(clientSocket, key, details)


def deleteAccount(clientSocket: socket.socket, key: int, details: tuple) -> None:
    prompt = '\nEnter account number: '
    safeSend(clientSocket, prompt, key, details)
    data = safeReceive(clientSocket, key, details)
    try:
        accountNumber = int(data)
        exists = dbe.doesValueExist('account_num', accountNumber)
        if exists:
            prompt = '@PASS\n\nEnter admin password to proceed: '
            safeSend(clientSocket, prompt, key, details)
            password = safeReceive(clientSocket, key, details)
            admin = dbe.isUserAdmin(0, password)
            if admin:
                dbe.executeQuery('''
					DELETE FROM CUSTOMERS
					WHERE account_num={}
				'''.format(accountNumber), 'database_admin')
                dbe.executeQuery('''
					DELETE FROM AUTH
					WHERE account_num={}
				'''.format(accountNumber), 'database_admin')
                prompt = '\nAccount {} was deleted. Press any key...'.format(
                    accountNumber)
                safeSend(clientSocket, prompt, key, details)
            else:
                prompt = '\nWrong password. Deletion will not happen. Press any key to continue...'
                safeSend(clientSocket, prompt, key, details)
        else:
            prompt = '\nAccount with that account number does not exist. Press any key to continue...'
            safeSend(clientSocket, prompt, key, details)
    except ValueError:
        prompt = '\nAccount number must be an integer. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)
    _ = safeReceive(clientSocket, key, details)


def displayTable(tableName: str, clientSocket: socket.socket,
                 key: int, details: tuple, database_name, condition='') -> None:
    query = 'SELECT * FROM {}'.format(tableName)
    if condition != '':
        query += ' WHERE ' + condition
    status = dbe.executeQuery(query, database_name)
    if status[0]:
        headers = [desc[0] for desc in status[2]]
        table = tabulate.tabulate(
            status[1], headers=headers, tablefmt='presto')
        prompt = '@CLEAR\n{} table\n\n{}\n\nPress any key to continue...'.format(
            tableName.upper(), table
        )
        safeSend(clientSocket, prompt, key, details)
    else:
        prompt = '\nUnable to show {} table. Press any key to continue...'.format(
            tableName.upper()
        )
    _ = safeReceive(clientSocket, key, details)


def adminMenu(clientSocket: socket.socket, key: int, details) -> None:
    while True:
        safeSend(clientSocket, MENU_LIST['adminMenu'], key, details)
        data = safeReceive(clientSocket, key, details)
        choice = data.casefold()
        if choice == 'a':
            addAccount(clientSocket, key, details)
        elif choice == 'b':
            deleteAccount(clientSocket, key, details)
        elif choice == 'c':
            displayTable('CUSTOMERS', clientSocket,
                         key, details, "database_admin")
        elif choice == 'd':
            displayTable('TRANSACTIONS', clientSocket,
                         key, details, "database_admin")
        elif choice == 'e':
            logoutMessage = '@EXIT\n\nThank you for using the system. You are now logged out.\n'
            safeSend(clientSocket, logoutMessage, key, details)
            break
        else:
            invalidOption(clientSocket, key, details)


def customerMenu(accountNumber: int, clientSocket: socket.socket, key: int, details) -> None:
    while True:
        status = dbe.executeQuery('''
			SELECT balance
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accountNumber), "database_customer")

        data = status[1]
        balance = data[0][0]
        prompt = MENU_LIST['customerMenu'].format(
            account_num=accountNumber, balance=balance)
        safeSend(clientSocket, prompt, key, details)
        data = safeReceive(clientSocket, key, details)
        choice = data.casefold()
        if choice == 'a':
            pass
        elif choice == 'b':
            depositMenu(accountNumber, clientSocket, key, details)
        elif choice == 'c':
            withdrawMenu(accountNumber, clientSocket, key, details)
        elif choice == 'd':
            transferMenu(accountNumber, clientSocket, key, details)
        elif choice == 'e':
            condition = 'from_account={} OR to_account={}'.format(
                accountNumber, accountNumber)
            displayTable('TRANSACTIONS', clientSocket, key,
                         details, "database_customer", condition)
        elif choice == 'f':
            logoutMessage = '@EXIT\n\nThank you for using the system. You are now logged out.\n'
            safeSend(clientSocket, logoutMessage, key, details)
            break
        else:
            invalidOption(clientSocket, key, details)


def depositMenu(accountNumber: int, clientSocket: socket.socket, key: int, details: tuple) -> None:
    prompt = '\nEnter amount to deposit: '
    safeSend(clientSocket, prompt, key, details)
    data = safeReceive(clientSocket, key, details)
    try:
        amount = float(data)
        status = dbe.executeQuery('''
			SELECT balance
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accountNumber), 'database_customer')

        data = status[1]
        balance = data[0][0]
        status = dbe.executeQuery('''
			UPDATE CUSTOMERS
			SET balance = {}
			WHERE account_num={}
		'''.format(balance+amount, accountNumber), 'database_customer')

        date = str(datetime.datetime.now())[:19]
        status = dbe.executeQuery('''
			INSERT INTO TRANSACTIONS(
				from_account, to_account, amount, type, date
			) VALUES (
				{}, {}, {}, '{}', '{}'
			)
		'''.format(accountNumber, accountNumber, amount, 'DEPOSIT', date), 'database_customer')

        data = dbe.executeQuery('''
			SELECT sms
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accountNumber), 'database_customer')
        sms = data[1][0][0]
        if sms == 'Y':
            dbe.sendSMS([accountNumber], amount, 'd', date)

        # PLAYSOUND

        prompt = '\nDeposit was successful. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)

    except ValueError:
        prompt = '\nEnter a valid number. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)

    _ = safeReceive(clientSocket, key, details)


def withdrawMenu(accountNumber: int, clientSocket: socket.socket, key: int, details: tuple) -> None:
    prompt = '\nEnter amount to withdraw: '
    safeSend(clientSocket, prompt, key, details)
    data = safeReceive(clientSocket, key, details)
    try:
        amount = float(data)
        status = dbe.executeQuery('''
			SELECT balance
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accountNumber), 'database_customer')

        data = status[1]
        balance = data[0][0]

        if balance >= amount:
            status = dbe.executeQuery('''
				UPDATE CUSTOMERS
				SET balance = {}
				WHERE account_num={}
			'''.format(balance-amount, accountNumber), 'database_customer')
            date = str(datetime.datetime.now())[:19]
            status = dbe.executeQuery('''
				INSERT INTO TRANSACTIONS(
					from_account, to_account, amount, type, date
				) VALUES (
				{}, {}, {}, '{}', '{}'
				)
			'''.format(accountNumber, accountNumber, amount, 'WITHDRAWAL', date), 'database_customer')

            data = dbe.executeQuery('''
				SELECT sms
				FROM CUSTOMERS
				WHERE account_num={}
			'''.format(accountNumber), 'database_customer')
            sms = data[1][0][0]
            if sms == 'Y':
                dbe.sendSMS([accountNumber], amount, 'w', date)

            # PLAYSOUND

            prompt = '\nWithdrawal was successful. Press any key to continue...'
            safeSend(clientSocket, prompt, key, details)
        else:
            prompt = '\nInsufficient balance to perform withdrawal. Press any key to continue...'
            safeSend(clientSocket, prompt, key, details)
    except ValueError:
        prompt = '\nEnter a valid number. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)

    _ = safeReceive(clientSocket, key, details)


def transferMenu(accountNumber: int, clientSocket: socket.socket, key: int, details: tuple) -> None:
    prompt = '\nEnter account number of receiver: '
    safeSend(clientSocket, prompt, key, details)
    data = safeReceive(clientSocket, key, details)
    try:
        theirAccount = int(data)
        exists = dbe.doesValueExist('account_num', theirAccount)
        if exists:
            prompt = '\nEnter amount to transfer: '
            safeSend(clientSocket, prompt, key, details)
            data = safeReceive(clientSocket, key, details)
            try:
                amount = float(data)
                status = dbe.executeQuery('''
					SELECT balance
					FROM CUSTOMERS
					WHERE account_num={}
				'''.format(accountNumber), 'database_customer')
                data = status[1]
                yourBalance = data[0][0]

                status = dbe.executeQuery('''
					SELECT balance
					FROM CUSTOMERS
					WHERE account_num={}
				'''.format(theirAccount), 'database_customer')
                data = status[1]
                theirBalance = data[0][0]

                if yourBalance >= amount:
                    status = dbe.executeQuery('''
						UPDATE CUSTOMERS
						SET balance = {}
						WHERE account_num={}
					'''.format(yourBalance-amount, accountNumber), 'database_customer')
                    status = dbe.executeQuery('''
						UPDATE CUSTOMERS
						SET balance = {}
						WHERE account_num={}
					'''.format(theirBalance+amount, theirAccount), 'database_customer')
                    date = str(datetime.datetime.now())[:19]

                    status = dbe.executeQuery('''
						INSERT INTO TRANSACTIONS(
							from_account, to_account, amount, type, date
						) VALUES (
							{}, {}, {}, '{}', '{}'
						)
					'''.format(accountNumber, theirAccount, amount, 'TRANSFER', date), 'database_customer')

                    data = dbe.executeQuery('''
						SELECT sms
						FROM CUSTOMERS
						WHERE account_num={}
					'''.format(accountNumber), 'database_customer')
                    sms = data[1][0][0]
                    if sms == 'Y':
                        dbe.sendSMS([accountNumber, theirAccount],
                                    amount, 'ts', date)

                    data = dbe.executeQuery('''
						SELECT sms
						FROM CUSTOMERS
						WHERE account_num={}
					'''.format(theirAccount), 'database_customer')
                    sms = data[1][0][0]
                    if sms == 'Y':
                        dbe.sendSMS([accountNumber, theirAccount],
                                    amount, 'tr', date)

                    # PLAYSOUND

                    prompt = '\nTransfer was successful. Press any key to continue...'
                    safeSend(clientSocket, prompt, key, details)
                else:
                    prompt = '\nInsufficient balance to perform withdrawal. Press any key to continue...'
                    safeSend(clientSocket, prompt, key, details)
            except ValueError:
                prompt = '\nEnter a valid number. Press any key to continue...'
                safeSend(clientSocket, prompt, key, details)
        else:
            prompt = '\nThe account does not exist. Press any key to continue...'
            safeSend(clientSocket, prompt, key, details)
    except ValueError:
        prompt = '\nAccount number must be an integer. Press any key to continue...'
        safeSend(clientSocket, prompt, key, details)

    _ = safeReceive(clientSocket, key, details)
