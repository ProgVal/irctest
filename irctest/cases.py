import time
import socket
import unittest
import collections

from . import authentication
from .irc_utils import message_parser

class _IrcTestCase(unittest.TestCase):
    """Base class for test cases."""
    controllerClass = None # Will be set by __main__.py

    def setUp(self):
        super().setUp()
        self.controller = self.controllerClass()
        if self.show_io:
            print('---- new test ----')
    def getLine(self):
        raise NotImplementedError()
    def getMessages(self, *args):
        lines = self.getLines(*args)
        return map(message_parser.parse_message, lines)
    def getMessage(self, *args, filter_pred=None):
        """Gets a message and returns it. If a filter predicate is given,
        fetches messages until the predicate returns a False on a message,
        and returns this message."""
        while True:
            msg = message_parser.parse_message(self.getLine(*args))
            if not filter_pred or filter_pred(msg):
                return msg
    def assertMessageEqual(self, msg, subcommand=None, subparams=None,
            target=None, **kwargs):
        """Helper for partially comparing a message.

        Takes the message as first arguments, and comparisons to be made
        as keyword arguments.

        Deals with subcommands (eg. `CAP`) if any of `subcommand`,
        `subparams`, and `target` are given."""
        for (key, value) in kwargs.items():
            with self.subTest(key=key):
                self.assertEqual(getattr(msg, key), value, msg)
        if subcommand is not None or subparams is not None:
            self.assertGreater(len(msg.params), 2, msg)
            msg_target = msg.params[0]
            msg_subcommand = msg.params[1]
            msg_subparams = msg.params[2:]
            if subcommand:
                with self.subTest(key='subcommand'):
                    self.assertEqual(msg_subcommand, subcommand, msg)
            if subparams is not None:
                with self.subTest(key='subparams'):
                    self.assertEqual(msg_subparams, subparams, msg)

class BaseClientTestCase(_IrcTestCase):
    """Basic class for client tests. Handles spawning a client and exchanging
    messages with it."""
    nick = None
    user = None
    def setUp(self):
        super().setUp()
        self._setUpServer()
    def tearDown(self):
        self.conn.sendall(b'QUIT :end of test.')
        self.controller.kill()
        self.conn_file.close()
        self.conn.close()
        self.server.close()

    def _setUpServer(self):
        """Creates the server and make it listen."""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('', 0)) # Bind any free port
        self.server.listen(1)
    def acceptClient(self):
        """Make the server accept a client connection. Blocking."""
        (self.conn, addr) = self.server.accept()
        self.conn_file = self.conn.makefile(newline='\r\n',
                encoding='utf8')

    def getLine(self):
        line = self.conn_file.readline()
        if self.show_io:
            print('C: {}'.format(line.strip()))
        return line
    def sendLine(self, line):
        ret = self.conn.sendall(line.encode())
        assert ret is None
        if not line.endswith('\r\n'):
            ret = self.conn.sendall(b'\r\n')
            assert ret is None
        if self.show_io:
            print('S: {}'.format(line.strip()))

