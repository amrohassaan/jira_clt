##@package jira_clt
#
# Extracts jira efforts.

from __future__ import division
from __future__ import print_function
from jira_clt.jira_clt_base import JcltBase
from jira_clt import AutoVivification, ProgressBarDotPrinter
from getpass import getpass
from workdays import networkdays
import logging
import sys
import os
import datetime as dt
import csv
import re

try:
    from jira.client import JIRA
except:
    #TODO: log exception
    print ('jira-python not installed')
    sys.exit('1')

NEXT_MONTH = dt.datetime.now().date().month + 1


class JiraEffortsCLTException(Exception):
    pass


class JiraEffortsCLT(JcltBase):
    '''Extracts efforts from JIRA for an arbitrary time span.
    '''
    usage_description = "Extracts time spent per engineer on issues over arbitrary period of time\n" +\
                        "Example:\n efforts -j 'https://cards.linaro.org' -s 2014.6.1 -e 2014.7.1"
    dot_interval = 5
    jiraserver = None
    password = None
    username = None
    jira = None

    def __init__(self, parser):
        super(JiraEffortsCLT, self).__init__(parser)
        self.orphan_issues = set()
        self.pmo = set()
        self.efforts_dict = AutoVivification()
        self.start_date = str(dt.datetime.now().replace(day=1).date()).replace('-', '/')
        self.end_date = str(dt.datetime.now().replace(month=NEXT_MONTH,
                                                      day=1).date()).replace('-', '/')
        #TODO: initialize logger
        parser.add_argument('-j', '--jira', action='store', dest='jiraserver',
                            help='URL for JIRA server to connect to')
        parser.add_argument('-s', '--start', action='store', dest='start_date',
                            type=self._check_date_string, nargs=1,
                            help='Time period start date "Boundary start"')
        parser.add_argument('-e', '--end', action='store', dest='end_date',
                            type=self._check_date_string, nargs=1,
                            help='Time period end date "Boundary end"')
        parser.add_argument('-u', '--username', dest='username', help='Jira username')

    def _check_date_string(self, string_date):
        if re.match(r'^\d{4}[\--/]\d{1,2}[\--/]\d{1,2}$', string_date):
            return re.sub('[\--.]', '/', string_date)
        else:
            #TODO: log that error
            print ("You must pass date in yyyy[.][/][-]m[.][/][-]d format \n"
                   "e.g. 2014/6/1 or 2014.6.1 or 2014-6-1")
            exit(1)

    def _write_to_csv_file(self):
        issue_url = JiraEffortsCLT.jiraserver + "/browse/"
        home_dir = os.path.expanduser("~")
        efforts_period = re.sub('[.-/]', '-', self.start_date + "_to_" + self.end_date)
        csv_filename = os.path.join(home_dir,
                                    '%s-time-sheet.csv' % efforts_period)
        with open(csv_filename, 'wb') as timesheet_file:
            headers_list = ['EPIC', 'CARD', 'ENGINEER', 'EFFORTS PER CYCLE',
                            None, 'GO TO ISSUE']
            timesheet_writer = csv.writer(timesheet_file, delimiter=',')
            timesheet_writer.writerow(headers_list)
            for k, v in self.efforts_dict.iteritems():
                timesheet_writer.writerow([k[0], k[1], k[2], v['timespent'],
                                           None, issue_url + k[1]])
            if self.orphan_issues:
                timesheet_writer.writerow(['Orphan issues'])
                for item in self.orphan_issues:
                    timesheet_writer.writerow([item, None, None, None, None,
                                               issue_url + item])

    def _get_arbitrary_dates_only(self, worklog):
        time_portion_idx = worklog.started.index('T')
        date_started = worklog.started[:time_portion_idx]
        month_of_worklog = int(dt.datetime.strptime(date_started, "%Y-%m-%d").month)
        arbitrary_start_date = int(dt.datetime.strptime(self.start_date,
                                                        "%Y/%m/%d").month)
        arbitrary_end_date = int(dt.datetime.strptime(self.end_date,
                                                        "%Y/%m/%d").month)
        if arbitrary_start_date <= month_of_worklog <= arbitrary_end_date:
            return True
        else:
            return False

    def _get_issue_hierarchy(self, issues):
        non_orphans = []
        for issue in issues:            
            if issue.fields.issuetype.subtask:
                parent = JiraEffortsCLT.jira.issue(issue.fields.parent.id)
                parent = self._get_issue_parent(parent)
            else:
                #either a BP or CARD
                parent = self._get_issue_parent(issue)

            if parent is None: #example QA-898
                self.orphan_issues.add(issue.key)
                continue

            if parent.fields.issuetype.name.lower() == "blueprint":
                parent = self._get_issue_parent(parent)

            if parent.fields.issuetype.name.lower() != "roadmap card":
                rmc = self._get_issue_parent(parent)
                rme = self._get_issue_parent(rmc)
                if rmc and rme:
                    non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                         issue.fields.assignee.name):
                                        [(rme.key, rme.fields.issuetype.name),
                                         (rmc.key, rmc.fields.issuetype.name)]})
                #in case of CARD-1372 for Milosz. how do we deal with that.
                #it is the same scenario as if a Bp is linked to RME directly without RMC
                if rmc and not rme:
                    non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                         issue.fields.assignee.name):
                                        [(rmc.key, rmc.fields.issuetype.name),
                                         (rmc.key, rmc.fields.issuetype.name)]})
                continue
            #worklogged directly against RMC
            if parent.fields.issuetype.name.lower() == "roadmap card" and\
            issue.fields.issuetype.name.lower() == "roadmap card":
                non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                     issue.fields.assignee.name):
                                    [(parent.key, parent.fields.issuetype.name),
                                     (issue.key, issue.fields.issuetype.name)]})
            #BP linked directly to RMC so get RME(test this on staging)
            #or subtask linked directly under LINK without BP
            else:
                rme = self._get_issue_parent(parent)
                if rme:
                    non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                         issue.fields.assignee.name):
                                        [(rme.key, rme.fields.issuetype.name),
                                         (parent.key, parent.fields.issuetype.name)]})
                else:
                    non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                         issue.fields.assignee.name):
                                        [(parent.key, parent.fields.issuetype.name)]})
        if non_orphans:
            return non_orphans

    def _get_duration_of_workingdays(self, start, end):
        start_date = dt.datetime.strptime(start, '%Y/%m/%d').date()
        end_date = dt.datetime.strptime(end, '%Y/%m/%d').date()
        workingdays = networkdays(start_date, end_date) - 1

        return workingdays * 8 * 60 * 60

    def _get_issue_parent(self, blueprint):
        if blueprint.fields.issuelinks:
            link = next((link for link in blueprint.fields.issuelinks\
                    if link.type.name.lower() == 'implements'\
                    and hasattr(link, 'outwardIssue')\
                    and link.outwardIssue.fields.issuetype.name.lower() != 'new feature')
                        , None)
            if link:
                return JiraEffortsCLT.jira.issue(link.outwardIssue.id)
        #customfield_10301 is the EpicLink field
        if blueprint.fields.customfield_10301:
            return JiraEffortsCLT.jira.issue(blueprint.fields.customfield_10301)

        return None

    def run(self, arguments):
        '''Overrides base class's run'''
        if arguments.jiraserver:
            JiraEffortsCLT.jiraserver = arguments.jiraserver
            #TODO: add check to config value for jira server as well.

        if arguments.start_date and arguments.end_date:
            self.start_date = arguments.start_date[0]
            self.end_date = arguments.end_date[0]

        secs_in_time_period = self._get_duration_of_workingdays(self.start_date,
                                                              self.end_date)
        JiraEffortsCLT.username = arguments.username

        if not arguments.username:
            JiraEffortsCLT.username = raw_input("Username: ")
        JiraEffortsCLT.password = getpass("Password(%s): " % JiraEffortsCLT.username)

        try:
            JiraEffortsCLT.jira = JIRA(options={'server': arguments.jiraserver,
                                                'verify': False},
                                       basic_auth=(JiraEffortsCLT.username,
                                                   JiraEffortsCLT.password))
        except JiraEffortsCLTException as e:
            print ("Login Error: %s" % e)
            raise

        worklogs_jql = 'issue IN workLoggedBetween("%s","%s")' % (self.start_date,
                                                                  self.end_date)
        try:
            dot_printer = ProgressBarDotPrinter(JiraEffortsCLT.dot_interval)
            dot_printer.start()
            issues = set(JiraEffortsCLT.jira.search_issues(worklogs_jql,
                                                           maxResults=500))
            #TODO: print message to user and exit if no issues this month
            for issue in issues:
                if issue.fields.project.key.lower() == "pmo":
                    self.pmo.add(issue)

            issues -= self.pmo
            issue_parents_list = self._get_issue_hierarchy(issues)

            for item in issue_parents_list:
                #issues keys are tuples in form of (issue key, issue type)
                issue_key = item.keys()[0][0]
                issue_assignee = item.keys()[0][2]
                parents_list = item.values()[0]
                #grandpa and parent tuples have (issue key, issue type) format
                # e.g.('TCWG-11','Roadmap Card')
                rme_tuple = parents_list[0]
                rmc_tuple = parents_list[1]
                #TODO: perform sanity check if there is only one RMC parent
                #in case a BP was linked directly to RME or linked to
                #RMC but no RME exists (odd scenarios)
                worklogs = JiraEffortsCLT.jira.worklogs(issue_key)
                cur_month_worklogs = filter(self._get_arbitrary_dates_only,
                                            worklogs)
                if not (rme_tuple[0], rmc_tuple[0],
                        issue_assignee) in self.efforts_dict.keys():
                    self.efforts_dict[(rme_tuple[0],
                                       rmc_tuple[0],
                                       issue_assignee)]['timespent'] = 0
                    for log in cur_month_worklogs:
                        self.efforts_dict[(rme_tuple[0],
                                           rmc_tuple[0],
                                           issue_assignee)]['timespent'] = \
                                           round(self.efforts_dict.get((rme_tuple[0],
                                                                        rmc_tuple[0],
                                                                        issue_assignee)).get('timespent') + \
                                                 log.timeSpentSeconds / secs_in_time_period, 2)
                else:
                    for log in cur_month_worklogs:
                        self.efforts_dict[(rme_tuple[0],
                                           rmc_tuple[0],
                                           issue_assignee)]['timespent'] = \
                                           round(self.efforts_dict.get((rme_tuple[0],
                                                                        rmc_tuple[0],
                                                                        issue_assignee)).get('timespent') + \
                                                 log.timeSpentSeconds /secs_in_time_period, 2)
        except Exception as e:
            print (e)
            raise

        else:
            if self.efforts_dict:
                self._write_to_csv_file()

        finally:
            dot_printer.stop()
