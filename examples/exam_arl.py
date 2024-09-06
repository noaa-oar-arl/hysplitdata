#!/usr/bin/env python3
#
# exam_arl.py - examine meteorological variables in ARL-formatted files
#
# Change history:
#  2 Feb 2024 - Initial.
#  5 Sep 2024 - Clean up.

import argparse
import logging
import sys

from hysplitdata import read_met_file

logger = logging.getLogger(__name__)


def main():
   parser = argparse.ArgumentParser(description='Examines ARL-formatted meterological data files.')
   parser.add_argument('--debug', '-d', action='store_true', default=False)
   parser.add_argument('--variable', '-v', default=None,
                       help='Variable name to examine (e.g. TEMP)')
   parser.add_argument('arl_file', nargs='+',
                       help='ARL-formatted meteorology filename')
   args = parser.parse_args()

   # Change the logging level if necessary
   if args.debug:
      logging.getLogger().setLevel(logging.DEBUG)

   for fn in args.arl_file:
      m = read_met_file(fn)
      # Collect pressure grids in time series.
      for v in m.collect(args.variable):
         # Print the maximum and minimum values.
         print(f'{v.record_identifier}: max {v.max_value:g}, min {v.min_value:g}')


if __name__ == '__main__':
   logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                       format='%(asctime)s.%(msecs)03d %(levelname)s - %(message)s',
                       datefmt='%H:%M:%S')
   main()
   sys.exit(0)

