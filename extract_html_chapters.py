#!/usr/bin/env python3

"""
Reads in literature chapters stored in HTML format and writes one text file for each book found.
"""

__author__ = "Todd Shore <errantlinguist+github@gmail.com>"
__copyright__ = "Copyright (C) 2018 Todd Shore"
__license__ = "Apache License, Version 2.0"

import argparse
import logging
import os
import re
from typing import Iterable, Iterator

from storygenerator.io import HTMLChapterReader, write_chapters

HTML_FILE_EXTENSION_PATTERN = re.compile("\.htm(l)", re.IGNORECASE)


def is_html_file(path: str) -> bool:
	ext = os.path.splitext(path)[1]
	match = HTML_FILE_EXTENSION_PATTERN.match(ext)
	return bool(match)


def walk_html_files(inpaths: Iterable[str]) -> Iterator[str]:
	for inpath in inpaths:
		for root, dirs, files in os.walk(inpath, followlinks=True):
			for file in files:
				filepath = os.path.join(root, file)
				if is_html_file(filepath):
					yield filepath


def __create_argparser() -> argparse.ArgumentParser:
	result = argparse.ArgumentParser(
		description="Reads in literature chapters stored in HTML format and writes one text file for each book found.")
	result.add_argument("inpaths", metavar="PATH", nargs='+',
						help="The paths to search for files to read.")
	result.add_argument("-o", "--outdir", metavar="PATH",
						help="The directory to write the extracted book data to.", required=True)
	result.add_argument("-d", "--debug", help="increase output verbosity",
						action="store_true")
	return result


def __main(args):
	if args.debug:
		logging.basicConfig(level=logging.DEBUG)

	inpaths = args.inpaths
	print("Will look for data under {}.".format(inpaths))
	reader = HTMLChapterReader()
	infiles = walk_html_files(inpaths)
	book_chapters = dict(reader(infiles))
	print("Read data for {} book(s): {}".format(len(book_chapters), sorted(book_chapters.keys())))

	outdir = args.outdir
	os.makedirs(outdir, exist_ok=True)
	for book_title, chapters in book_chapters.items():
		outfile_path = os.path.join(outdir, book_title + ".txt")
		print("Writing book titled \"{}\" to \"{}\".".format(book_title, outfile_path))
		with open(outfile_path, 'w') as outf:
			write_chapters(chapters, outf)


if __name__ == "__main__":
	__main(__create_argparser().parse_args())
