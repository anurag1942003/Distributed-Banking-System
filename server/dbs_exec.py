import hashlib
import sqlite3
import twilio.rest as tr
import threading
# Global constants
ADMIN_ID = 0
ADMIN_HASH = '4813494d137e1631bba301d5acab6e7bb7aa74ce1185d456565ef51d737677b2'

db_lock = threading.Lock()


def executeQuery(query, database_name):
    operation = query.split()[0].upper()
    is_write_operation = operation in ['INSERT', 'UPDATE', 'DELETE']

    if is_write_operation:
        db_lock.acquire()
    connector = sqlite3.connect(f'{database_name}.db')
    cursor = connector.cursor()
    try:
        cursor.execute(query)
        connector.commit()

        # If it's a write operation, replicate the changes
        if is_write_operation:
            if database_name == 'database_main':
                replicate_changes(
                    query, ['database_customer', 'database_admin'])
            elif database_name == 'database_admin':
                replicate_changes(
                    query, ['database_customer', 'database_main'])
            else:
                replicate_changes(
                    query, ['database_admin', 'database_main'])
        result = cursor.fetchall() if operation == 'SELECT' else []
        data = [True, result, cursor.description if operation == 'SELECT' else None]

    except sqlite3.Error as sqe:
        data = [False, sqe]

    finally:
        cursor.close()
        connector.close()
        if is_write_operation:
            db_lock.release()

    return data


def replicate_changes(query, databases):
    # List of databases to replicate the changes to, excluding the source if it's listed
    for db_name in databases:
        try:
            with sqlite3.connect(f'{db_name}.db') as conn:
                conn.execute(query)
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error replicating changes to {db_name}: {e}")


def createDatabase(database_name):
    status = executeQuery('''
		CREATE TABLE IF NOT EXISTS CUSTOMERS(
			account_num INTEGER PRIMARY KEY AUTOINCREMENT,
			first_name VARCHAR(20) NOT NULL,
			last_name VARCHAR(20) NOT NULL,
			aadhar_num VARCHAR(16) UNIQUE NOT NULL,
			phone_num VARCHAR(12) UNIQUE NOT NULL,
			sms CHAR(1) NOT NULL,
			balance FLOAT NOT NULL
		)
	''', database_name)
    if not status[0]:
        return status

    status = executeQuery('''
		CREATE TABLE IF NOT EXISTS TRANSACTIONS(
			transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
			from_account INTEGER NOT NULL,
			to_account INTEGER NOT NULL,
			amount FLOAT NOT NULL,
			type VARCHAR(10),
			date varchar(20),
			FOREIGN KEY (from_account, to_account) REFERENCES CUSTOMERS(account_num, account_num)
		)
	''', database_name)
    if not status[0]:
        return status

    status = executeQuery('''
		CREATE TABLE IF NOT EXISTS AUTH(
			account_num INTEGER,
			password varchar(100) NOT NULL,
			FOREIGN KEY (account_num) REFERENCES CUSTOMERS(account_num) ON DELETE CASCADE
		)
	''', database_name)
    return status


def sha256Hash(string: str) -> str:
    return hashlib.sha256(string.encode()).hexdigest()


def isUserAdmin(accountNumber: int, password: str) -> bool:
    passHash = sha256Hash(password)
    return (accountNumber == ADMIN_ID and passHash == ADMIN_HASH)


def doesValueExist(field: str, value: any) -> bool:
    if isinstance(value, str):
        value = "'" + value + "'"

    status = executeQuery('''
		SELECT {}
		FROM CUSTOMERS
		WHERE {}={}
	'''.format(field, field, value), 'database_main'
    )
    return len(status[1]) > 0


def authenticate(accountNumber: int, password: str) -> bool:
    passhash = sha256Hash(password)
    status = executeQuery('''
		SELECT account_num
		FROM AUTH 
		WHERE account_num={} AND password='{}'
	'''.format(accountNumber, passhash), 'database_main')
    return len(status[1]) > 0


def sendSMS(accounts, amount, type, date):
    account_sid = 'ACCOUNT_SID'
    auth_token = 'AUTH_TOKEN'
    client = tr.Client(account_sid, auth_token)

    phone = None
    body = None
    if type == 'd':
        status = executeQuery('''
			SELECT phone_num
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accounts[0]), 'database_customer')
        phone = '+91' + status[1][0][0]
        body = ('MIT bank account XXX' + str(accounts[0]).zfill(3)[-3:]
                + ' was credited for Rs ' + str(amount) + ' on ' + date + '.'
                )

    elif type == 'w':
        status = executeQuery('''
			SELECT phone_num
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accounts[0]), 'database_customer')
        phone = '+91' + status[1][0][0]
        body = ('MIT bank account XXX' + str(accounts[0]).zfill(3)[-3:]
                + ' was debited for Rs ' + str(amount) + ' on ' + date + '.'
                )

    elif type == 'ts':
        status = executeQuery('''
			SELECT phone_num
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accounts[0]), 'database_customer')
        status = executeQuery('''
			SELECT first_name
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accounts[1]), 'database_customer')
        firstName = status[1][0][0]
        status = executeQuery('''
			SELECT last_name
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accounts[1]), 'database_customer')
        lastName = status[1][0][0]
        name = firstName.upper() + ' ' + lastName.upper()

        status = executeQuery('''
			SELECT phone_num
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accounts[1]), 'database_customer')
        phone = '+91' + status[1][0][0]
        body = ('MIT bank account XXX' + str(accounts[0]).zfill(3)[-3:]
                + ' was debited for Rs ' + str(amount) + ' on ' + date + '.'
                + ' ' + name + ' credited.'
                )

    elif type == 'tr':
        status = executeQuery('''
			SELECT phone_num
			FROM CUSTOMERS
			WHERE account_num={}
		'''.format(accounts[1]), 'database_customer')
        phone = '+91' + status[1][0][0]
        body = ('MIT bank account XXX' + str(accounts[1]).zfill(3)[-3:]
                + ' was credited for Rs ' + str(amount) + ' on ' + date + '.'
                )
    client.messages.create(
        from_='TWILIO_PHONE_NUMBER',
        body=body,
        to=phone
    )
