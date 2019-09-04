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
Script which builds projects and copies them to remote location.
Remote location must be mounted in operating system,
so it is possible to easy copy/remove files.
"""

import os
import json
import glob
import subprocess
import time
from JiraInstance import JiraInstance


class Builder:
    """Class which is response for building projects based on config from conf.json."""

    debug_project: str
    secure_project: str
    generate_usb_recovery: bool
    work_dir: str
    branch: str
    debug_logo_filename: str
    secure_logo_filename: str
    debug_bootimage_filename: str
    secure_bootimage_filename: str
    remote_location: str
    remove_files_time_in_days: int
    build_dir: str
    sw_tag: str
    jira_instance: JiraInstance

    def __init__(self, build_config: dict, jira_config: dict):
        """Constructor of Builder class.

        Args:
        build_config (dict): Data taken from conf.json containing specific project data.
        jira_config (dict): Data taken from conf.json containing Jira data.
        """

        self.debug_project = build_config["DEBUG_PROJECT"]
        self.secure_project = build_config["SECURE_PROJECT"]
        self.generate_usb_recovery = build_config["GENERATE_USB_RECOVERY"]
        self.work_dir = build_config["WORK_DIR"]
        self.branch = build_config["BRANCH"]
        self.debug_logo_filename = build_config["DEBUG_LOGO_FILENAME"]
        self.secure_logo_filename = build_config["SECURE_LOGO_FILENAME"]
        self.debug_bootimage_filename = build_config["DEBUG_BOOTIMAGE_FILENAME"]
        self.secure_bootimage_filename = build_config["SECURE_BOOTIMAGE_FILENAME"]
        self.remote_location = build_config["REMOTE_LOCATION"]
        self.remove_files_time_in_days = int(build_config["REMOVE_FILES_AFTER_DAYS"])
        self.build_dir = os.path.join(self.work_dir, self.branch)
        self.sw_tag = None
        self.jira_instance = JiraInstance(jira_config)

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
            self.clean()
            exit(0)

    def clean(self):
        """
        Remove files created during building project.
        Source files are not removed, to prevent non-stop pulling files.
        """

        print("Cleaning ...")
        #self.call_command("rm -rf {}".format(os.path.join(self.build_dir, "sbuild-*")))
        #self.call_command("rm -rf {}".format(os.path.join(self.build_dir, "__temp")))
        print("Cleaning done.")

    def prepare_directories(self):
        """Prepare working directories."""

        print("Preparing working directories ...")
        os.makedirs(self.work_dir, exist_ok=True)
        os.makedirs(self.build_dir, exist_ok=True)
        os.chdir(self.build_dir)
        print("Done")

    def prepare_software_tag(self):
        """Prepare software tag based on current datetime."""

        print("Setting SRM_BUILD_ID ...")
        command = 'date +"%Y_%m_%d"'
        ps = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        self.sw_tag = str(ps.communicate()[0], "utf-8").rstrip("\n")
        os.system('export SRM_BUILD_ID={}'.format(self.sw_tag))
        print("Done: SRM_BUILD_ID={}".format(self.sw_tag))

    def prepare(self):
        """Prepare directories, files, software tag."""

        if self.jira_instance.is_any_new_changeset_in_changelog() is False:
            print("No changesets since last build. Finishing.")
            self.clean()
            exit(0)

        self.prepare_directories()

        print("Pulling branch {} to {} ...".format(self.branch, self.build_dir))
        self.call_command('nosilo pull {} -ym'.format(self.branch))
        print("Pulling done.")

        self.prepare_software_tag()

    def prepare_usb_recovery(self, sw_type: str, output_directory_path: str):
        """
        Generate USB Recovery.

        Args:
        sw_type (str): software type (Debug, Secure).
        output_directory_path (str): path to wich usb recovery files will be copied.
        """

        print("Generating USB recovery for {} software".format(sw_type))
        usb_recovery_path = os.path.join(sw_type, "USBRecovery")
        os.makedirs(usb_recovery_path, exist_ok=True)

        package = glob.glob(os.path.join(output_directory_path, "*tgz"))[0]
        assert len(package) > 0
        self.call_command("tar -vxf {} --wildcards --no-anchored 'BOOTIMAGE*'".format(package))

        bootimg_file = glob.glob("*BOOTIMAGE*")[0]
        assert len(bootimg_file) > 0

        if self.debug_bootimage_filename is not None and self.debug_bootimage_filename is not "":
            os.system("cp {} {}".format(bootimg_file,
                                        os.path.join(usb_recovery_path,
                                                     self.debug_bootimage_filename)))
        if self.secure_bootimage_filename is not None and self.secure_bootimage_filename is not "":
            os.system("cp {} {}".format(bootimg_file,
                                        os.path.join(usb_recovery_path,
                                                     self.secure_bootimage_filename)))

        os.system("tar -vxf {} --wildcards --no-anchored 'LOGO*'".format(package))
        logo_file = glob.glob("*LOGO*")[0]
        assert len(logo_file) > 0

        if self.debug_logo_filename is not None and self.debug_logo_filename is not "":
            os.system("cp {} {}".format(logo_file,
                                        os.path.join(usb_recovery_path,
                                                     self.debug_logo_filename)))
        if self.secure_logo_filename is not None and self.secure_logo_filename is not "":
            os.system("cp {} {}".format(logo_file,
                                        os.path.join(usb_recovery_path,
                                                     self.secure_logo_filename)))

        os.system("rm -rf {}".format(bootimg_file))
        os.system("rm -rf {}".format(logo_file))
        print("Done")

    def copy_packages_to_remote_location(self, directory: str):
        """Copy prepared packages and USB Recovery to remote location."""

        remote_location = os.path.join(self.remote_location, self.sw_tag)
        print("Copying packages to remote location: {}".format(remote_location))
        os.makedirs(remote_location, exist_ok=True)
        os.system("cp -r {} {}".format(directory, remote_location))

    def build(self, project: str, is_debug: bool):
        """
        Build single project. Software will be tagged by tag prepared in prepare() method.
        USB Recovery will be created with file names pointed in conf.json.

        Args:
            is_debug (bool): flag indicating if building software is debuf
        """

        print("Build project {}".format(project))
        if is_debug is True:
            self.call_command('export SRM_BUILD_ID={} &&  \
                              SvDebug=yes SvDebugBuild=yes SvKeepStack=yes \
                              pysilo --project {}'.format(self.sw_tag, project))
        else:
            self.call_command('export SRM_BUILD_ID={} \
                              && pysilo --project {}'.format(self.sw_tag, project))
        print("Build done.")

        upgrade_package = glob.glob(os.path.join("sbuild-{}".format(project), "*upgrade*.tgz"))[0]
        assert len(upgrade_package) > 0

        cmd = 'tar -ztf {} | grep "md5$"'.format(upgrade_package)
        ps = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        upgrade_file = str(ps.communicate()[0], "utf-8").rstrip("\n")
        assert len(upgrade_file) > 0

        cmd = "tar -O -zxf {} {} | head -n 1 | awk '{{print $1}}'".format(upgrade_package,
                                                                          upgrade_file)

        ps = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        version_md5_hash = str(ps.communicate()[0], "utf-8").rstrip("\n")
        assert len(version_md5_hash) > 0

        if is_debug is True:
            print("Cleaning before tagging ...")
            self.call_command('nosilo foreach "hg revert --all && hg purge"')
            print("Done")

            print("Tagging new software ...")
            self.call_command('nosilo tag {} --name=bluelab_{}_{}'.format(self.branch,
                                                                          self.sw_tag,
                                                                          version_md5_hash))

        sw_type_dir = "Debug" if is_debug is True else "Secure"
        os.makedirs(sw_type_dir, exist_ok=True)
        tmp_dir = "__temp"
        os.makedirs(tmp_dir, exist_ok=True)
        self.call_command("tar zxvf {} -C {}".format(upgrade_package, tmp_dir))
        self.call_command('cp {} {}'.format(upgrade_package, sw_type_dir))

        if self.generate_usb_recovery is True:
            self.prepare_usb_recovery(sw_type_dir, tmp_dir)

        if self.remote_location is not None and self.remote_location is not "":
            self.copy_packages_to_remote_location(sw_type_dir)

    def remove_oldest_packages(self):
        """
        Delete oldest than REMOVE_FILES_AFTER_DAYS nightly build packages from remote location.
        Value REMOVE_FILES_AFTER_DAYS is defined in conf.json.
        """

        current_time = time.time()
        for d in os.listdir(self.remote_location):
            dir_path = os.path.join(self.remote_location, d)
            if not os.path.isdir(dir_path):
                continue

            created = os.stat(dir_path).st_ctime
            if (current_time - created) // (24*3600) >= self.remove_files_time_in_days:
                os.system("rm -rf {}".format(self.remote_location, d))

    def build_nightly_projects(self):
        """
        Build single nightly project.

        This method aggregates all needed methods to build, tag and do update in Jira tasks.
        """

        self.prepare()

        #self.remove_oldest_packages()
        if self.debug_project is not None:
            print("Start building debug Nightly Build ...")
            self.build(self.debug_project, True)
            print("Done")
        else:
            print("Skipping build debug software")
        if self.secure_project is not None:
            print("Start building secure Nightly Build ...")
            self.build(self.secure_project, False)
            print("Done")
        else:
            print("Skipping build secure software")

        fixed_version = "CURRENT_{}".format(self.sw_tag)
        print("Updating fixedVersion {} for changelog tasks ...".format(fixed_version))
        self.jira_instance.add_fixed_version_to_tasks(fixed_version)
        print("Done")

        self.clean()

def main():
    """
    Run a worker which will try to build projects from branches.
    All parameters are taken from conf.json file.
    """

    config_file = "conf.json"
    with open(config_file) as f:
        data = json.load(f)

    for project in data["NIGHTLY_BUILD"]:
        builder = Builder(project, data["JIRA"])
        builder.build_nightly_projects()


if __name__ == "__main__":
    main()
