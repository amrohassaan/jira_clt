##@package jira_clt
#
# Jira clt tool to extract efforts and write them to a file..

import sys
import argparse
import logging
import jira_clt.logger
import os
from jira_clt import jira_clt_efforts
from jira_clt_efforts import CONFIG_FILE, open_config_for_editing


def main():
    '''Entry point for efforts.
    '''
    parser = argparse.ArgumentParser(description=jira_clt_efforts.JiraEffortsCLT.usage_description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-v', '--verbose', action='store_true',
                        dest='verbose', default=False,
                        help='Turn verbosity on for debugging.')

    jira_clt_efforts.JiraEffortsCLT(parser)    
#         parser.add_argument('--default', help=argparse.SUPPRESS)
#         parser.print_help()
#         sys.exit(1)

    arguments = parser.parse_args()
    jira_clt.logger.enable_console_logging(logging.WARN)
    if arguments.verbose:
        jira_clt.logger.set_console_level(logging.DEBUG)

    arguments.func(arguments)

if __name__ == '__main__':
    main()
