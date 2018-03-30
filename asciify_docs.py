#!/usr/bin/env python3

"""
Replaces as many unicode characters with ASCII analogues as possible.

Use with e.g. "find . -type f -iname "*.txt" -exec ./asciify_docs.py {} +"
"""

__author__ = "Todd Shore <errantlinguist+github@gmail.com>"
__copyright__ = "Copyright (C) 2018 Todd Shore"
__license__ = "Apache License, Version 2.0"

import argparse
import sys

import unidecode


def __create_argparser() -> argparse.ArgumentParser:
	result = argparse.ArgumentParser(
		description="Replaces as many unicode characters with ASCII analogues as possible.")
	result.add_argument("infiles", metavar="PATH", nargs="+",
						help="The files to read.")
	return result


def __main(args):
	infiles = args.infiles
	for infile in infiles:
		print("Reading \"{}\".".format(infile), file=sys.stderr)
		with open(infile, 'r') as inf:
			lines = inf.readlines()
		print("Writing \"{}\".".format(infile), file=sys.stderr)
		with open(infile, 'w') as outf:
			for line in lines:
				line = unidecode.unidecode(line)
				print(line, file=outf, end="")


if __name__ == "__main__":
	__main(__create_argparser().parse_args())
