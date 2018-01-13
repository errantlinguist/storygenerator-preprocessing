import logging
import re
from collections import defaultdict
from typing import IO
from typing import Iterable, Iterator, List, Mapping, Sequence, Tuple

import bs4

from . import Chapter, natural_keys

CHAPTER_DELIM = "=" * 64
WHITESPACE_PATTERN = re.compile("\\s+")

_MAX_NON_NUMERIC_CHAPTER_SEQ_LENGTH = max(len(seq) for seq in Chapter.NON_NUMERIC_CHAPTER_SEQS)


class HTMLChapterReader(object):

	@staticmethod
	def __is_chapter_header(text: str) -> bool:
		lower = text.lower()
		return lower == "chapter"

	@staticmethod
	def __is_non_numeric_chapter_seq(text: str) -> bool:
		if len(text) > _MAX_NON_NUMERIC_CHAPTER_SEQ_LENGTH:
			result = False
		else:
			lowercased_text = text.lower()
			result = lowercased_text in Chapter.NON_NUMERIC_CHAPTER_SEQS
		return result

	@staticmethod
	def __is_toc_header(text: str) -> bool:
		toc_title = "table of contents"
		if len(text) > len(toc_title):
			result = False
		else:
			result = text.lower() == toc_title
		return result

	@staticmethod
	def __merge_file_chapters(file_data: Mapping[str, Sequence[Chapter]]) -> List[Chapter]:
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

	@staticmethod
	def __parse_title(pars: Iterator[bs4.Tag]) -> str:
		# The following paragraph should be the chapter title
		title_par = next(pars)
		result = normalize_spacing(title_par.text)
		if not result and title_par.find("img"):
			# The element processed was actually the header image for the chapter; Try parsing the next paragraph
			title_par = next(pars)
			result = normalize_spacing(title_par.text)

		assert bool(result)
		return result

	@classmethod
	def __parse_pars(cls, pars: bs4.ResultSet) -> Iterator[Chapter]:
		chapters = []
		current_chapter = Chapter()
		pars = iter(pars)
		for par in pars:
			text = par.text.strip()
			if text:
				if cls.__is_chapter_header(text):
					chapters.append(current_chapter)
					# The following paragraph should be the chapter number
					seq_par = next(pars)
					seq = seq_par.text.strip()
					if not seq:
						# Compute the sequence desc from that of the previous chapter
						last_seq = current_chapter.seq
						numeric_last_seq = int(last_seq)
						seq = str(numeric_last_seq + 1)
					# The following paragraph should be the chapter title
					title = cls.__parse_title(pars)
					current_chapter = Chapter(seq, title)
				elif cls.__is_non_numeric_chapter_seq(text):
					chapters.append(current_chapter)
					seq = text.strip().lower()
					# The following paragraph should be the chapter title
					title = cls.__parse_title(pars)
					current_chapter = Chapter(seq, title)
				elif cls.__is_toc_header(text):
					# Do nothing with the table of contents
					# The following paragraph should be related to the TOC, e.g. "Start"; Discard it
					next(pars)
				else:
					# The paragraph is a normal content paragraph; Process it
					normalized_text = normalize_spacing(text)
					if normalized_text:
						current_chapter.pars.append(normalized_text)

		# Add the last chapter
		chapters.append(current_chapter)
		return (chapter for chapter in chapters if chapter)

	@staticmethod
	def __validate_chapter(chapter: Chapter):
		if not chapter.seq:
			raise ValueError("Chapter titled \"{}\" has no seq desc.".format(chapter.title))
		elif not chapter.title:
			raise ValueError("Chapter with seq desc \"{}\" has no title.".format(chapter.seq))
		elif not chapter.pars:
			raise ValueError(
				"Chapter with seq desc \"{}\" and title \"{}\" has no paragraphs.".format(chapter.seq, chapter.title))

	@classmethod
	def __validate_chapters(cls, chapters: Iterable[Chapter]):
		prev_seq_key = (float("-inf"), (float("-inf"),))
		for chapter in chapters:
			seq_key = chapter.seq_sort_key
			if prev_seq_key > seq_key:
				raise ValueError("Chapter is out of order: {}".format(chapter))
			else:
				cls.__validate_chapter(chapter)

			prev_seq_key = seq_key

	def __init__(self):
		pass

	def __call__(self, infile_paths: Iterable[str]) -> Iterator[Tuple[str, List[Chapter]]]:
		book_file_data = defaultdict(dict)
		for infile_path in infile_paths:
			logging.info("Reading \"%s\".", infile_path)
			book_title, chapters = self.__read_file(infile_path)
			book_file_data[book_title][infile_path] = chapters
		logging.info("Read data for %d book(s): %s", len(book_file_data), sorted(book_file_data.keys()))

		for book_title, file_data in book_file_data.items():
			book_chapters = self.__merge_file_chapters(file_data)
			self.__validate_chapters(book_chapters)
			yield book_title, book_chapters

	def __read_file(self, infile_path: str) -> Tuple[str, Tuple[Chapter, ...]]:
		with open(infile_path) as inf:
			soup = bs4.BeautifulSoup(inf, "html.parser")
			book_title = normalize_spacing(soup.head.title.text)
			logging.debug("Parsing data for book titled \"%s\".", book_title)
			# For some reason, chapter titles are occasionally in "blockquote" elements
			pars = soup.find_all(("p", "blockquote"))
			chapters = tuple(self.__parse_pars(pars))
			return book_title, chapters


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


def __create_seq_desc(seq: str) -> str:
	if seq in Chapter.NON_NUMERIC_CHAPTER_SEQS:
		result = seq.upper()
	else:
		result = "CHAPTER " + seq
	return result


def __write_chapter(chapter: Chapter, out: IO[str]):
	seq_desc = __create_seq_desc(chapter.seq)
	chapter_title = seq_desc + ": " + chapter.title
	print(chapter_title, file=out)
	print("\n", file=out)
	for par in chapter.pars:
		print(par, file=out)
