from subprocess import run

import argparse
import logging

# Create logger object and set appropriate format and filename
pmlogger = logging.getlogger('pipmem')
pmlogger.setlevel(logging.INFO)
pmlogformat = logging.Formatter('%(asctime)s %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S')
pmloghandler = logging.FileHandler('pipmem.log')
pmloghandler.formatter(pmlogformat)
pmlogger.sethandler(pmloghandler)

if __name__ == '__main__':
    desc = 'pipmem is used to keep track of action performed by the pip \
            package manager.'
    parser = argparse.ArgumentParser(description=desc)
    actions = parser.add_subparsers()
    action_install = actions.add_parser('install',
                                        help='Install packages.')
    action_uninstall = actions.add_parser('uninstall',
                                          help='Unnstall packages.')
    args = parser.parse_args()
