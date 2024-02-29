# Distributed Multithreaded Banking System
## Distributed Systems Lab Mini Project 2024
###The Banking Management System is a comprehensive software solution designed to streamline and automate various banking operations, catering to both administrators and customers. This system provides a user-friendly interface for managing accounts, transactions, and other banking functionalities efficiently.



[Project Report](https://github.com/anurag1942003/Distributed-Banking-System/blob/main/DS-Mini%20Project%20Report.pdf)




## Contents

This project consists of 2 folders: `client` and `server`.

The `client` folder contains a single file `main.py`. This file tries to
connect to the database server. Once the user is connected, the user can perform
various actions like refreshing to see updated balance, deposit, withdraw and 
transfer money, etc. The user also has ability to see all transactions they were
involved in.
If the user enters credentials of admin user (username: 0 and password: root), they can add and delete accounts, see all customers and see all transactions that have taken place.

The `server` folder contains a folder for text of menus, the `sqlite3` database and
3 python programs. The `main.py` starts the server and creates threads for clients.
The `admin.py` handles the admin operations and `customer.py` handles the customer operations.
The `dbs_view.py` consists of responses to send to client and how to process their 
request. The `dbs_exec.py` contains code that access the database. Any access to the
DB has to be done by functions in `dbs_exec`, most commonly used function being
`execute()`.

The `twilio` library is used to send SMS and `tabulate` library to beautify table
output.

## How To Execute

Before starting make sure you create a virtual environment and install necessary
dependencies.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate virtual environment
./venv/bin/activate

# Install necessary dependencies
pip install -r requirements.txt
```

First, execute `main.py` in the `server` folder, followed by `admin.py` and `customer.py` in the same folder. Then, execute `main.py` in the `client` folder in a separate terminal. Ensure that the client connects to the server.

**Note**: You may need to change the twilio account credentials, along with the IP
Addresses
