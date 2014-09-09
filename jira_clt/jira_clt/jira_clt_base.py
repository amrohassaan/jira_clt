##@package jira_clt
#
#Package for all jira command line tools


class JcltBase(object):
    '''Easy Jira Tool base

     Contains command functions for all JT classes to inherit from
    '''

    usage_description = "What does jira command do? Fill in the information in your class."

    def __init__(self, parser):
        parser.set_defaults(func=self.run)

    def run(self, arguements):
        '''Run the command line tool

        This should be overridden in your particular jira tool
        @param arguments list of parsed arguments for your tool
        '''
        raise NotImplementedError('This needs to be overridden in your command line tool.')
