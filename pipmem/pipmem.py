import argparse
import datetime
import logging
import os
import sqlite3
import subprocess

VERSION = 0.2

# Create logger object and set appropriate format and filename
pm_logger = logging.getLogger('pipmem')
pm_logger.setLevel(logging.INFO)
pmlogformat = logging.Formatter('%(asctime)s %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S')
pm_log_handler = logging.FileHandler('pipmem.log')
pm_log_handler.setFormatter(pmlogformat)
pm_logger.addHandler(pm_log_handler)

pmdbfile = 'pipmem.db'


def setupdb():
    """ Create the sqlite3 database and appropriate tables.

        venv variable is used to store any activated venv in order to operate
        on its packages instead of the system packages. """

    try:
        conn = sqlite3.connect(pmdbfile)
        conn.execute('CREATE TABLE transactions ( \
                     id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, \
                     timestamp TEXT NOT NULL, \
                     action TEXT NOT NULL, \
                     venv TEXT NULL, \
                     pkgs TEXT NOT NULL)')
        conn.commit()
        conn.close()
    except:
        pm_logger.error('Unable to initialize pipmem database.')
        print('Unable to initialize pipmem database.')


def insert_transaction(action, pkgs, venv=None):
    """ Insert data for the given operation into the database.
        Include data on the packages modified and venv activated if any. """

    now = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    pkgs = ','.join(pkgs)
    try:
        if os.environ['VIRTUAL_ENV']:
            venv = os.environ['VIRTUAL_ENV']
    except:
        pass

    try:
        conn = sqlite3.connect(pmdbfile)
        conn.execute('INSERT INTO transactions (timestamp, action, venv, pkgs) \
                     VALUES (?, ?, ?, ?)', (now, action, venv, pkgs))
        conn.commit()
        conn.close()
    except FileNotFoundError:
        print('Unable to find pipmem.db. Attempting creation of new database.')
        setupdb()


def show_history(size=10):
    """ Show a summary of the most recent transaations performed. """

    try:
        conn = sqlite3.connect(pmdbfile)
        cur = conn.cursor()
        cur.execute('SELECT id,timestamp,action FROM transactions \
                    ORDER BY id DESC')
        transactions = cur.fetchmany(size)
        conn.close()

        # Use string justification here to ensure neat column output.
        print('Last 10 transactions performed\n')
        print('ID'.ljust(8), '|', 'Timestamp'.ljust(20), '|',
              'Action'.ljust(20))
        print('-' * 48)
        for t in transactions:
            print(str(t[0]).ljust(8), '|', t[1].ljust(20), '|', t[2].ljust(20))
    except FileNotFoundError:
        print('Unable to find pipmem.db. Attempting creation of new database.')
        setupdb()


def get_transaction(id):
    """ Show information on the specified transaction. """

    try:
        conn = sqlite3.connect(pmdbfile)
        cur = conn.cursor()
        cur.execute('SELECT * FROM transactions WHERE ID = (?)', (id,))
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
    except FileNotFoundError:
        print('Unable to find pipmem.db. Attempting creation of new database.')
        setupdb()


def undo_transaction(id):
    """ Determine transaction action and package list, then perform the
        opposite action on the same package list. """

    try:
        conn = sqlite3.connect(pmdbfile)
        cur = conn.cursor()
        cur.execute('SELECT action,venv,pkgs FROM transactions '
                    'WHERE ID is (?)',
                    (id,))
        transaction = cur.fetchone()
        conn.close()

        action = transaction[0]
        venv = transaction[1]
        pkgs = transaction[2].replace('-', '==')

        if action == 'install':
            uninstall_packages(pkgs, venv=venv)
        elif action == 'uninstall':
            install_packages(pkgs, venv=venv)
    except FileNotFoundError:
        print('Unable to find pipmem.db. Attempting creation of new database.')
        setupdb()


def configure_venv_path(venv):
    """ Properly return pip location to run for the given venv. """

    if os.name == 'nt':
        return os.path.abspath(os.path.join(venv, 'scripts', 'pip.exe'))
    elif os.name == 'posix':
        return os.path.abspath(os.path.join(venv, 'bin', 'pip'))


def install_packages(pkgs, is_upgrade=False, venv=None):
    """ Use pip to install the given packages. """

    # Predefine pip commands being used.
    if venv:
        installcmd = (configure_venv_path(venv) + ' install').split(' ')
        upgradecmd = (configure_venv_path(venv) + ' install -U').split(' ')
    else:
        installcmd = 'pip install'.split(' ')
        upgradecmd = 'pip install -U'.split(' ')

    # Select the appropriate pip command if performing package upgrade.
    if is_upgrade:
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
                insert_transaction(action, ipkgs, venv)
                for ipkg in ipkgs:
                    pm_logger.info('Installed %s', ipkg)


def uninstall_packages(pkgs, venv=None):
    """ Use pip to uninstall the given packages. """

    # Predefine pip commands being used.
    if venv:
        erasecmd = (configure_venv_path(venv) + ' uninstall -y').split(' ')
    else:
        erasecmd = 'pip uninstall -y'.split(' ')

    # The subprocess.PIPE hides the command output from the user so printing
    # is needed as an additional step.
    output = subprocess.run(erasecmd + pkgs.split(','),
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
        insert_transaction('uninstall', upkgs, venv)
        for upkg in upkgs:
            pm_logger.info('Uninstalled %s', upkg)


def main():
    # Create the application database if it does not already exist.
    if not os.path.exists(pmdbfile):
        setupdb()

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
    action_history.add_argument('--undo',
                                type=int, metavar='ID',
                                help='Undo transaction with ID')

    # Collect application arguments into the args variable.
    args = parser.parse_args()

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

if __name__ == '__main__':
    main()
