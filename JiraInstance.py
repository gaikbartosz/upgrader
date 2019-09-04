#!/usr/bin/env python3

from jira import JIRA
import datetime
import re


class JiraInstance:
    """
    Class which is response for creataing FixVersion, marking it as RELEASED and for annote tasks which where
    done within lastday.
    """
    def __init__(self, config):
        self.SERVER_ADDRESS = config["SERVER_ADDRESS"]
        self.USER = config["USER"]
        self.PASSWORD = config["PASSWORD"]
        self.PROJECT = config["PROJECT_TAG"]
        self.CHANGELOG_TAG = config["CHANGELOG_TAG"]
        self.tasks = []
        self.fixedVersion = None

        options = {
            'server': self.SERVER_ADDRESS
        }

        self.jira = JIRA(options, basic_auth=(self.USER, self.PASSWORD))

    def is_any_new_changeset_in_changelog(self) -> bool:
        """
        Check if there is any new changeset in changelog in Jira task
        """
        changelog_issue = self.jira.issue(self.CHANGELOG_TAG, fields='comment')
        changelog = self.jira.comments(changelog_issue)[-1]
        regexp = "{}-([1-9]+[0-9]*)".format(self.PROJECT)
        for line in changelog.body.splitlines():
            issueTag = re.search(regexp, line)
            if issueTag is None or issueTag is "":
                continue
            self.tasks.append(issueTag.group())

        return True if len(self.tasks) > 0 else False

    def add_fixed_version_to_tasks(self, fixed_version):
        """
        Create and add fixed version to tasks from chagnelog task pointed in conf.json
        """
        if fixed_version is None or fixed_version is "":
            print("Wrong fixed_version")
            return

        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        self.jira.create_version(name=(fixed_version), project=self.PROJECT, released=True, startDate=today_str,
                                 releaseDate=today_str)

        for task in self.tasks:
            print("Add fixed version to {}".format(task))
            issue = self.jira.issue(task, fields='fixVersions')
            issue.add_field_value('fixVersions', {'name': fixed_version})

        '''
        for task in self.tasks:
            print("Add fixed version to {}".format(task))
            fixVersions = []
            issue = self.jira.issue(task)
            for version in issue.fields.fixVersions:
                if version.name != fixVersions:
                    fixVersions.append({'name': version.name})
            fixVersions.append({'name': fixed_version})
            issue.update(fields={'fixVersions': fixVersions})
        '''
