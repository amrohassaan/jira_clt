##@package jira_clt
#
# Jira clt tool to extract efforts and write them to a file.

import argparse
from jira_clt import jira_clt_efforts
#TODO: import logger


def main():
    '''Entry point for efforts.
    '''
    parser = argparse.ArgumentParser(description=jira_clt_efforts.JiraEffortsCLT.usage_description)
    parser.add_argument('-v', '--verbose', action='store_true',
                        dest='verbose', default=False,
                        help='Turn verbosity on')

    jira_clt_efforts.JiraEffortsCLT(parser)
    arguments = parser.parse_args()

    if arguments.verbose:
        #TODO: turn debugging level on logger
        pass
    else:
        #TODO: set logging level on console to info
        pass

    arguments.func(arguments)


if __name__ == '__main__':
    main()