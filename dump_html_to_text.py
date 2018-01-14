#!/usr/bin/env python3

"""
Reads in HTML files with their names sorted lexicographically and then dumps the content to file in text form. This is useful for HTML files which don't work with the other code because they're broken in some way.
"""

__author__ = "Todd Shore <errantlinguist+github@gmail.com>"
__copyright__ = "Copyright (C) 2018 Todd Shore"
__license__ = "Apache License, Version 2.0"

import argparse
import os
import re
from typing import Iterable, Iterator

import html2text

from storygenerator import natural_keys

HTML_FILE_EXTENSION_PATTERN = re.compile("\.x?html?", re.IGNORECASE)


def is_html_file(path: str) -> bool:
	ext = os.path.splitext(path)[1]
	match = HTML_FILE_EXTENSION_PATTERN.match(ext)
	return bool(match)


def walk_html_files(inpaths: Iterable[str]) -> Iterator[str]:
	for inpath in inpaths:
		if os.path.isdir(inpath):
			for root, dirs, files in os.walk(inpath, followlinks=True):
				for file in files:
					filepath = os.path.join(root, file)
					if is_html_file(filepath):
						yield filepath
		elif is_html_file(inpath):
			yield inpath


def __create_argparser() -> argparse.ArgumentParser:
	result = argparse.ArgumentParser(
		description="Reads in HTML files with their names sorted lexicographically and then dumps the content to file in text form.")
	result.add_argument("inpaths", metavar="PATH", nargs='+',
						help="The paths to search for files to read.")
	return result


def __main(args):
	inpaths = args.inpaths
	print("Will look for data under {}.".format(inpaths))
	infiles = tuple(sorted(frozenset(walk_html_files(inpaths)), key=natural_keys))
	print("Will read {} file(s).".format(len(infiles)))

	text = []
	for infile in infiles:
		with open(infile, 'r') as inf:
			html = inf.read()
			text.append(html2text.html2text(html))

	for line in text:
		print(line)


if __name__ == "__main__":
	__main(__create_argparser().parse_args())