class ClientNegociationHelper:
    """Helper class for tests handling capabilities negociation."""
    def readCapLs(self, auth=None):
        (hostname, port) = self.server.getsockname()
        self.controller.run(
                hostname=hostname,
                port=port,
                auth=auth,
                )
        self.acceptClient()
        m = self.getMessage()
        self.assertEqual(m.command, 'CAP',
                'First message is not CAP LS.')
        if m.params == ['LS']:
            self.protocol_version = 301
        elif m.params == ['LS', '302']:
            self.protocol_version = 302
        elif m.params == ['END']:
            self.protocol_version = None
        else:
            raise AssertionError('Unknown CAP params: {}'
                    .format(m.params))

    def userNickPredicate(self, msg):
        """Predicate to be used with getMessage to handle NICK/USER
        transparently."""
        if msg.command == 'NICK':
            self.assertEqual(len(msg.params), 1, msg)
            self.nick = msg.params[0]
            return False
        elif msg.command == 'USER':
            self.assertEqual(len(msg.params), 4, msg)
            self.user = msg.params
            return False
        else:
            return True

    def negotiateCapabilities(self, capabilities, cap_ls=True, auth=None):
        """Performes a complete capability negociation process, without
        ending it, so the caller can continue the negociation."""
        if cap_ls:
            self.readCapLs(auth)
            if not self.protocol_version:
                # No negotiation.
                return
            self.sendLine('CAP * LS :{}'.format(' '.join(capabilities)))
        capability_names = {x.split('=')[0] for x in capabilities}
        self.acked_capabilities = set()
        while True:
            m = self.getMessage(filter_pred=self.userNickPredicate)
            if m.command != 'CAP':
                return m
            self.assertGreater(len(m.params), 0, m)
            if m.params[0] == 'REQ':
                self.assertEqual(len(m.params), 2, m)
                requested = frozenset(m.params[1].split())
                if not requested.issubset(capability_names):
                    self.sendLine('CAP {} NAK :{}'.format(
                        self.nick or '*',
                        m.params[1][0:100]))
                else:
                    self.sendLine('CAP {} ACK :{}'.format(
                        self.nick or '*',
                        m.params[1]))
                    self.acked_capabilities.update(requested)
            else:
                return m

Client = collections.namedtuple('Client',
        'conn conn_file')

class BaseServerTestCase(_IrcTestCase):
    """Basic class for server tests. Handles spawning a server and exchanging
    messages with it."""
    def setUp(self):
        super().setUp()
        self.find_hostname_and_port()
        kwargs = {}
        if self.server_start_delay is not None:
            kwargs['start_wait'] = self.server_start_delay
        self.controller.run(self.hostname, self.port, **kwargs)
        self.clients = {}
    def tearDown(self):
        self.controller.kill()
        for client in list(self.clients):
            self.removeClient(client)
    def find_hostname_and_port(self):
        """Find available hostname/port to listen on."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        (self.hostname, self.port) = s.getsockname()
        s.close()

    def addClient(self, name=None):
        """Connects a client to the server and adds it to the dict.
        If 'name' is not given, uses the lowest unused non-negative integer."""
        if not name:
            name = max(map(int, list(self.clients)+[0]))+1
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((self.hostname, self.port))
        conn_file = conn.makefile(newline='\r\n', encoding='utf8')
        self.clients[name] = Client(conn=conn, conn_file=conn_file)
        return name

    def removeClient(self, name):
        """Disconnects the client, without QUIT."""
        assert name in self.clients
        self.clients[name].conn.close()
        del self.clients[name]

    def getLines(self, client):
        data = b''
        conn = self.clients[client].conn
        try:
            conn.setblocking(False)
            while True:
                time.sleep(0.1) # TODO: do better than this (use ping?)
                data += conn.recv(4096)
        except BlockingIOError:
            for line in data.decode().split('\r\n'):
                if line:
                    print('S -> {}: {}'.format(client, line.strip()))
                    yield line + '\r\n'
        finally:
            conn.setblocking(True) # required for readline()
    def getLine(self, client):
        assert client in self.clients
        line = self.clients[client].conn_file.readline()
        if self.show_io:
            print('S -> {}: {}'.format(client, line.strip()))
        return line
    def sendLine(self, client, line):
        ret = self.clients[client].conn.sendall(line.encode())
        assert ret is None
        if not line.endswith('\r\n'):
            ret = self.clients[client].conn.sendall(b'\r\n')
            assert ret is None
        if self.show_io:
            print('{} -> S: {}'.format(client, line.strip()))

    def getCapLs(self, client):
        """Waits for a CAP LS block, parses all CAP LS messages, and return
        the list of capabilities."""
        capabilities = []
        while True:
            m = self.getMessage(client,
                    filter_pred=lambda m:m.command != 'NOTICE')
            self.assertMessageEqual(m, command='CAP', subcommand='LS')
            if m.params[2] == '*':
                capabilities.extend(m.params[3].split())
            else:
                capabilities.extend(m.params[2].split())
                return capabilities
