#!/usr/bin/python3

import os
import sys
import asyncio
import json
from nightly_build import Builder
from UpgraderInstance import Upgrader
from asyncrpc.server import UniCastServer

class RPCServer:

    def __init__(self):
        prefix = os.path.dirname(os.path.realpath(sys.argv[0]))
        config_file = os.path.join(prefix, 'conf.json')
        with open(config_file) as f:
            data = json.load(f)
            self.nightlyBuilds = data['NIGHTLY_BUILD']
            self.upgrade = data['UPGRADE']
            self.jira = data['JIRA']

    @asyncio.coroutine
    def upgradeAllBoxes(self):
        upgrader = Upgrader(self.upgrade)
        upgrader.upgrade_all_boxes()

    @asyncio.coroutine
    def upgradeBox(self, project:str, branch:int, ip:str):
        upgrade_params = {'PROJECT': project, 'BRANCH': branch, 'IP': ip}
        upgrader = Upgrader(self.upgrade)
        upgrader.upgrade_box(upgrade_params)

    @asyncio.coroutine
    def upgradeBoxWithRC(self, project:str, ip:str):
        upgrade_params = {'PROJECT': project, 'IP': ip}
        upgrader = Upgrader(self.upgrade)
        upgrader.upgrade_box_with_rc(upgrade_params)

    @asyncio.coroutine
    def buildNightlySoft(self):
        for nightlyBuild in self.nightlyBuilds:
            builder = Builder(nightlyBuild, self.jira)
            builder.build_nightly_projects()

if __name__ == '__main__':
    print('Run rpc server')
    server = UniCastServer(
        obj=RPCServer(),
        ip_addrs='10.136.209.228',
        port=9001
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start())
    loop.run_forever()
