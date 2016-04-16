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


def install_package(pkgs):
    output = subprocess.run(['pip', 'install'] + pkgs.split(','),
                            stdout=subprocess.PIPE,
                            universal_newlines=True)
    print(output.stdout)
    for line in output.stdout.split('\n'):
        if 'Successfully installed' in line:
            ipkgs = line.split(' ')[2:]
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
            upkgs += line.split(' ')[4:]
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
    action_uninstall = actions.add_parser('uninstall',
                                          help='Unnstall packages.')
    ipkgs = action_install.add_argument('-p', '--pkgs',
                                        action='store',
                                        help='List of packages to install')
    upkgs = action_uninstall.add_argument('-p', '--pkgs',
                                          action='store',
                                          help='List of packages to install')
    args = parser.parse_args()

    if not os.path.exists(pmdbfile):
        setupdb()

    if args.action == 'install':
        install_package(args.pkgs)
    elif args.action == 'uninstall':
        uninstall_package(args.pkgs)
