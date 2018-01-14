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
from typing import Iterable, Iterator

import magic

from storygenerator import natural_keys
from storygenerator.io import EPUBChapterReader, write_chapters

EPUB_MIMETYPE = "application/epub+zip"


def walk_epub_files(inpaths: Iterable[str]) -> Iterator[str]:
	mime = magic.Magic(mime=True)

	for inpath in inpaths:
		if os.path.isdir(inpath):
			for root, dirs, files in os.walk(inpath, followlinks=True):
				for file in files:
					filepath = os.path.join(root, file)
					mimetype = mime.from_file(filepath)
					if EPUB_MIMETYPE == mimetype:
						yield filepath
		else:
			mimetype = mime.from_file(filepath)
			if EPUB_MIMETYPE == mimetype:
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
	reader = EPUBChapterReader()
	infiles = tuple(sorted(frozenset(walk_epub_files(inpaths)), key=natural_keys))
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
