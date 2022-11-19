
'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import argparse
import sys
import os
import csv

module_name = 'fix_csv.py'

##################################################

def main(argv):

    # arguments
    parser = argparse.ArgumentParser(description="Fix CSV file for loading into SQLite3")
    parser.add_argument('filespec', help="path to a csv file to fix")
    parser.add_argument('-d', '--debug', action="store_true", help="provide debugging information")
    parser.add_argument('-o', '--output', help="path to a new csv file - otherwise, _fixed is appended to filespec")
    args = parser.parse_args()

    if not os.path.exists(args.filespec):
        print(f"Error: file not found: {args.filespec}")
        return False

    if not args.filespec.endswith(".csv"):
        print(f"Error: file must be .csv")
        return False

    fi = open(args.filespec, 'U')

    if args.output:
        outfile = args.output
    else:
        outfile = args.filespec[:-4] + '_fixed.csv'

    fo = open(outfile, 'w', encoding='utf-8')

    csv_i = csv.reader(fi)  
    csv_o = csv.writer(fo, quoting=csv.QUOTE_NONNUMERIC)
        
    csv_o.writerows(csv_i)

    # for row in csv_i:
    #     csv_o.writerow(row)
            
    fi.close()
    fo.close()

    print(f"{module_name}: wrote {outfile}")

#############################################    
    
if __name__ == "__main__":
    main(sys.argv)

# end