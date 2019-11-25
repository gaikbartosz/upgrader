#!/usr/bin/python3

#
# TiVo Poland Sp. z o.o. Software License Version 1.0
#
# Copyright (C) 2008-2019 TiVo Poland Sp. z o.o. All rights reserved.
#
# Any rights which are not expressly granted in this License are entirely and
# exclusively reserved to and by TiVo Poland Sp. z o.o. You may not rent, lease,
# modify, translate, reverse engineer, decompile, disassemble, or create
# derivative works based on this Software. You may not make access to this
# Software available to others in connection with a service bureau,
# application service provider, or similar business, or make any other use of
# this Software without express written permission from TiVo Poland Sp. z o.o.
#
# Any User wishing to make use of this Software must contact
# TiVo Poland Sp. z o.o. to arrange an appropriate license. Use of the Software
# includes, but is not limited to:
# (1) integrating or incorporating all or part of the code into a product for
#     sale or license by, or on behalf of, User to third parties;
# (2) distribution of the binary or source code to third parties for use with
#     a commercial product sold or licensed by, or on behalf of, User.
#

"""
Script which builds projects, copies them to remote location, upgrades boxes and sends status email.
"""

import json
import os
import glob
import subprocess
import datetime
import argparse
import textwrap
import pysftp
import time
from typing import List, Dict
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class Upgrader:
    """Class which is response for building projects based on config from conf.json."""

    def __init__(self, upgrade_config:dict):
        """Constructor of Upgrader class.

        Args:
        upgrade_config (dict): Data taken from conf.json containing specific upgrade data.
        """

        """Config params"""
        self.remote_location: int = upgrade_config['REMOTE_LOCATION']
        self.work_dir: str = upgrade_config['WORK_DIR']
        self.server: str = upgrade_config['SERVER']
        self.username: str = upgrade_config['USERNAME']
        self.lab_key_path: str = upgrade_config['LAB_KEY_PATH']
        self.all_boxes: List[Dict[str, str]]= upgrade_config['BOXES_LIST']
        self.upgrade_base_dir: str = upgrade_config['UPGRADE_BASE_DIR']
        self.upgrade_base_url: str = upgrade_config['UPGRADE_BASE_URL']
        self.from_mail_address: str = upgrade_config['FROM_MAIL_ADDRESS']
        self.to_mail_address: str = upgrade_config['TO_MAIL_ADDRESS']

        """Present upgrade params"""
        self.upgrade_type: str = 'single'
        self.version_md5_hash: str = None
        self.build_dir: str = None
        self.project: str = None
        self.branch: str = None
        self.ip: str = None
        self.key_path: str = None
        self.upgrade_succeed: bool = None
        self.base_dir: str = None
        self.local_path: str = None
        self.local_arch_path: str = None

    def call_command(self, command: str):
        """
        Call specific command.

        Args:
        command (str): command which will be called
        """

        try:
            subprocess.check_call(command, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as error:
            print(error.output)
            exit(0)

    def prepare(self):
        """Prepare directories, files"""

        if self.upgrade_type == 'single' or self.upgrade_type == 'all':
            self.base_dir = os.path.join(self.work_dir, self.branch)
            print("Preparing working directories in {}".format(self.base_dir))
            os.makedirs(self.base_dir, exist_ok=True)
            os.chdir(self.base_dir)
            print("Done")
            
            print("Pulling branch {} ...".format(self.branch))
            self.call_command('nosilo pull {} -ym'.format(self.branch))
            print("Pulling done.")
        elif self.upgrade_type == 'rc':
            self.base_dir = os.path.join(self.work_dir, 'RC')
            print("Preparing working directories in {}".format(self.base_dir))
            os.makedirs(self.base_dir, exist_ok=True)
            os.chdir(self.base_dir)
            print("Done")
            
            print("Pulling RC {} ...".format(self.project))
            self.call_command('nosilo fetch release {}'.format(self.project))
            print("Pulling done.")
        elif self.upgrade_type == 'local':
            pass


    def build(self):
        """Build single project. Software will be tagged by tag prepared in prepare() method."""

        if not self.upgrade_type == 'rc':
            print("Build project {}".format(self.project))
            self.call_command('SvDebug=yes SvDebugBuild=yes SvKeepStack=yes pysilo --clean --project {}'.format(self.project))
            print("Build done.")

        upgrade_package = glob.glob(os.path.join("sbuild-{}".format(self.project), "*upgrade*.tgz"))[0]
        assert len(upgrade_package) > 0

        cmd = 'tar -ztf {} | grep "md5$"'.format(upgrade_package)
        ps = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        upgrade_file = str(ps.communicate()[0], "utf-8").rstrip("\n")
        assert len(upgrade_file) > 0

        cmd = "tar -O -zxf {} {} | head -n 1 | awk '{{print $1}}'".format(upgrade_package,
                                                                          upgrade_file)

        ps = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        self.version_md5_hash = str(ps.communicate()[0], "utf-8").rstrip("\n")
        assert len(self.version_md5_hash) > 0

        print("Cleaning before tagging ...")
        self.call_command('nosilo foreach "hg revert --all && hg purge"')
        print("Done")

        print("Tagging new software ...")
        self.call_command('nosilo tag {} --name=bluelab_{}'.format(self.branch,
                                                                   self.version_md5_hash))

    def copy(self):
        """Copy prepared packages to remote and local locations"""

        if self.upgrade_type == 'rc':
            return

        self.local_path = os.path.join(self.base_dir, 'sbuild-{}'.format(self.project))
        archName = 'sbuild.tar'
        print("Create {} from {}\n".format(archName, self.local_path.split('/')[-1]))
        self.local_arch_path = os.path.join(self.base_dir, archName)
        self.call_command('cd {}'.format(self.base_dir))
        self.call_command('tar -zcf {} {}'.format(archName, self.local_path.split('/')[-1]))

        remoteBasePath = os.path.join(self.remote_location, self.version_md5_hash)
        remoteSbuildPath = os.path.join(remoteBasePath, 'sbuild-{}'.format(self.project))
        print("Extract {} in remote {}\n".format(archName, remoteBasePath))
        with pysftp.Connection(self.server, username=self.username, private_key=self.lab_key_path) as sftp:
            if not sftp.exists(remoteSbuildPath):
                sftp.makedirs(remoteBasePath)
                remoteArchPath = os.path.join(remoteBasePath, archName)
                sftp.put(self.local_arch_path, remoteArchPath)
                sftp.execute('cd {path} && tar -xf {arch} && rm {arch}'.format(path=remoteBasePath, arch=archName))
                sftp.execute('chmod -R 777 {}'.format(remoteBasePath))
            sftp.close()

        packagePath = os.path.join(self.local_path, '{}-upgrade-CURRENT.tgz'.format(self.project))
        upgradePath = os.path.join(self.upgrade_base_dir, self.project)

        print("Extract {} in local {}\n".format(packagePath.split('/')[-1], upgradePath))
        self.call_command('mkdir -p {}'.format(upgradePath))
        self.call_command('tar -xf {} -C {}'.format(packagePath, upgradePath))

    def upgrade(self):
        """Upgrade STB"""

        client = pysftp.paramiko.SSHClient()
        known_host_path = os.path.join('~', '.ssh', 'known_hosts')
        client.load_host_keys(os.path.expanduser(known_host_path))

        upgradeUrl = os.path.join(self.upgrade_base_url, self.project)
        print('Upgrade STB with package {}\n'.format(upgradeUrl))
        client.connect(self.ip, username='admin', key_filename=self.key_path, timeout=10)

        time.sleep(5)
        client.exec_command('upgrade --with-gui --upgrade-server {}'.format(upgradeUrl))

        print('Wait for upgrade and reboot')
        time.sleep(120)
        client.exec_command('/sbin/reboot')
        client.close()

        print('Wait for activation and check upgrade status')
        time.sleep(120)
        client.connect(self.ip, username='admin', key_filename=self.key_path)
        stdin, stdout, stderr = client.exec_command("/usr/local/bin/setnv | grep SV_VERSION | cut -d'=' -f2")
        self.upgrade_succeed = True if stdout.readlines()[0].rstrip() == self.version_md5_hash else False
        client.close()

    def notify(self):
        """Send email with confirmations"""

        msg = MIMEMultipart()

        if (self.upgrade_succeed):
            message='Software {} from branch: {} was installed succesfully on STB: {}! Software hash: {}.'.format(self.project, self.branch, self.ip, self.version_md5_hash)
            subject="Automatic software upgrade SUCCEED"
        else:
            message='Software {} from branch: {} was not installed successfully on STB: {}! Currently installed version is different to expected: {}.'.format(self.project, self.branch, self.ip, self.version_md5_hash)
            subject="Automatic software upgrade FAILED"

        msg = MIMEMultipart()

        msg['From'] = self.from_mail_address
        msg['To'] = self.to_mail_address
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        server = SMTP()
        server.connect()
        server.sendmail(from_addr=self.from_mail_address, to_addrs=self.to_mail_address, msg=msg.as_string())
        server.quit()

        print(message)

    def clean(self):
        """Remove unneeded files"""

        self.call_command('rm {}'.format(self.local_arch_path))
        self.call_command('rm -rf {}'.format(self.local_path))
        self.call_command('rm -rf {}/{}'.format(self.upgrade_base_dir, self.project))

    def upgrade_box(self, upgrade_params: Dict[str, str]):
        self.project = upgrade_params['PROJECT']
        self.branch = upgrade_params['BRANCH']
        self.ip = upgrade_params['IP']
        #self.key_path = upgrade_params['KEY_PATH']

        '''
        temporary hack, should be fix soon
        map project name to path
        '''

        if 'millicom_prod' in self.project:
            self.key_path = '/home/bgaik/.ssh/stbkeys/id_rsa_millicom'
        elif 'millicom' in self.project:
            self.key_path = '/home/bgaik/.ssh/stbkeys/id_rsa_dta'
        elif 'qb' in self.project:
            self.key_path = '/home/bgaik/.ssh/stbkeys/id_rsa_generic'

        print('#'*60)
        print('Upgrade params:')
        for k, v in upgrade_params.items():
            if k and v: print('{} = {}'.format(k, v))
        print('#'*60)

        self.prepare()
        self.build()
        self.copy()
        self.upgrade()
        self.notify()
        self.clean()

    def upgrade_all_boxes(self):
        self.upgrade_type = 'all'
        for box in self.all_boxes:
            self.upgrade_box(box)

    def upgrade_box_with_local_sbuild(self, upgrade_params: Dict[str, str]):
        self.upgrade_type = 'local'
        self.upgrade_box(upgrade_params)

    @staticmethod
    def helper():
        epilog=textwrap.dedent('''\
        Example of usage:
        ./{scriptName} -h
        ./{scriptName} --type all
        ./{scriptName} --type single --ip 10.136.2015.153 --project qb-arion7584a1-cubitvexp4-conax --branch 3800 --key /home/bgaik/.ssh/stbkeys/id_rsa_generic
        ./{scriptName} --type rc --ip 10.136.2015.153 --project millicom-kaon7581b0-cubitv-viewrightdvb-4.0rc2 --key /home/bgaik/.ssh/stbkeys/id_rsa_generic
        ./{scriptName} --type local --ip 10.136.2015.153 --sbuild qb-arion7584a1-cubitvexp4-conax --key /home/bgaik/.ssh/stbkeys/id_rsa_generic'''
        .format(scriptName=os.path.basename(__file__)))

        parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description='Script is used to upgrade boxes in lab.',
                                         epilog=epilog)

        parser.add_argument('--type', type=str, help=r"'single' box with params, 'all' boxes located in conf.json, 'local' sbuild or 'rc'")
        parser.add_argument('--ip', type=str)
        parser.add_argument('--project', type=str)
        parser.add_argument('--branch', type=str)
        parser.add_argument('--key', type=str)
        parser.add_argument('--path', type=str)
        parser.add_argument('--sbuild', type=str)
        return parser.parse_args()

def main():
    """
    Run a worker which will try to build projects from branches.
    All parameters are taken from conf.json file.
    """

    args = Upgrader.helper()

    config_file = 'conf.json'
    with open(config_file) as f:
        data = json.load(f)

    upgradeData = data['UPGRADE']
    upgrader = Upgrader(upgradeData)
    if args.type == 'all':
        upgrader.upgrade_all_boxes()
    elif args.type == 'single' and args.ip and args.project and args.branch and args.key:
        upgrade_params = {'PROJECT': args.project, 'BRANCH_PATH': '', 'BRANCH': args.branch, 'IP': args.ip, 'KEY_PATH': args.key}
        upgrader.upgrade_box(upgrade_params)
    elif args.type == 'sbuild' and args.ip and args.sbuild and args.key:
        upgrade_params = {'PROJECT': args.project, 'BRANCH_PATH': '', 'BRANCH': '', 'IP': args.ip, 'KEY_PATH': args.key}
        upgrader.upgrade_box_with_local_sbuild(upgrade_params)
    else:
        assert(False)

if __name__ == "__main__":
    main()
