#!/usr/bin/env python3

"""
Writes a lexicon to disk with the relevant counts of each word.

Use with e.g. "find . -type f -iname "*.txt" -exec ./write_token_counts.py {} +"
"""

__author__ = "Todd Shore <errantlinguist+github@gmail.com>"
__copyright__ = "Copyright (C) 2018 Todd Shore"
__license__ = "Apache License, Version 2.0"

import argparse
import csv
import sys
from typing import MutableMapping

import nltk


def __create_argparser() -> argparse.ArgumentParser:
	result = argparse.ArgumentParser(
		description="Writes a lexicon to disk with the relevant counts of each word.")
	result.add_argument("infiles", metavar="PATH", nargs="+",
						help="The files to read.")
	return result


def count_tokens(infile: str, counts: MutableMapping[str, int]):
	with open(infile, 'r') as inf:
		for line in inf:
			tokens = nltk.tokenize.word_tokenize(line)
			for token in tokens:
				try:
					counts[token] += 1
				except KeyError:
					counts[token] = 1


def __main(args):
	infiles = args.infiles
	counts = {}
	for infile in infiles:
		print("Reading \"{}\".".format(infile), file=sys.stderr)
		count_tokens(infile, counts)
	print("Found {} unique token type(s).".format(len(counts)), file=sys.stderr)

	writer = csv.writer(sys.stdout, dialect=csv.excel_tab)
	writer.writerow(("TOKEN", "COUNT"))
	for token, count in sorted(sorted(counts.items(), key=lambda item: item[0]), key=lambda item: item[1],
							   reverse=True):
		writer.writerow((token, count))


if __name__ == "__main__":
	__main(__create_argparser().parse_args())
