import argparse
import logging
import subprocess

# Create logger object and set appropriate format and filename
pmlogger = logging.getLogger('pipmem')
pmlogger.setLevel(logging.INFO)
pmlogformat = logging.Formatter('%(asctime)s %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S')
pmloghandler = logging.FileHandler('pipmem.log')
pmloghandler.setFormatter(pmlogformat)
pmlogger.addHandler(pmloghandler)


def install_package(pkgs):
    for pkg in pkgs.split(','):
        output = subprocess.run(['pip', 'install', pkg],
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        print(output.stdout)
        for line in output.stdout.split('\n'):
            if 'Successfully' in line:
                for ipkg in line.split(' ')[2:]:
                    pmlogger.info('Installed %s', ipkg)

def uninstall_package(pkgs):
    for pkg in pkgs.split(','):
        output = subprocess.run(['pip', 'uninstall', '-y', pkg],
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        print(output.stdout)
        for line in output.stdout.split('\n'):
            if 'Successfully' in line:
                for ipkg in line.split(' ')[4:]:
                    pmlogger.info('Uninstalled %s', ipkg)


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

    if args.action == 'install':
        install_package(args.pkgs)
    elif args.action == 'uninstall':
        uninstall_package(args.pkgs)
