from typing import IO, Iterable

from . import Chapter

CHAPTER_DELIM = "=" * 64


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
