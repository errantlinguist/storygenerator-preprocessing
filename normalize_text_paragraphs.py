#!/usr/bin/env python3

"""
Reads in a text file and tries to put a single paragraph on each line, removing any line breaks e.g. in the middle of sentences.
"""

__author__ = "Todd Shore <errantlinguist+github@gmail.com>"
__copyright__ = "Copyright (C) 2018 Todd Shore"
__license__ = "Apache License, Version 2.0"

import argparse
import re
import sys

from typing import IO, Iterable, List, Tuple

CHAPTER_DELIM = "=" * 64
CHAPTER_DELIM_PATTERN = re.compile("=+")
WHITESPACE_PATTERN = re.compile("\\s+")


def __create_argparser() -> argparse.ArgumentParser:
	result = argparse.ArgumentParser(
		description="Reads in a text file and tries to put a single paragraph on each line, removing any line breaks e.g. in the middle of sentences.")
	result.add_argument("infile", metavar="PATH",
						help="The file to read.")
	return result


def group_chapter_pars(lines: Iterable[str]) -> List[Tuple[str, List[str]]]:
	result = []
	chapter_title = None
	chapter_pars = None
	current_par = None

	parse_chapter_title = True
	for line in lines:
		line = line.strip()
		if parse_chapter_title:
			chapter_title = line
			current_par = []
			chapter_pars = []
			parse_chapter_title = False
		else:
			if line:
				if CHAPTER_DELIM_PATTERN.match(line):
					parse_chapter_title = True
					if chapter_pars is not None:
						if current_par:
							chapter_pars.append(current_par)
							current_par = []
						result.append((chapter_title, chapter_pars))
					chapter_pars = []


				else:
					tokens = WHITESPACE_PATTERN.split(line)
					current_par.extend(tokens)
			else:
				# start a new paragraph
				if current_par:
					chapter_pars.append(" ".join(current_par))
					current_par = []

	chapter_pars.append(" ".join(current_par))
	result.append((chapter_title, chapter_pars))

	return result


def write_chapter_pars(chapter_title: str, pars: List[str], out: IO[str]):
	print(chapter_title, file=out)
	print("\n", file=out)
	for par in pars:
		print(par, file=out)


def __main(args):
	infile = args.infile
	print("Reading \"{}\".".format(infile), file=sys.stderr)
	with open(infile, 'r') as inf:
		chapter_pars = iter(group_chapter_pars(inf))

	chapter, pars = next(chapter_pars)
	write_chapter_pars(chapter, pars, sys.stdout)
	for chapter, pars in chapter_pars:
		print("\n", file=sys.stdout)
		print(CHAPTER_DELIM, file=sys.stdout)
		write_chapter_pars(chapter, pars, sys.stdout)


if __name__ == "__main__":
	__main(__create_argparser().parse_args())
