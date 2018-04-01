#!/usr/bin/env python3

"""
Reads in literature chapters stored in EPUB format <http://idpf.org/epub> and writes one text file for each book found.
"""

__author__ = "Todd Shore <errantlinguist+github@gmail.com>"
__copyright__ = "Copyright (C) 2018 Todd Shore"
__license__ = "Apache License, Version 2.0"

import argparse
import logging
import os
import sys
from typing import Callable, Iterable, Iterator

import magic

from storygenerator_preprocessing import natural_keys
from storygenerator_preprocessing.io import EPUBChapterReader, write_chapters

EPUB_MIMETYPE = "application/epub+zip"


class MimetypeFileWalker(object):

	def __init__(self, mimetype_matcher: Callable[[str], bool]):
		self.mimetype_matcher = mimetype_matcher
		self.__mime = magic.Magic(mime=True)

	def __call__(self, inpaths: Iterable[str]) -> Iterator[str]:
		for inpath in inpaths:
			if os.path.isdir(inpath):
				for root, _, files in os.walk(inpath, followlinks=True):
					for file in files:
						filepath = os.path.join(root, file)
						mimetype = self.__mime.from_file(filepath)
						if self.mimetype_matcher(mimetype):
							yield filepath
			else:
				mimetype = self.__mime.from_file(inpath)
				if self.mimetype_matcher(mimetype):
					yield inpath


def __create_argparser() -> argparse.ArgumentParser:
	result = argparse.ArgumentParser(
		description="Reads in literature chapters stored in EPUB format <http://idpf.org/epub> and writes one text file for each book found.")
	result.add_argument("inpaths", metavar="PATH", nargs='+',
						help="The paths to search for files to read.")
	result.add_argument("-o", "--outdir", metavar="PATH",
						help="The directory to write the extracted book data to.", required=True)
	log_args = result.add_mutually_exclusive_group()
	log_args.add_argument("-i", "--info", help="increase output verbosity to INFO.",
						  action="store_true")
	log_args.add_argument("-d", "--debug", help="increase output verbosity to DEBUG.",
						  action="store_true")
	return result


def __main(args):
	if args.debug:
		logging.basicConfig(level=logging.DEBUG)
	elif args.info:
		logging.basicConfig(level=logging.INFO)

	inpaths = args.inpaths
	print("Will look for data under {}.".format(inpaths), file=sys.stderr)
	file_walker = MimetypeFileWalker(lambda mimetype: mimetype == EPUB_MIMETYPE)
	infiles = tuple(sorted(frozenset(file_walker(inpaths)), key=natural_keys))
	reader = EPUBChapterReader()
	logging.info("Will read %d file(s).", len(infiles))
	outdir = args.outdir
	os.makedirs(outdir, exist_ok=True)
	for infile in infiles:
		book_title, chapters = reader(infile)
		outfile_path = os.path.join(outdir, book_title + ".txt")
		print("Writing book titled \"{}\" to \"{}\".".format(book_title, outfile_path))
		with open(outfile_path, 'w') as outf:
			write_chapters(chapters, outf)
	print("Finished writing {} file(s).".format(len(infiles)))


if __name__ == "__main__":
	__main(__create_argparser().parse_args())
