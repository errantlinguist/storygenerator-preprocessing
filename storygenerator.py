#!/usr/bin/env python3

"""
Reads in literature stored in PDF format and uses it to generate new data using a neural network.
"""

__author__ = "Todd Shore <errantlinguist+github@gmail.com>"
__copyright__ = "Copyright (C) 2018 Todd Shore"
__license__ = "Apache License, Version 2.0"

import argparse
import logging
import os
import random
import re
import sys
from collections import defaultdict, namedtuple
from typing import Iterable, List, Tuple, Mapping

import bs4
import ebooklib
import ebooklib.epub
import magic
import nltk
import numpy as np

DOC_MIMETYPE = "application/epub+zip"
# DOC_MIMETYPE = "application/pdf"
NAV_POINT_TITLE_BLACKLIST = frozenset(("cover", "cover page", "title", "title page", "copyright", "copyright page",
									   "dedication", "contents", "table of contents", "maps", "glossary",
									   "about the author", "start"))
WHITESPACE_PATTERN = re.compile("\\s+")

ChapterDescription = namedtuple("ChapterDescription", "seq name src")


class CorpusReader(object):
	def __init__(self):
		self.book_titles = []
		self.chapter_seq_names = defaultdict(list)
		self.paragraphs = []

	def __parse_doc(self, doc: ebooklib.epub.EpubHtml):
		soup = bs4.BeautifulSoup(doc.get_content(), "html5lib")
		pars = soup.find_all("p")
		content_texts = trim_content_beginning(pars)
		self.paragraphs.extend(content_texts)

	def __parse_navigation(self, elem: ebooklib.epub.EpubNcx) -> List[ChapterDescription]:
		soup = bs4.BeautifulSoup(elem.get_content(), "xml")
		nav_points = soup.find_all("navPoint")
		# There are occasionally duplicate navigation points used as "subtitles"
		nav_points_by_src = defaultdict(list)
		for nav in nav_points:
			# print(nav)
			normalized_label = normalize_spacing(nav.navLabel.text).lower()
			if not normalized_label in NAV_POINT_TITLE_BLACKLIST:
				# id = nav.attrs["id"]
				src = nav.content.attrs["src"]
				nav_points_by_src[src].append(nav)

		result = []
		for src, nav_points in nav_points_by_src.items():
			joined_label_text = normalize_spacing(" ".join(nav.navLabel.text for nav in nav_points))
			if not joined_label_text.lower() in NAV_POINT_TITLE_BLACKLIST:
				chapter_seq, chapter_name = parse_chapter_title(joined_label_text)
				self.chapter_seq_names[chapter_seq] = chapter_name
				result.append(ChapterDescription(chapter_seq, chapter_name, src))

		return result

	def read_file(self, filepath: str):
		# with open(filepath, "rb") as inf:
		#	reader = PyPDF2.PdfFileReader(inf)
		#	for page in reader.pages:
		#		print(page)

		book = ebooklib.epub.read_epub(filepath)
		book_title = normalize_spacing(book.title)
		logging.info("Reading book \"%s\".", book_title)
		self.book_titles.append(book_title)
		chapter_descs = tuple(
			desc for elem in book.get_items_of_type(ebooklib.ITEM_NAVIGATION) for desc in self.__parse_navigation(elem))
		# print(chapter_descs)

		for desc in chapter_descs:
			doc = book.get_item_with_href(desc.src)
			logging.debug("Reading document with HREF \"%s\".", desc.src)
			self.__parse_doc(doc)


def is_chapter_header(text: str) -> bool:
	lower = text.lower()
	if lower.startswith("chapter"):
		result = True
	else:
		try:
			int(lower)
			result = True
		except ValueError:
			# The next element is not a chapter number; It must be a proper content element
			result = False

	return result


def normalize_chapter_seq(seq: str) -> str:
	result = seq.lower()

	if result.endswith(":"):
		result = seq[:len(seq) - 1]
	else:
		result = seq

	if result.startswith("prologue"):
		result = "PROLOGUE"
	elif result.startswith("epilogue"):
		result = "EPILOGUE"

	return result


def normalize_spacing(label: str) -> str:
	tokens = WHITESPACE_PATTERN.split(label.strip())
	return " ".join(tokens)


def parse_chapter_title(title: str) -> Tuple[str, str]:
	tokens = WHITESPACE_PATTERN.split(title.strip())
	if tokens[0].lower() == "chapter":
		tokens = tokens[1:]
	chapter_seq = normalize_chapter_seq(tokens[0])
	chapter_name = " ".join(tokens[1:])
	return chapter_seq, chapter_name


def read_epub_files(inpaths: Iterable[str]):
	mime = magic.Magic(mime=True)
	reader = CorpusReader()

	for inpath in inpaths:
		for root, dirs, files in os.walk(inpath, followlinks=True):
			for file in files:
				filepath = os.path.join(root, file)
				mimetype = mime.from_file(filepath)
				if DOC_MIMETYPE == mimetype:
					print("Reading \"{}\".".format(filepath), file=sys.stderr)
					reader.read_file(filepath)


def trim_content_beginning(pars: Iterable[bs4.Tag]) -> List[str]:
	par_texts = []
	for par in pars:
		text = par.text.strip()
		if text:
			par_texts.append(text)

	if par_texts:
		start_idx = 0
		for text in par_texts:
			# print(start_idx)
			if not is_chapter_header(text):
				break
		result = par_texts[start_idx:]
	else:
		result = par_texts

	return result


def __create_argparser() -> argparse.ArgumentParser:
	result = argparse.ArgumentParser(
		description="Reads in literature stored in EPUB format <http://idpf.org/epub> and uses it to generate new data using a neural network.")
	result.add_argument("inpaths", metavar="PATH", nargs='+',
						help="The paths to search for EPUB files to read.")
	result.add_argument("-s", "--random-seed", dest="random_seed", metavar="SEED", type=int, default=7,
						help="The random seed to use.")
	result.add_argument("-d", "--debug", help="increase output verbosity",
						action="store_true")
	return result


def __parse_body(content: ebooklib.epub.EpubHtml):
	# print(body)
	soup = bs4.BeautifulSoup(content, 'html.parser')
	body = soup.body
	p = body.find_all('p')


def __main(args):
	if args.debug:
		logging.basicConfig(level=logging.DEBUG)

	random_seed = args.random_seed
	print("Setting random seed to {}.".format(random_seed), file=sys.stderr)
	# https://machinelearningmastery.com/time-series-prediction-lstm-recurrent-neural-networks-python-keras/
	# fix random seed for reproducibility
	random.seed(random_seed)
	np.random.seed(random_seed)

	inpaths = args.inpaths
	print("Will look for data under {}".format(inpaths), file=sys.stderr)
	read_epub_files(inpaths)


if __name__ == "__main__":
	__main(__create_argparser().parse_args())
