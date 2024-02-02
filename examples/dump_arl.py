#!/usr/bin/env python3
#
# dump_arl.py - print header information in ARL-formatted meteorological data file
#
# Change history:
#  2 Feb 2024 - Initial.

import sys

from hysplitdata import read_met_file


def print_usage(prog_name: str):
    print(f'''\
 List meterological variables in ARL-formatted files
 
 Usage: {prog_name} FILENAME [FILENAME ...]''')


if __name__ == '__main__':
   if len(sys.argv) < 2:
      print_usage(sys.argv[0])
      sys.exit(1)

   for fn in sys.argv[1:]:
      m = read_met_file(fn)
      m.dump()

   sys.exit(0)