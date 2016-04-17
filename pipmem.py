import argparse
import datetime
import logging
import os
import sqlite3
import subprocess

VERSION = 0.1

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
    """ Create the sqlite3 database and appropriate tables.

        venv variable is used to store any activated venv in order to operate
        on its packages instead of the system packages. """

    conn = sqlite3.connect(pmdbfile)
    conn.execute('CREATE TABLE transactions ( \
                 id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, \
                 timestamp TEXT NOT NULL, \
                 action TEXT NOT NULL, \
                 venv TEXT NULL, \
                 pkgs TEXT NOT NULL)')


def insert_transaction(action, pkgs, venv=None):
    """ Insert data for the given operation into the database.
        Include data on the packages modified and venv activated if any. """

    now = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    pkgs = ','.join(pkgs)

    conn = sqlite3.connect(pmdbfile)
    conn.execute('INSERT INTO transactions (timestamp, action, venv, pkgs) \
                 VALUES (?, ?, ?, ?)', (now, action, venv, pkgs))
    conn.commit()
    conn.close()


def show_history(size=10):
    conn = sqlite3.connect(pmdbfile)
    cur = conn.cursor()
    cur.execute('SELECT id,timestamp,action FROM transactions \
                ORDER BY id DESC')
    transactions = cur.fetchmany(size)
    conn.close()

    # Use string justification here to ensure neat column output to the screen.
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
        print('venv: %s' % transaction[3])
        print('Packages:')
        for pkg in transaction[4].split(','):
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
        uninstall_packages(pkgs)
    elif action == 'uninstall':
        install_packages(pkgs)


def install_packages(pkgs, isupgrade=False):
    """ Use pip to install the given packages. """

    # Predefine pip commands being used.
    installcmd = 'pip install'.split(' ')
    upgradecmd = 'pip install -U'.split(' ')

    # Select the appropriate pip command if performing package upgrade.
    if isupgrade:
        action = 'upgrade'
        pipcmd = upgradecmd
    else:
        action = 'install'
        pipcmd = installcmd

    # The subprocess.PIPE hides the command output from the user so printing
    # is needed as an additional step.
    output = subprocess.run(pipcmd + pkgs.split(','),
                            stdout=subprocess.PIPE,
                            universal_newlines=True)
    print(output.stdout)

    if output.returncode == 0:
        # Search for a notification of successfully installed packages in
        # output to determine installed packages list.
        for line in output.stdout.split('\n'):
            if 'Successfully installed' in line:
                # Split the output line to gather specific package information.
                # Simulate requirements.txt format by replacing the hypens.
                ipkgs = line.replace('-', '==').split(' ')[2:]

                # Record transaction in both database and log file.
                insert_transaction(action, ipkgs)
                for ipkg in ipkgs:
                    pmlogger.info('Installed %s', ipkg)


def uninstall_packages(pkgs):
    """ Use pip to uninstall the given packages. """

    # The subprocess.PIPE hides the command output from the user so printing
    # is needed as an additional step.
    output = subprocess.run(['pip', 'uninstall', '-y'] + pkgs.split(','),
                            stdout=subprocess.PIPE,
                            universal_newlines=True)
    print(output.stdout)

    if output.returncode == 0:
        # The uninstall process outputs to separate lines unlike installation.
        # Check each line and simulate requirements.txt format, then add the
        # package data to the upkgs list.
        upkgs = []
        for line in output.stdout.split('\n'):
            if 'Successfully uninstalled' in line:
                upkgs.append(line.replace('-', '==').split(' ')[4])

        # Record transaction in both database and log file.
        insert_transaction('uninstall', upkgs)
        for upkg in upkgs:
            pmlogger.info('Uninstalled %s', upkg)


if __name__ == '__main__':
    desc = 'pipmem is used to keep track of action performed by the pip \
            package manager.'

    # Define the arguments used by the application.
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v', '--version', action='version',
                        version=str(VERSION),
                        help='Print version number then exit')

    # Subparsers are used to ignore the leading hypen for the first argument.
    actions = parser.add_subparsers(dest='action')
    actions.required = True

    # Application action definitions.
    action_install = actions.add_parser('install',
                                        help='Install packages.')
    action_uninstall = actions.add_parser('uninstall',
                                          help='Unnstall packages')
    action_history = actions.add_parser('history',
                                        help='Transaction history data')

    # Arguments for each action specified below.
    action_install.add_argument('-p', '--pkgs',
                                action='store',
                                help='List of packages to install')
    action_install.add_argument('-u', '--upgrade',
                                action='store_true',
                                help='Upgrade specified packages to the '
                                     'latest available version')

    action_uninstall.add_argument('-p', '--pkgs',
                                  action='store',
                                  help='List of packages to install')

    action_history.add_argument('-i', '--info',
                                type=int, metavar='ID',
                                help='Show history details for ID')
    action_history.add_argument('-u', '--undo',
                                type=int, metavar='ID',
                                help='Undo transaction with ID')

    # Collect application arguments into the args variable.
    args = parser.parse_args()

    # Create the application database if it does not already exist.
    if not os.path.exists(pmdbfile):
        setupdb()

    # Run appropriate function based on provided arguments.
    if args.action == 'install':
        if args.upgrade and not args.pkgs:
            print('Package list required for upgrade.')
            print('Please add the -p option with a list of packages and '
                  'retry.')
        else:
            install_packages(args.pkgs, args.upgrade)
    elif args.action == 'uninstall':
        uninstall_packages(args.pkgs)
    elif args.action == 'history':
        if args.info:
            get_transaction(str(args.info))
        elif args.undo:
            undo_transaction(str(args.undo))
        else:
            show_history()
