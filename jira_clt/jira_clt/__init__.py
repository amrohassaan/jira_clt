##@package jira_clt
#
#Package for all jira command line tools.

import threading
import time
import sys


class ProgressBarDotPrinter():
    '''Prints dots to the screen to indicate progress on running commands'''

    def __init__(self, print_interval=5):
        self._stop = False
        self._print_interval = print_interval
        self._dot_printer_thread = threading.Thread(target=self._print_dots)

    def _print_dots(self):
        '''Thread target function that does the actual printing to console'''
        while not self._stop:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(self._print_interval)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def start(self):
        '''Start printing dots to console'''
        self._stop = False
        self._dot_printer_thread.start()

    def stop(self):
        '''Stop printing dots to console'''
        self._stop = True
        sys.stdout.write("DONE!")
        sys.stdout.flush()
        self._dot_printer_thread.join()


#copied from stackoverflow
class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value
