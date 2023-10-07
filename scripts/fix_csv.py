
'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import argparse
import csv

def fix_csv(filespec, output=None):
    try:
        with open(filespec, 'r', encoding='utf-8') as fi:
            csv_i = csv.reader(fi)
            if not output:
                output = filespec[:-4] + '_fixed.csv'
            with open(output, 'w', encoding='utf-8', newline='') as fo:
                csv_o = csv.writer(fo, quoting=csv.QUOTE_NONNUMERIC)
                csv_o.writerows(csv_i)
        print(f"Wrote {output}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix CSV file for loading into SQLite3")
    parser.add_argument('filespec', help="path to a csv file to fix")
    parser.add_argument('-o', '--output', help="path to a new csv file")
    args = parser.parse_args()
    fix_csv(args.filespec, args.output)
