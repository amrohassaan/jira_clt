##@package jira_clt
#
# Extracts jira efforts

from __future__ import division
from __future__ import print_function
from jira_clt.jira_clt_base import JcltBase
from jira_clt import AutoVivification
from getpass import getpass
from workdays import networkdays
from configobj import ConfigObj
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
import logging
import sys
import os
import datetime as dt
import calendar
import csv
import re
import subprocess

try:
    from jira.client import JIRA
    from jira.exceptions import JIRAError
except:
    print ('jira-python not installed')
    sys.exit('1')


NEXT_MONTH = dt.datetime.now().date().month + 1
COMPONENTS = {'Android': 'andr',
              'Android Engineering': 'ae',
              'ARMLT': 'armlt',
              'Broadcom LT': 'blt',
              'Builds and Baselines': 'bb',
              'Fujitsu LT': 'flt',
              'Graphics WG': 'gwg',
              'Hisilicon LT': 'hlt',
              'Kernel WG': 'kwg',
              'LAB': 'lab',
              'LAVA': 'lava',
              'LEG - Linaro Enterprise Group': 'leg',
              'LHG - Linaro Home Group': 'lhg',
              'LMG - Linaro Mobile Group': 'lmg',
              'LNG - Linaro Networking Group': 'lng',
              'LSK': 'lsk',
              'OCTO': 'octo',
              'Power Management WG': 'pmwg',
              'QA Services': 'qa',
              'Qualcomm LT': 'qlt',
              'Security WG': 'swg',
              'ST LT': 'stlt',
              'Systems': 'sys',
              'Toolchain WG': 'tcwg',
              'Virtualisation': 'virt'}
COMPONENTS_HELP = "\n".join(["================================================",
                             "||'QA Services'                   ||OR|| qa   ||",
                             "||'Virtualisation'                ||OR|| virt ||",
                             "||'LEG - Linaro Enterprise Group' ||OR|| leg  ||",
                             "||'LMG - Linaro Mobile Group'     ||OR|| lmg  ||",
                             "||'OCTO'                          ||OR|| octo ||",
                             "||'LAVA'                          ||OR|| lava ||",
                             "||'Android'                       ||OR|| andr ||",
                             "||'LHG - Linaro Home Group'       ||OR|| lhg  ||",
                             "||'LSK'                           ||OR|| lsk  ||",
                             "||'ARMLT'                         ||OR|| armlt||",
                             "||'Broadcom LT'                   ||OR|| blt  ||",
                             "||'Power Management WG'           ||OR|| pmwg ||",
                             "||'LNG - Linaro Networking Group' ||OR|| lng  ||",
                             "||'Builds and Baselines'          ||OR|| bb   ||",
                             "||'Graphics WG'                   ||OR|| gwg  ||",
                             "||'Toolchain WG'                  ||OR|| tcwg ||",
                             "||'Fujitsu LT'                    ||OR|| flt  ||",
                             "||'Hisilicon LT'                  ||OR|| hlt  ||",
                             "||'Android Engineering'           ||OR|| ae   ||",
                             "||'LAB'                           ||OR|| lab  ||",
                             "||'Security WG'                   ||OR|| swg  ||",
                             "||'Kernel WG'                     ||OR|| kwg  ||",
                             "||'Qualcomm LT'                   ||OR|| qlt  ||",
                             "||'ST LT'                         ||OR|| stlt ||",
                             "||'Systems'                       ||OR|| sys  ||",
                             "================================================"])
MISSING_ARG_ERROR = ''.join(['Missing %s! Please add to config or provide \n',
                             'on command line with "%s" option'])


def getlastday(year, month, daytofind):
    monthrange = calendar.monthrange(year, month)
    lastday = monthrange[1]
    while True:
        current_day = calendar.weekday(year, month, lastday)
        if current_day != daytofind:
            lastday -= 1
        else:
            return dt.date(year, month, lastday)

FRIDAY_AFTER_RELEASE = getlastday(dt.datetime.today().year,
                                  dt.datetime.today().month,
                                  calendar.FRIDAY)
NEXT_RELEASE_MONTH = FRIDAY_AFTER_RELEASE + relativedelta(months=+1)
NEXT_RELEASE_DATE = getlastday(NEXT_RELEASE_MONTH.year,
                               NEXT_RELEASE_MONTH.month,
                               calendar.THURSDAY)
