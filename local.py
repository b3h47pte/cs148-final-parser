import argparse
import json
import os
import glob
import sys
import subprocess
if __name__ == "__main__": 
    cmdParser = argparse.ArgumentParser(description='Parser')
    cmdParser.add_argument('--eid', required=True)
    cmdParser.add_argument('--option', required=True, choices=["main", "vara", "varb", "writeup"], type=str.lower)
    args = cmdParser.parse_args()

    with open('mapping.json') as fh:
        mapping = json.load(fh)

    if not args.eid in mapping:
        raise Exception("Oops! Can't find EID: " + args.eid)

    folder = "data/" + mapping[args.eid] + "/"
    filename = folder
    if args.option == "main":
        filename += "main_*"
    elif args.option == "vara":
        filename += "image_A_*"
    elif args.option == "varb":
        filename += "image_B_*"
    elif args.option == "writeup":
        filename += "writeup_*"
    files = glob.glob(filename)
    if not files:
        raise Exception("Oops! Can't find a file that matches: " + filename)

    if sys.platform == "win32":
        os.startfile(files[0])
    elif sys.platform == "darwin":
        subprocess.call(["open", files[0]])
    else:
        subprocess.call(["xdg-open", files[0]])
