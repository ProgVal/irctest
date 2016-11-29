import os
import time
import subprocess

from irctest.basecontrollers import NotImplementedByController
from irctest.basecontrollers import BaseServerController, DirectoryBasedController

TEMPLATE_CONFIG = """
network:
    name: OragonoTest

server:
    name: oragono.test
    listen:
        - "{hostname}:{port}"

    check-ident: false

    connection-limits:
        cidr-len-ipv4: 24
        cidr-len-ipv6: 120
        ips-per-subnet: 16

        exempted:
            - "127.0.0.1/8"
            - "::1/128"

registration:
    accounts:
        enabled: true
        verify-timeout: "120h"
        enabled-callbacks:
            - none # no verification needed, will instantly register successfully

authentication-enabled: true

datastore:
    path: {directory}/ircd.db

limits:
    nicklen: 32
    channellen: 64
    awaylen: 200
    kicklen: 390
    topiclen: 390
    monitor-entries: 100
    whowas-entries: 100
    chan-list-modes: 60
"""

class OragonoController(BaseServerController, DirectoryBasedController):
    software_name = 'Oragono'
    supported_sasl_mechanisms = {
            'PLAIN',
    }
    def create_config(self):
        super().create_config()
        with self.open_file('ircd.yaml'):
            pass

    def kill_proc(self):
        self.proc.kill()

    def run(self, hostname, port, password=None, ssl=False,
            restricted_metadata_keys=None,
            valid_metadata_keys=None, invalid_metadata_keys=None):
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                    'Defining valid and invalid METADATA keys.')
        if password is not None:
            #TODO(dan): fix dis
            raise NotImplementedByController('PASS command')
        if ssl:
            #TODO(dan): fix dis
            raise NotImplementedByController('SSL')
        assert self.proc is None
        self.port = port
        self.create_config()
        with self.open_file('server.yml') as fd:
            fd.write(TEMPLATE_CONFIG.format(
                directory=self.directory,
                hostname=hostname,
                port=port,
                ))
        subprocess.call(['oragono', 'initdb',
            '--conf', os.path.join(self.directory, 'server.yml'), '--quiet'])
        subprocess.call(['oragono', 'mkcerts',
            '--conf', os.path.join(self.directory, 'server.yml'), '--quiet'])
        self.proc = subprocess.Popen(['oragono', 'run',
            '--conf', os.path.join(self.directory, 'server.yml'), '--quiet'])

    def registerUser(self, case, username, password=None):
        # XXX: Move this somewhere else when
        # https://github.com/ircv3/ircv3-specifications/pull/152 becomes
        # part of the specification
        client = case.addClient(show_io=False)
        case.sendLine(client, 'CAP LS 302')
        case.sendLine(client, 'NICK registration_user')
        case.sendLine(client, 'USER r e g :user')
        case.sendLine(client, 'CAP END')
        while case.getRegistrationMessage(client).command != '001':
            pass
        list(case.getMessages(client))
        case.sendLine(client, 'REG CREATE {} passphrase {}'.format(
            username, password))
        msg = case.getMessage(client)
        assert msg.command == '920', msg
        list(case.getMessages(client))
        case.removeClient(client)

def get_irctest_controller_class():
    return OragonoController