CONFIG_FILE = os.path.expanduser('~') + '/.efforts.ini'
CONF_INITIALIZER = OrderedDict([('DEFAULT',
                                 OrderedDict([('jira-server',
                                               'https://cards.linaro.org'),
                                              ('username', 'amro'),
                                              ('password', 'pass'),
                                              ('start-date', FRIDAY_AFTER_RELEASE.strftime('%Y/%m/%d')),
                                              ('end-date', NEXT_RELEASE_DATE.strftime('%Y/%m/%d'))
                                              ])
                                 )]
                               )


class JiraEffortsCLTException(Exception):
    pass


class JiraEffortsCLT(JcltBase):
    '''Extracts efforts from JIRA for an arbitrary time span.
    '''
    usage_description = "Extracts time spent per engineer on issues over arbitrary period of time.\n\n" +\
                        "=============================================================================================\n" +\
                        "||+ 'efforts' accepts command line arg and values from config file '~/.efforts.ini'        ||\n"+\
                        "||+ Command line args override config file values.                                         ||\n"+\
                        "||+ On first run, it creates the config file in user homedir and opens it to user          ||\n"+\
                        "||   to fill it.                                                                           ||\n"+\
                        "||+ Config has 'DEFAULT' section which extracts efforts for all components. And a section  ||\n"+\
                        "||   for each component.                                                                   ||\n"+\
                        "||+ Release cycle dates are autopopulated in the config 'DEFAULT' section. If interested   ||\n"+\
                        "||   in extracting individual components, user has to specify component dates ONLY.        ||\n"+\
                        "||   Other components arguments (server..etc) map to 'DEFAULT' section unless              ||\n"+\
                        "||   user input other values for those arguments in components section.                    ||\n"+\
                        "=============================================================================================\n"+\
                        "Example-1 (collect efforts for all components from start to end date using config file default values):\n"+\
                        "\t efforts \n\n" +\
                        "Example-2 (collect efforts for 'LAVA' components only using config LAVA section):\n"+\
                        "\t efforts -m lava\n\n" +\
                        "Example-3 (collect efforts for 'LAVA' and 'QA' components. If no command line dates args,\n"+\
                        "          it will use 'DEFAULT' section args. Extracting efforts for multiple components\n"+\
                        "          will NOT use config component sections) :\n"+\
                        "\t efforts -m lava,qa \n\n" +\
                        "Example-4 (collect efforts for all components from start to end date (args override config)):\n"+\
                        "\t efforts -j 'https://cards.linaro.org' -s 2014.6.1 -e 2014.6.21\n\n" +\
                        "Example-5 (collect efforts ONLY for LAB component from start to end date (args override config)):\n "+\
                        "\t effort -j 'https://cards.linaro.org' -s 2014.6.1 -e 2014.7.1 -m lab\n\n"+\
                        "Example-6 (collect efforts for multiple comma-separated components from start to end date (args override config)):\n"+\
                        "\t effort -j 'https://cards.linaro.org' -s 2014.6.1 -e 2014.7.1 -m lab,sys,lava,lng\n\n"+\
                        "Example-7 (opens config for editing):\n"+\
                        "\t effort config\n\n" +\
                        "Example-8 (updates start and end dates in the config DEFAULT section to current month release cycle):\n"+\
                        "\t effort uprel"
    jiraserver = None
    password = None
    username = None
    jira = None

    def __init__(self, parser):
        super(JiraEffortsCLT, self).__init__(parser)
        if len(sys.argv) > 1 and sys.argv[1].lower() == "config":
            if os.path.isfile(CONFIG_FILE):
                open_config_for_editing()
                exit(0)
        if len(sys.argv) > 1 and sys.argv[1].lower() == "uprel":
            if os.path.isfile(CONFIG_FILE):
                self.config = ConfigObj(CONFIG_FILE)
                default_section = self.config['DEFAULT']
                default_section['start-date'] = FRIDAY_AFTER_RELEASE.strftime('%Y/%m/%d')
                default_section['end-date'] = NEXT_RELEASE_DATE.strftime('%Y/%m/%d')
                self.config.write()
                print('Config: default start and end dates updated to current release cycle successfully.')
                exit(0)
            else:
                print("Config file has never been created.\n"
                      "Type 'efforts' to have it created in your home directory.")
                exit(0)
        if not os.path.isfile(CONFIG_FILE):
            self.config = ConfigObj(CONF_INITIALIZER, write_empty_values=True)
            for value in COMPONENTS.itervalues():
                self.config[value] = OrderedDict([('server', '%(jira-server)s'),
                                                  ('user', '%(username)s'),
                                                  ('pass', '%(password)s'),
                                                  ('start', ''),
                                                  ('end', '')])

            self.config.filename = CONFIG_FILE
            self.config.initial_comment.append('To use this config please fill in all '
                                               'the arguments under the default section')
            self.config.initial_comment.append('Also fill in the start and end dates'
                                               'for the component(s) you want to extract efforts for')
            self.config.write()
            open_config_for_editing()
        self.config = ConfigObj(CONFIG_FILE)
        self.logger = logging.getLogger('jira_clt.efforts')
        self.orphan_issues = set()
        self.pmo = set()
        self.retrieved_components = set()
        self.efforts_dict = AutoVivification()
        self.start_date = str(dt.datetime.now().replace(day=1).date()).replace('-', '/')
        self.end_date = str(dt.datetime.now().replace(month=NEXT_MONTH,
                                                      day=1).date()).replace('-', '/')
        self.components = None

        parser.add_argument('-j', '--jira', action='store', dest='jiraserver',
                            help='URL for JIRA server to connect to')
        parser.add_argument('-s', '--start', action='store', dest='start_date',
                            type=self._check_date_string, nargs=1,
                            help='Time period start date "Boundary start"')
        parser.add_argument('-e', '--end', action='store', dest='end_date',
                            type=self._check_date_string, nargs=1,
                            help='Time period end date "Boundary end"')
        parser.add_argument('-m', '--component', action='store', dest='components',
                            type=self._parse_components,
                            help="Collect efforts for a specific single or comma-separated list of component(s).\n"
                            "Valid components arguments are listed below. ONLY short version is accepted.\n"
                            "short version is case insensitive. e.g. LNG or lng:\n"
                            + COMPONENTS_HELP)
        parser.add_argument('-u', '--username', dest='username', help='Jira username')

    def _parse_components(self, string_components):
        components_list = []
        components_long = set()
        components_short = set()
        for k, v in COMPONENTS.iteritems():
            components_long.add(k)
            components_short.add(v.lower())

        for component in string_components.split(','):
            if component.lower() not in components_short:
                print ("Component(s) argument not valid!")
                print ("Type 'efforts' or 'efforts -h' for help on valid component names!\n")
                exit(1)
            else:
                for k in COMPONENTS.keys():
                    if COMPONENTS[k].lower() == component.lower():
                        components_list.append(k)
                        break
        return components_list

    def _check_date_string(self, string_date):
        if re.match(r'^\d{4}[\--/]\d{1,2}[\--/]\d{1,2}$', string_date):
            return re.sub('[\--.]', '/', string_date)
        else:
            print ("You must pass date in yyyy[.][/][-]m[.][/][-]d format \n"
                  "e.g. 2014/6/1 or 2014.6.1 or 2014-6-1")
            exit(1)

    def _write_to_csv_file(self):
        issue_url = JiraEffortsCLT.jiraserver + "/browse/"
        headers_list = ['EPIC', 'CARD', 'ENGINEER', 'EFFORTS PER CYCLE',
                        'COMPONENT(S)', None, 'GO TO ISSUE']
        timesheet_writer = csv.writer(sys.stdout, delimiter='\t')
        timesheet_writer.writerow(headers_list)
        for k, v in self.efforts_dict.iteritems():
            timesheet_writer.writerow([k[0], k[1], k[2], v['timespent'],
                                       v['components'], None,
                                       issue_url + k[1]])
        if self.orphan_issues:
            timesheet_writer.writerow(['Orphan issues'])
            for item in self.orphan_issues:
                timesheet_writer.writerow([item, None, None, None, None,
                                           None, issue_url + item])

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
            if not issue.fields.assignee:
                self.logger.debug("issue %s has no assignee. "
                                  "Skipping work logs from this issue" % issue.key)
                self.orphan_issues.add(issue.key)
                continue

            if issue.fields.issuetype.subtask:
                parent = JiraEffortsCLT.jira.issue(issue.fields.parent.id)
                parent = self._get_issue_parent(parent)
            else:
                #either a BP or CARD
                parent = self._get_issue_parent(issue)

            if parent is None:
                self.orphan_issues.add(issue.key)
                continue
            #safeguard against issues of same level implementing each other 
            #(e.g. here Bp implementing Bp)
            if parent.fields.issuetype.name.lower() == "blueprint":
                parent = self._get_issue_parent(parent)

            if parent.fields.issuetype.name.lower() != "roadmap card":
                rmc = self._get_issue_parent(parent)
                rme = self._get_issue_parent(rmc)
                if rmc.fields.issuetype.name.lower() != "roadmap card":
                    self.orphan_issues.add(issue.key)
                    continue
                if rmc and rme:
                    self.logger.debug("issue:%s, parent:%s " % (issue.key, parent.key))
                    non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                         issue.fields.assignee.name):
                                        [(rme.key, rme.fields.issuetype.name),
                                         (rmc.key, rmc.fields.issuetype.name),
                                         self._get_rmc_components_names(rmc)]})
                #in case of CARD-1372 for Milosz. how do we deal with that.
                #it is the same scenario as if a Bp is linked to RME directly without RMC
                if rmc and not rme:
                    self.logger.debug("issue:%s, parent:%s " % (issue.key, parent.key))
                    non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                         issue.fields.assignee.name):
                                        [(rmc.key, rmc.fields.issuetype.name),
                                         (rmc.key, rmc.fields.issuetype.name),
                                         self._get_rmc_components_names(rmc)]})
                continue
            #worklogged directly against RMC
            if parent.fields.issuetype.name.lower() == "roadmap card" and\
            issue.fields.issuetype.name.lower() == "roadmap card":
                self.logger.debug("issue:%s, parent:%s " % (issue.key, parent.key))
                non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                     issue.fields.assignee.name):
                                    [(parent.key, parent.fields.issuetype.name),
                                     (issue.key, issue.fields.issuetype.name),
                                     self._get_rmc_components_names(issue)]})
            #BP linked directly to RMC so get RME(test this on staging)
            #or subtask linked directly under LINK without BP
            else:
                rme = self._get_issue_parent(parent)
                if rme:
                    self.logger.debug("issue:%s, parent:%s " % (issue.key, parent.key))
                    non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                         issue.fields.assignee.name):
                                        [(rme.key, rme.fields.issuetype.name),
                                         (parent.key, parent.fields.issuetype.name),
                                         self._get_rmc_components_names(parent)]})
                else:
                    self.logger.debug("issue:%s, parent:%s " % (issue.key, parent.key))
                    non_orphans.append({(issue.key, issue.fields.issuetype.name,
                                         issue.fields.assignee.name):
                                        [(parent.key, parent.fields.issuetype.name),
                                         (parent.key, parent.fields.issuetype.name),
                                         self._get_rmc_components_names(parent)]})
        if non_orphans:
            return non_orphans

    def _get_rmc_components_names(self,rmc):
        rmc_components = []
        if len(rmc.fields.components) > 0:
            for component in rmc.fields.components:
                rmc_components.append(component.name)
                self.retrieved_components.add(component.name)

            return rmc_components
        else:
            return None

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

    def set_console_level(self, log_level):
        if JiraEffortsCLT.console_handler:
            JiraEffortsCLT.console_handler.setLevel(log_level)

    def error_exit(self, argument, option):
        print(MISSING_ARG_ERROR % (argument, option))
        exit(1)

    def run(self, arguments):
        '''Overrides base class's run'''

        if arguments.components and len(sys.argv) == 3\
        and len(arguments.components) == 1:
            self.components = arguments.components
            section = self.config[COMPONENTS[self.components[0]]]
            self.start_date = section['start'] if section['start'] else \
                              self.error_exit('start date', '-s')
            self.end_date = section['end'] if section['end'] else \
                            self.error_exit('end date', '-e')
            JiraEffortsCLT.jiraserver = section['server'] if section['server'] else\
                              self.error_exit('jira server', '-j')
            JiraEffortsCLT.username = section['user'] if section['user'] else\
                                      self.error_exit('username', '-u')
            JiraEffortsCLT.password = section['pass']

        elif len(sys.argv) == 1:
            section = self.config['DEFAULT']
            self.start_date = section['start-date'] if section['start-date'] else \
                              self.error_exit('start date', '-s')
            self.end_date = section['end-date'] if section['end-date'] else \
                            self.error_exit('end date', '-e')
            JiraEffortsCLT.jiraserver = section['jira-server'] if section['jira-server'] else\
                              self.error_exit('jira server', '-j')
            JiraEffortsCLT.username = section['username'] if section['username'] else\
                                      self.error_exit('username', '-u')
            JiraEffortsCLT.password = section['password']

        else:
            if arguments.jiraserver:
                JiraEffortsCLT.jiraserver = arguments.jiraserver
            elif self.config['DEFAULT']['jira-server']:
                JiraEffortsCLT.jiraserver = self.config['DEFAULT']['jira-server']
            else:
                self.error_exit('jira-server', '-j')
            if arguments.start_date and arguments.end_date:
                self.start_date = arguments.start_date[0]
                self.end_date = arguments.end_date[0]
            else:
                self.start_date = self.config['DEFAULT']['start-date']
                self.end_date = self.config['DEFAULT']['end-date']
                print("Using default start and end dates:")
            if not self.start_date:
                self.error_exit('start-date', '-s')
            if not self.end_date:
                self.error_exit('end-date', '-e')
            if arguments.components:
                self.components = arguments.components
            if arguments.username:
                JiraEffortsCLT.username = arguments.username
            else:
                JiraEffortsCLT.username = self.config['DEFAULT']['username']
            if not JiraEffortsCLT.username:
                JiraEffortsCLT.username = raw_input("Username: ")
                self.config['DEFAULT']['username'] = JiraEffortsCLT.username

        start_date_obj = dt.datetime.strptime(self.start_date,
                                                  '%Y/%m/%d').date()
        #advance end day by one day to inculde end day in jql search
        end_date_obj = dt.datetime.strptime(self.end_date,
                                                '%Y/%m/%d').date() + \
                                                  relativedelta(days=+1)
        self.end_date = end_date_obj.strftime('%Y/%m/%d')
        if start_date_obj >= end_date_obj:
            print ("start date cannot be equal to or small than end date!")
            exit(1)
        if start_date_obj > dt.date.today():
            print("start date is bigger than today. Cannot use future start date!")
            exit(1)

        secs_in_time_period = (networkdays(start_date_obj,
                                           end_date_obj) - 1) * 8 * 60 * 60

        if not self.config['DEFAULT']['password']:
            JiraEffortsCLT.password = getpass("Password(%s): " % 
                                                  JiraEffortsCLT.username)
            self.config['DEFAULT']['password'] = JiraEffortsCLT.password

        if not JiraEffortsCLT.password:
            JiraEffortsCLT.password = self.config['DEFAULT']['password']

        try:
            JiraEffortsCLT.jira = JIRA(options={'server': JiraEffortsCLT.jiraserver,
                                                'verify': True},
                                       basic_auth=(JiraEffortsCLT.username,
                                                   JiraEffortsCLT.password),
                                       validate=True)
        except JIRAError as e:
            print ("Login Error! Username or password is invalid")
            exit(1)

        worklogs_jql = 'issue IN workLoggedBetween("%s","%s")' % (self.start_date,
                                                                  self.end_date)
        try:
            issues = set(JiraEffortsCLT.jira.search_issues(worklogs_jql,
                                                           maxResults=500))
            if len(issues) == 0:
                print ("Didn't find any any work logs for this period/given component!")
                exit(0)

            for issue in issues:
                if issue.fields.project.key.lower() == "pmo":
                    self.pmo.add(issue)

            issues -= self.pmo
            issue_parents_list = self._get_issue_hierarchy(issues)
            if self.components and not set(self.components) & self.retrieved_components:
                print("Found no worklogs for specified components in this period!")
                exit(1)

            for item in issue_parents_list:
                #issues keys are tuples in form of (issue key, issue type)
                issue_key = item.keys()[0][0]
                issue_assignee = item.keys()[0][2]
                parents_list = item.values()[0]
                #grandpa and parent tuples have (issue key, issue type) format
                # e.g.('TCWG-11','Roadmap Card')
                rme_tuple = parents_list[0]
                rmc_tuple = parents_list[1]
                components_set = set(component for component in parents_list[2])
                if self.components:
                    if not components_set & set(self.components):
                        continue
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
                    self.efforts_dict[(rme_tuple[0],
                                       rmc_tuple[0],
                                       issue_assignee)]['components'] = '|'.join(components_set).upper()
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
            exit(1)

        else:
            if self.efforts_dict:
                self._write_to_csv_file()


def open_config_for_editing():
        if sys.platform == 'linux' or sys.platform == 'linux2' or sys.platform == 'darwin':
                cmd = os.environ.get('EDITOR', 'vi') + " " + CONFIG_FILE
                #TODO: add elif for windows
        subprocess.call(cmd, shell=True)
