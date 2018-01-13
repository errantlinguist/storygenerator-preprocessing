import logging
import re
from collections import defaultdict, namedtuple
from typing import DefaultDict, Dict, Iterable, Iterator, List, Mapping, Sequence, Tuple
from typing import IO

import bs4
import ebooklib
from ebooklib import epub

from . import Chapter, chapter_seq_sort_key, natural_keys

BOOK_END_PATTERN = re.compile("The\\s+End\\s+of\\s+the\\s+(?:\\w+)\\s+Book\\s+of", re.IGNORECASE)
CHAPTER_DELIM = "=" * 64
CHAPTER_HEADER_PATTERN = re.compile("CHAPTER(?:\\s+(\\d+))?:?", re.IGNORECASE)
TITLE_BLACKLIST = frozenset(("cover", "cover page", "title", "title page", "copyright", "copyright page",
							 "dedication", "contents", "table of contents", "maps", "glossary",
							 "about the author", "start"))
WHITESPACE_PATTERN = re.compile("\\s+")

_MAX_NON_NUMERIC_CHAPTER_SEQ_LENGTH = max(len(seq) for seq in Chapter.NON_NUMERIC_CHAPTER_SEQS)

_ChapterDescription = namedtuple("_ChapterDescription", "seq name src")


class EPUBChapterReader(object):

	@staticmethod
	def __is_chapter_header(text: str) -> bool:
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

	@staticmethod
	def __normalize_chapter_seq(seq: str) -> str:
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

	@classmethod
	def __parse_chapter_title(cls, title: str) -> Tuple[str, str]:
		tokens = WHITESPACE_PATTERN.split(title.strip())
		if tokens[0].lower() == "chapter":
			tokens = tokens[1:]
		chapter_seq = cls.__normalize_chapter_seq(tokens[0])
		chapter_name = " ".join(tokens[1:])
		return chapter_seq, chapter_name

	@classmethod
	def __parse_doc(cls, doc: epub.EpubHtml) -> Iterator[Chapter]:
		soup = bs4.BeautifulSoup(doc.get_content(), "html.parser")
		return _parse_chapters(soup)

	@classmethod
	def __parse_navigation(cls, elem: ebooklib.epub.EpubNcx) -> List[_ChapterDescription]:
		soup = bs4.BeautifulSoup(elem.get_content(), "xml")
		nav_points = soup.find_all("navPoint")
		# There are occasionally duplicate navigation points used as "subtitles"
		nav_points_by_src = defaultdict(list)
		for nav in nav_points:
			# print(nav)
			normalized_label = normalize_spacing(nav.navLabel.text).lower()
			if not normalized_label in TITLE_BLACKLIST:
				# id = nav.attrs["id"]
				src = nav.content.attrs["src"]
				nav_points_by_src[src].append(nav)

		result = []
		for src, nav_points in nav_points_by_src.items():
			joined_label_text = normalize_spacing(" ".join(nav.navLabel.text for nav in nav_points))
			if not joined_label_text.lower() in TITLE_BLACKLIST:
				chapter_seq, chapter_name = cls.__parse_chapter_title(joined_label_text)
				result.append(_ChapterDescription(chapter_seq, chapter_name, src))

		return result

	@classmethod
	def __read_book_files(cls, infile_paths: Iterable[str]) -> DefaultDict[str, Dict[str, Tuple[Chapter, ...]]]:
		result = defaultdict(dict)
		for infile_path in infile_paths:
			logging.info("Reading \"%s\".", infile_path)
			book_title, chapters = cls.__read_file(infile_path)
			if chapters:
				result[book_title][infile_path] = chapters

		return result

	@classmethod
	def __read_file(cls, infile_path: str) -> Tuple[str, Tuple[Chapter, ...]]:
		book = ebooklib.epub.read_epub(infile_path)
		book_title = normalize_spacing(book.title)
		logging.debug("Parsing data for book titled \"%s\".", book_title)
		ordered_chapter_descs = sorted((
			desc for elem in book.get_items_of_type(ebooklib.ITEM_NAVIGATION) for desc in cls.__parse_navigation(elem)),
			key=lambda desc: chapter_seq_sort_key(desc.seq))
		chapters = []
		for desc in ordered_chapter_descs:
			doc = book.get_item_with_href(desc.src)
			logging.debug("Parsing document with HREF \"%s\".", desc.src)
			chapters.extend(cls.__parse_doc(doc))
		logging.debug("Parsed %d chapter(s) for book titled \"%s\".", len(chapters), book_title)
		return book_title, chapters

	@classmethod
	def __trim_content_beginning(cls, pars: Iterable[bs4.Tag]) -> List[str]:
		par_texts = []
		for par in pars:
			text = par.text.strip()
			if text:
				par_texts.append(text)

		if par_texts:
			start_idx = 0
			for text in par_texts:
				# print(start_idx)
				if not cls.__is_chapter_header(text):
					break
			result = par_texts[start_idx:]
		else:
			result = par_texts

		return result

	# -> DefaultDict[str, Dict[str, Tuple[Chapter, ...]]]:
	def __call__(self, infile_path) -> Tuple[str, Tuple[Chapter, ...]]:
		logging.info("Reading \"%s\".", infile_path)
		book_title, chapters = self.__read_file(infile_path)
		return book_title, chapters


