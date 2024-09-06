#!/usr/bin/env python3
#
# comp_arl.py - compare the contents of two ARL-formatted files
#
# Change history:
#  5 Sep 2024 - initial.

import argparse
import logging
import matplotlib.pyplot as plt
import numpy
import sys

from hysplitdata import read_met_file

logger = logging.getLogger(__name__)


def compute_error_measures(d1: list, d2: list) -> dict:
   prop = dict()

   # Error - may be reused for plotting
   err = numpy.subtract(d1, d2)
   prop['err'] = err

   # Max absolute error
   abs_err = numpy.absolute(err)
   prop['max_abs_error'] = numpy.max(abs_err)

   # Mean absolute scaled error (MASE)
   sum_abs_err = numpy.sum(abs_err)
   d1_mean = numpy.mean(d1)
   d1_diff = numpy.absolute(numpy.subtract(d1, d1_mean))
   d1_diff_sum = numpy.sum(d1_diff)
   prop['MASE'] = sum_abs_err / d1_diff_sum

   return prop


def create_comparison_plots(record_identifier: str,
                            d1: list,
                            d2: list,
                            err: list):
   # err = d1 - d2 and it is an array.
   fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.5, 11.))

   ax1.scatter(d1, d2, s=10, c='none', edgecolors='r', marker='o')
   ax1.set_title(record_identifier)
   ax1.grid(True, linestyle='--')

   ax2.plot(err, 'bo', markersize=2)
   ax2.set_title(record_identifier)
   ax2.set_xlabel('flat array index')
   ax2.set_ylabel('difference')
   ax2.grid(True, axis='y', linestyle='--')
   ax2.set_xlim([0, len(err)])

   plt.tight_layout()

   plt.savefig(record_identifier + '.png')

   plt.close()


def main():
   parser = argparse.ArgumentParser(description='Examines ARL-formatted meterological data files.')
   parser.add_argument('--debug', '-d', action='store_true', default=False)
   parser.add_argument('--variable', '-v', default=None,
                       help='Variable name to examine (e.g. TEMP)')
   parser.add_argument('-n', type=int, default=10000,
                       help='Max number of records to examine')
   parser.add_argument('arlfile1', type=str, help='first ARL-formatted meteorological file')
   parser.add_argument('arlfile2', type=str, help='second ARL-formatted meteorological file')
   args = parser.parse_args()

   # Change the logging level if necessary
   if args.debug:
      logging.getLogger().setLevel(logging.DEBUG)

   m1 = read_met_file(args.arlfile1)
   m2 = read_met_file(args.arlfile2)

   # Collect the specified variable.
   # All variables will be collected if the --variable option is not given.
   vars1 = m1.collect(args.variable)
   vars2 = m2.collect(args.variable)

   # For sumary
   diff_var_names = []  # Variable names that have different values
   ntotal_rec = 0  # The number of total variables (or records)
   ndiff_rec = 0  # The number of records that differ

   for k, v1 in enumerate(vars1):
      ntotal_rec += 1
      v2 = vars2[k]

      if v1.record_identifier != v2.record_identifier:
         logger.fatal('Cannot compare files of different structure')
         logger.fatal(f'{args.arlfile1}: {v1.record_identifier}')
         logger.fatal(f'{args.arlfile2}: {v2.record_identifier}')
         sys.exit(1)

      d1 = v1.data.flatten()
      d2 = v2.data.flatten()

      prop = compute_error_measures(d1, d2)

      # print messages when there is a difference
      if prop["max_abs_error"] != 0:
         ndiff_rec += 1
         print(f'{v1.record_identifier}:')
         print(f'  min {v1.min_value:g}, max {v1.max_value:g}')
         print(f'  max abs error {prop["max_abs_error"]:g}')
         print(f'  mean abs scaled error {prop["MASE"]:g}')
         print('')

         create_comparison_plots(v1.record_id_for_filename,
                                 d1,
                                 d2,
                                 prop['err'])

         if v1.kvar not in diff_var_names:
            diff_var_names.append(v1.kvar)

      if ntotal_rec >= args.n:
         break

   if len(diff_var_names) > 0:
      print('Summary:')
      print(f'  number of records: {ntotal_rec}')
      print(f'  number of different records: {ndiff_rec}')
      print(f'  names of different records: {diff_var_names}')


if __name__ == '__main__':
   logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                       format='%(asctime)s.%(msecs)03d %(levelname)s - %(message)s',
                       datefmt='%H:%M:%S')
   main()
   sys.exit(0)

