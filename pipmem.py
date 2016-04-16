import argparse
import datetime
import logging
import os
import sqlite3
import subprocess

# Create logger object and set appropriate format and filename
pmlogger = logging.getLogger('pipmem')
pmlogger.setLevel(logging.INFO)
pmlogformat = logging.Formatter('%(asctime)s %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S')
pmloghandler = logging.FileHandler('pipmem.log')
pmloghandler.setFormatter(pmlogformat)
pmlogger.addHandler(pmloghandler)

pmdbfile = 'pipmem.db'


def setupdb():
    conn = sqlite3.connect(pmdbfile)
    conn.execute('CREATE TABLE transactions ( \
                 id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, \
                 timestamp TEXT NOT NULL, \
                 action TEXT NOT NULL, \
                 pkgs TEXT NOT NULL, \
                 venv TEXT)')


def insert_transaction(action, pkgs):
    now = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    pkgs = ','.join(pkgs)

    conn = sqlite3.connect(pmdbfile)
    conn.execute('INSERT INTO transactions (timestamp, action, pkgs, venv) \
                 VALUES (?, ?, ?, ?)', (now, action, pkgs, None))
    conn.commit()
    conn.close()


def show_history():
    conn = sqlite3.connect(pmdbfile)
    cur = conn.cursor()
    cur.execute('SELECT id,timestamp,action FROM transactions \
                ORDER BY id DESC')
    transactions = cur.fetchmany(10)
    conn.close()

    print('Last 10 transactions performed\n')
    print('ID'.ljust(8), '|', 'Timestamp'.ljust(20), '|', 'Action'.ljust(20))
    print('-' * 48)
    for t in transactions:
        print(str(t[0]).ljust(8), '|', t[1].ljust(20), '|', t[2].ljust(20))


def get_transaction(id):
    conn = sqlite3.connect(pmdbfile)
    cur = conn.cursor()
    cur.execute('SELECT * FROM transactions WHERE ID is (?)', (id,))
    transaction = cur.fetchone()
    conn.close()

    if transaction:
        print('ID: %s' % transaction[0])
        print('Timestamp: %s' % transaction[1])
        print('Action: %s' % transaction[2])
        print('venv: %s' % transaction[4])
        print('Packages:')
        for pkg in transaction[3].split(','):
            print('\t%s' % pkg)
    else:
        print('No transaction with ID %s found' % id)


def undo_transaction(id):
    conn = sqlite3.connect(pmdbfile)
    cur = conn.cursor()
    cur.execute('SELECT action,pkgs FROM transactions WHERE ID is (?)', (id,))
    transaction = cur.fetchone()
    conn.close()

    action = transaction[0]
    pkgs = transaction[1].replace('-', '==')

    if action == 'install':
        uninstall_package(pkgs)
    elif action == 'uninstall':
        install_package(pkgs)


def install_package(pkgs):
    output = subprocess.run(['pip', 'install'] + pkgs.split(','),
                            stdout=subprocess.PIPE,
                            universal_newlines=True)
    print(output.stdout)
    for line in output.stdout.split('\n'):
        if 'Successfully installed' in line:
            ipkgs = line.replace('-', '==').split(' ')[2:]
            insert_transaction('install', ipkgs)
            for ipkg in ipkgs:
                pmlogger.info('Installed %s', ipkg)


def uninstall_package(pkgs):
    output = subprocess.run(['pip', 'uninstall', '-y'] + pkgs.split(','),
                            stdout=subprocess.PIPE,
                            universal_newlines=True)
    print(output.stdout)
    upkgs = []
    for line in output.stdout.split('\n'):
        if 'Successfully uninstalled' in line:
            upkgs.append(line.replace('-', '==').split(' ')[4])
    insert_transaction('uninstall', upkgs)
    for upkg in upkgs:
        pmlogger.info('Uninstalled %s', upkg)


if __name__ == '__main__':
    desc = 'pipmem is used to keep track of action performed by the pip \
            package manager.'
    parser = argparse.ArgumentParser(description=desc)
    actions = parser.add_subparsers(dest='action')
    actions.required = True
    action_install = actions.add_parser('install',
                                        help='Install packages.')
    action_install.add_argument('-p', '--pkgs',
                                action='store',
                                help='List of packages to install')

    action_uninstall = actions.add_parser('uninstall',
                                          help='Unnstall packages.')
    action_uninstall.add_argument('-p', '--pkgs',
                                  action='store',
                                  help='List of packages to install')

    action_history = actions.add_parser('history',
                                        help='Transaction history data')
    action_history.set_defaults(func=show_history)
    action_history.add_argument('-i', '--info',
                                type=int,
                                help='Show history details for ID')
    action_history.add_argument('-u', '--undo',
                                type=int,
                                help='Undo transaction with ID')

    args = parser.parse_args()

    if not os.path.exists(pmdbfile):
        setupdb()

    if args.action == 'install':
        install_package(args.pkgs)
    elif args.action == 'uninstall':
        uninstall_package(args.pkgs)
    elif args.action == 'history':
        if args.info:
            get_transaction(str(args.info))
        elif args.undo:
            undo_transaction(str(args.undo))
        else:
            show_history()
