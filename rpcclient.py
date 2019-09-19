#/usr/bin/env python3

import asyncio
import os, sys
from asyncrpc.client import UniCastClient
from contextlib import suppress

class RPCClient():
    def getJenkinsVariable(self, name):
        val = os.getenv(name)
        if val:
            val.endswith(",")
            val = val[:-1]
        return val

    def doUpgrade(self):
        mode = self.getJenkinsVariable("Mode")
        if not mode:
            mode = "All"
        serverIP = self.getJenkinsVariable("ServerIP")
        if not serverIP:
            serverIP = "10.136.209.228"
        serverPort = self.getJenkinsVariable("ServerPort")
        if not serverPort:
            serverPort = "9001"
        '''
        if serverIP is "" or serverPort is "":
            raise Exception("Please type server IP/PORT")
            sys.exit()
        '''
        server = UniCastClient(
            interfaces_info=[(serverIP, serverPort)]
        )

        loop = asyncio.get_event_loop()
        loop.set_debug(1)
        if mode == "Singl":
            boxIP = self.getJenkinsVariable("BoxIP")
            project = self.getJenkinsVariable("Project")
            if boxIP is "" or project is "":
                raise Exception("Please type BoxIP/Project")
                sys.exit()

            isRelease = self.getJenkinsVariable("Release")
            if isRelease == "true":
                releaseVersion = self.getJenkinsVariable("ReleaseVersion")
                if releaseVersion is "":
                    raise Exception("Please type ReleaseVersion for RELEASE upgrade")
                    sys.exit()

            isRelease = self.getJenkinsVariable("Release")
            if isRelease == "true":
                releaseVersion = self.getJenkinsVariable("ReleaseVersion")
                if releaseVersion is "":
                    raise Exception("Please type ReleaseVersion for RELEASE upgrade")
                    sys.exit()
                print("Upgrade box: {} with project {} release {} ...".format(boxIP, project, releaseVersion))
                with suppress(asyncio.TimeoutError):
                    print(loop.run_until_complete(server.upgradeBoxWithRC(boxIP, "{}-{}".format(project, releaseVersion))))

            else:
                branch = self.getJenkinsVariable("Branch")
                if branch is "" :
                    raise Exception("Please type Branch for CURRENT upgrade")
                    sys.exit()
                print("Upgrade box: {} from branch {} with project {} ...".format(boxIP, branch, project));
                with suppress(asyncio.TimeoutError):
                    print(loop.run_until_complete(server.upgradeBox(project, boxIP)))
        else:
            print("Upgrading all boxes in Generic Lab ...")
            with suppress(asyncio.TimeoutError):
                print(loop.run_until_complete(server.upgradeAllBoxes()))

        loop.run_until_complete(server.close())

def main():
    rpcClient = RPCClient()
    rpcClient.doUpgrade()

if __name__ == '__main__':
    main()
