#/usr/bin/env python3

import asyncio
import os, sys
import json
import textwrap
from asyncrpc.client import UniCastClient
from contextlib import suppress
import argparse

class RPCClient:

    def __init__(self):
        config_file = os.path.expanduser(os.path.join('~', 'rpcclient.json'))
        with open(config_file) as f:
            data = json.load(f)
            self.nightly_build_host = data['NIGHTLY_BUILD_HOST']
            self.upgrade_host = data['UPGRADE_HOST']
            self.server_port = data['PORT']

    def doUpgrade(self):
        print("Starting upgrade job ...")
        self.server = UniCastClient(interfaces_info=[(self.upgrade_host, self.server_port)])
        mode = RPCClient.getJenkinsVariable("Mode")
        if not mode:
            mode = "All"

        loop = asyncio.get_event_loop()
        loop.set_debug(1)
        if mode == "Singl":
            boxIP = RPCClient.getJenkinsVariable("BoxIP")
            project = RPCClient.getJenkinsVariable("Project")
            if boxIP is "" or project is "":
                raise Exception("Please type BoxIP/Project")
                sys.exit()

            isRelease = RPCClient.getJenkinsVariable("Release")
            if isRelease == "true":
                releaseVersion = RPCClient.getJenkinsVariable("ReleaseVersion")
                if releaseVersion is "":
                    raise Exception("Please type ReleaseVersion for RELEASE upgrade")
                    sys.exit()

            isRelease = RPCClient.getJenkinsVariable("Release")
            if isRelease == "true":
                releaseVersion = RPCClient.getJenkinsVariable("ReleaseVersion")
                if releaseVersion is "":
                    raise Exception("Please type ReleaseVersion for RELEASE upgrade")
                    sys.exit()
                print("Upgrade box: {} with project {} release {} ...".format(boxIP, project, releaseVersion))
                with suppress(asyncio.TimeoutError):
                    print(loop.run_until_complete(self.server.upgradeBoxWithRC(boxIP, "{}-{}".format(project, releaseVersion))))

            else:
                branch = RPCClient.getJenkinsVariable("Branch")
                if branch is "" :
                    raise Exception("Please type Branch for CURRENT upgrade")
                    sys.exit()
                print("Upgrade box: {} from branch {} with project {} ...".format(boxIP, branch, project));
                with suppress(asyncio.TimeoutError):
                    print(loop.run_until_complete(self.server.upgradeBox(project, boxIP)))
        else:
            print("Upgrading all boxes in Generic Lab ...")
            with suppress(asyncio.TimeoutError):
                print(loop.run_until_complete(self.server.upgradeAllBoxes()))

        loop.run_until_complete(self.server.close())
    
    def doNightlyBuild(self):
        print("Starting nightly job ...")
        self.server = UniCastClient(interfaces_info=[(self.nightly_build_host, self.server_port)])
        loop = asyncio.get_event_loop()
        with suppress(asyncio.TimeoutError):
            try:
                print(loop.run_until_complete(self.server.buildNightlySoft()))
            except:
                pass
        loop.run_until_complete(self.server.close())

    @staticmethod
    def getJenkinsVariable(name):
        val = os.getenv(name)
        if val:
            val.endswith(",")
            val = val[:-1]
        return val

    @staticmethod
    def helper():
        epilog=textwrap.dedent('''\
        Example of usage:
        ./{scriptName} --help
        ./{scriptName} --type nightly
        ./{scriptName} --type upgrade'''
        .format(scriptName=os.path.basename(__file__)))

        parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description='Client rpc is use to connect to server rpc and do upgrade or nightly build.',
                                         epilog=epilog)

        parser.add_argument('--type', type=str)
        return parser.parse_args()

def main():

    args = RPCClient.helper()

    rpcClient = RPCClient()
    if args.type == 'upgrade':
        rpcClient.doUpgrade()
    elif args.type == 'nightly':
        rpcClient.doNightlyBuild()

if __name__ == '__main__':
    main()