# def __call__(self, infile_paths: Iterable[str]) -> Iterator[Tuple[str, List[Chapter]]]:
# 	book_file_data = self.__read_book_files(infile_paths)
#
# 	logging.info("Read data for %d book(s): %s", len(book_file_data), sorted(book_file_data.keys()))
#
# 	for book_title, file_data in book_file_data.items():
# 		book_chapters = _merge_file_chapters(file_data)
# 		_validate_chapters(book_chapters)
# 		print("yield!!!")
# 		yield book_title, book_chapters


class HTMLChapterReader(object):

	@classmethod
	def __read_file(cls, infile_path: str) -> Tuple[str, Tuple[Chapter, ...]]:
		with open(infile_path) as inf:
			soup = bs4.BeautifulSoup(inf, "html.parser")
			book_title = normalize_spacing(soup.head.title.text)
			logging.debug("Parsing data for book titled \"%s\".", book_title)
			chapters = tuple(_parse_chapters(soup))
			return book_title, chapters

	def __call__(self, infile_paths: Iterable[str]) -> Iterator[Tuple[str, List[Chapter]]]:
		book_file_data = defaultdict(dict)
		for infile_path in infile_paths:
			logging.info("Reading \"%s\".", infile_path)
			book_title, chapters = self.__read_file(infile_path)
			book_file_data[book_title][infile_path] = chapters
		logging.info("Read data for %d book(s): %s", len(book_file_data), sorted(book_file_data.keys()))

		for book_title, file_data in book_file_data.items():
			book_chapters = _merge_file_chapters(file_data)
			_validate_chapters(book_chapters)
			yield book_title, book_chapters


def normalize_spacing(text: str) -> str:
	tokens = WHITESPACE_PATTERN.split(text.strip())
	return " ".join(tokens)


def write_chapters(chapters: Iterable[Chapter], out: IO[str]):
	chapters = iter(chapters)
	__write_chapter(next(chapters), out)
	for chapter in chapters:
		print("\n", file=out)
		print(CHAPTER_DELIM, file=out)
		__write_chapter(chapter, out)


def _merge_file_chapters(file_data: Mapping[str, Sequence[Chapter]]) -> List[Chapter]:
	result = []
	sorted_file_data = tuple(sorted(file_data.items(), key=lambda item: natural_keys(item[0])))

	for _, chapters in sorted_file_data:
		for chapter in chapters:
			if not chapter.seq:
				assert not chapter.title
				# Add the pars from this chapter to the last chapter
				last_chapter = result[len(result) - 1]
				last_chapter.pars.extend(chapter.pars)
			else:
				result.append(chapter)

	return result


