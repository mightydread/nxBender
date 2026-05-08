import configargparse
import requests
import logging
import getpass
from colorlog import ColoredFormatter

parser = configargparse.ArgumentParser(
        description='Connect to a netExtender VPN',
        default_config_files=['/etc/nxbender', '~/.nxbender'],
    )

parser.add_argument('-c', '--conf', is_config_file=True)

parser.add_argument('-s', '--server', required=True)
parser.add_argument('-P', '--port', type=int, default=443, help='Server port - default 443')
parser.add_argument('-u', '--username', required=True)
parser.add_argument('-p', '--password', required=False)
parser.add_argument('-d', '--domain', required=True)

parser.add_argument('-f', '--fingerprint', help='Verify server\'s SSL certificate has this fingerprint. Overrides all other certificate verification.')
parser.add_argument('-m', '--max-line', type=int, default=1500, help='Maximum length of a single line of PPP data sent to the server')

parser.add_argument('--resolve-domain', action='append', default=[],
                    help='Additional DNS routing domain to send via the VPN (e.g. "example.com"). May be specified multiple times. The server-supplied dnsSuffix is always included.')
parser.add_argument('--no-dns', action='store_true', help='Do not configure DNS via systemd-resolved when the tunnel comes up')
parser.add_argument('--split-tunnel', action='store_true',
                    help='Do not install the server-pushed default route (0.0.0.0/0). Only specific subnets pushed by the server are routed via the VPN; all other traffic uses the system default route.')
parser.add_argument('--extra-route', action='append', default=[],
                    help='Additional CIDR to route via the VPN beyond what the server pushes (e.g. "10.0.0.0/8"). Repeatable.')

parser.add_argument('--pinentry', help='Program to use to prompt for interactive responses eg. OTP codes. Specify "none" to just prompt on the terminal.')

parser.add_argument('--debug', action='store_true', help='Show debugging information')
parser.add_argument('-q', '--quiet', action='store_true', help='Don\'t output basic info whilst running')
parser.add_argument('--show-ppp-log', action='store_true', help='Print PPP log messages to stdout')


def main():
    args = parser.parse_args()

    if args.debug:
        loglevel = logging.DEBUG
    elif args.quiet:
        loglevel = logging.WARNING
    else:
        loglevel = logging.INFO

    if not args.password:
        args.password = getpass.getpass()


    formatter = ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(message_log_color)s%(message)s",
            secondary_log_colors={
                    'message': {
                            'ERROR':    'red',
                            'CRITICAL': 'red'
                    }
            }
    )
    logging.basicConfig(level=loglevel)
    logging.getLogger().handlers[0].setFormatter(formatter)

    if args.debug:
        try:
            from http.client import HTTPConnection # py3
        except ImportError:
            from httplib import HTTPConnection # py2

        HTTPConnection.debuglevel = 2

    from . import nx, sslconn

    sess = nx.NXSession(args)

    try:
        sess.run()
    except requests.exceptions.SSLError as e:
        logging.error("SSL error: %s" % e)
        # print the server's fingerprint for the user to consider
        sslconn.print_fingerprint(args.server)
    except requests.exceptions.ConnectionError as e:
        message = e.message.reason.message.split(':')[1:][-1]   # yuk
        logging.error("Error connecting to remote host: %s" % message)
