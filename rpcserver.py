#!/usr/bin/python3.6

import asyncio
import json
import UpgraderInstance
import nightly_build
from asyncrpc.server import UniCastServer

class RPCServer:

    def __init__(self):
        config_file = 'conf.json'
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
        upgrader.upgrade_box(upgradeParams)

    @asyncio.coroutine
    def upgradeBoxWithRC(self, project:str, ip:str):
        upgrade_params = {'PROJECT': project, 'IP': ip}
        upgrader = Upgrader(self.upgrade)
        upgrader.upgrade_box_with_rc(upgradeParams)

    @asyncio.coroutine
    def buildNightlySoft(self):
        for nightlyBuild in self.nightlyBuilds:
            builder = Builder(nightlyBuild, self.jira)
            builder.build_nightly_projects()

if __name__ == '__main__':
    server = UniCastServer(
        obj=RPCServer(),
        ip_addrs='10.136.208.248',
        port=9001
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start())
    loop.run_forever()