def _parse_chapters(soup: bs4.BeautifulSoup) -> Iterator[Chapter]:
	chapters = []
	# For some reason, chapter titles are occasionally in "blockquote" elements
	pars = iter(soup.find_all(("p", "blockquote")))
	current_chapter = Chapter()
	for par in pars:
		text = par.text.strip()
		if text:
			chapter_header_match = CHAPTER_HEADER_PATTERN.match(text)
			if chapter_header_match:
				chapters.append(current_chapter)

				seq = chapter_header_match.group(1)
				if not seq:
					# The following paragraph should be the chapter number
					seq_par = next(pars)
					seq = seq_par.text.strip()
					if not seq:
						# Compute the sequence desc from that of the previous chapter
						last_seq = current_chapter.seq
						numeric_last_seq = int(last_seq)
						seq = str(numeric_last_seq + 1)
				# The following paragraph should be the chapter title
				title = __parse_title(pars)
				current_chapter = Chapter(seq, title)
			elif __is_non_numeric_chapter_seq(text):
				chapters.append(current_chapter)
				seq = text.strip().lower()
				# The following paragraph should be the chapter title
				title = __parse_title(pars)
				current_chapter = Chapter(seq, title)
			elif __is_toc_header(text):
				# Do nothing with the table of contents
				# The following paragraph should be related to the TOC, e.g. "Start"; Discard it
				next(pars)
			else:
				end_match = BOOK_END_PATTERN.match(text)
				if end_match:
					break
				else:
					# The paragraph is a normal content paragraph; Process it
					normalized_text = normalize_spacing(text)
					if normalized_text:
						current_chapter.pars.append(normalized_text)

	# Add the last chapter
	chapters.append(current_chapter)
	return (chapter for chapter in chapters if chapter)


def _validate_chapters(chapters: Iterable[Chapter]):
	prev_seq_key = (float("-inf"), (float("-inf"),))
	for chapter in chapters:
		seq_key = chapter.seq_sort_key
		if prev_seq_key > seq_key:
			raise ValueError("Chapter is out of order: {}".format(chapter))
		else:
			__validate_chapter(chapter)

		prev_seq_key = seq_key


def __create_seq_desc(seq: str) -> str:
	if seq in Chapter.NON_NUMERIC_CHAPTER_SEQS:
		result = seq.upper()
	else:
		result = "CHAPTER " + seq
	return result


def __is_non_numeric_chapter_seq(text: str) -> bool:
	if len(text) > _MAX_NON_NUMERIC_CHAPTER_SEQ_LENGTH:
		result = False
	else:
		lowercased_text = text.lower()
		result = lowercased_text in Chapter.NON_NUMERIC_CHAPTER_SEQS
	return result


def __is_toc_header(text: str) -> bool:
	toc_title = "table of contents"
	if len(text) > len(toc_title):
		result = False
	else:
		result = text.lower() == toc_title
	return result


def __parse_title(pars: Iterator[bs4.Tag]) -> str:
	# The following paragraph should be the chapter title
	title_par = next(pars)
	result = normalize_spacing(title_par.text)
	while not result and title_par.find("img"):
		# The element processed was actually the header image for the chapter; Try parsing the next paragraph
		title_par = next(pars)
		result = normalize_spacing(title_par.text)

	assert bool(result)
	return result


def __write_chapter(chapter: Chapter, out: IO[str]):
	seq_desc = __create_seq_desc(chapter.seq)
	chapter_title = seq_desc + ": " + chapter.title
	print(chapter_title, file=out)
	print("\n", file=out)
	for par in chapter.pars:
		print(par, file=out)


def __validate_chapter(chapter: Chapter):
	if not chapter.seq:
		raise ValueError("Chapter titled \"{}\" has no seq desc.".format(chapter.title))
	elif not chapter.title:
		raise ValueError("Chapter with seq desc \"{}\" has no title.".format(chapter.seq))
	elif not chapter.pars:
		raise ValueError(
			"Chapter with seq desc \"{}\" and title \"{}\" has no paragraphs.".format(chapter.seq, chapter.title))
