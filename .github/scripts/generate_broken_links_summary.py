#!/usr/bin/env python3
'''
@author: Peter Kahn
@contact: peter@swirl.today
@description: This script processes a CSV file containing URL check results, generates a fixed CSV file, and creates a summary report. Used in URL check processing.
'''

import argparse
import sys
import os
import csv
import logging

# Get the script name without the .py extension
script_name = os.path.basename(__file__).split('.')[0]

def main(argv):
    parser = argparse.ArgumentParser(description="Fix CSV file for loading into SQLite3")
    parser.add_argument('filespec', help="path to a csv file to fix")
    parser.add_argument('-o', '--output', help="path to a new csv file - otherwise, _fixed is appended to filespec")
    args = parser.parse_args()

    # Configure logging to write to both a file and the console
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.FileHandler('fix_csv.log'),
                            logging.StreamHandler(sys.stdout)
                        ])
    logger = logging.getLogger(script_name)

    if not os.path.exists(args.filespec):
        logger.error(f"File not found: {args.filespec}")
        return False

    if not args.filespec.endswith(".csv"):
        logger.error("File must be .csv")
        return False

    if args.output:
        outfile = args.output
    else:
        outfile = args.filespec[:-4] + '_fixed.csv'

    summary_file = args.filespec[:-4] + '_summary.md'
    logger.info(f"Reading {args.filespec}, Output Files: [Fixed Csv: {outfile}, Summary: {summary_file}]")

    passed_count = 0
    excluded_count = 0
    failed_count = 0
    unhandled_count = 0
    failed_urls = []
    unhandled_lines = []

    try:
        with open(args.filespec, 'r', encoding='utf-8') as fi, open(outfile, 'w', encoding='utf-8') as fo:
            csv_i = csv.reader(fi)
            csv_o = csv.writer(fo, quoting=csv.QUOTE_NONNUMERIC)

            for i, row in enumerate(csv_i):
                if i == 0:
                    csv_o.writerow(row)
                    continue

                url, result, filename = row
                if result == "passed":
                    passed_count += 1
                elif result == "excluded":
                    excluded_count += 1
                elif result == "failed":
                    failed_count += 1
                    failed_urls.append(f"{url}, {filename}")
                else:
                    unhandled_count += 1
                    unhandled_lines.append(f"Line {i}: {row}")

                csv_o.writerow([url, result, filename])

        logger.info(f"Finished processing CSV with {i} lines and Passed: {passed_count}, Excluded: {excluded_count}, Failed: {failed_count}, Unhandled: {unhandled_count}")

        # Generate summary
        with open(summary_file, 'w', encoding='utf-8') as summary:
            summary.write("## URL Check Summary\n")
            summary.write(f"*Passed:* {passed_count}\n")
            summary.write(f"*Excluded:* {excluded_count}\n")
            summary.write(f"*Failed:* {failed_count}\n")
            summary.write(f"*Unhandled Lines:* {unhandled_count}\n")

            if failed_count > 0:
                summary.write("\n### Failed URLs:\n")
                summary.write("* " + "\n* ".join(failed_urls) + "\n")

            if unhandled_count > 0:
                summary.write("\n### Unhandled Lines:\n")
                summary.write("* " + "\n* ".join(unhandled_lines) + "\n")

        logger.info(f"Summary stored {summary_file}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    main(sys.argv)

