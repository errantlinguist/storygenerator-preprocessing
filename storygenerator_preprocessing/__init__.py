"""
Functionalities for reading in literature and using it to generate new data using a neural network.
"""

__author__ = "Todd Shore <errantlinguist+github@gmail.com>"
__copyright__ = "Copyright (C) 2018 Todd Shore"
__license__ = "Apache License, Version 2.0"

import re
from typing import Optional, Sequence, Tuple, Union

__DIGITS_PATTERN = re.compile('(\d+)')


class Chapter(object):

	def __init__(self, seq: Optional[str] = None, title: Optional[str] = None,
				 pars: Optional[Sequence[str]] = None):
		"""
		:param seq: The chapter sequence description, e.g. "CHAPTER 1", "PROLOGUE" or "EPILOGUE".
		:param title: The chapter title.
		:param pars A sequence of strings, each representing a single paragraph.
		"""
		self.seq = seq
		self.title = title
		self.pars = [] if pars is None else pars

	@property
	def __key(self):
		return self.seq, self.title, self.pars

	def __bool__(self):
		return bool(self.seq) or bool(self.title) or bool(self.pars)

	def __eq__(self, other):
		return self is other or (isinstance(other, type(self)) and self.__key == other.__key)

	def __hash__(self):
		return hash(self.__key)

	def __ne__(self, other):
		return not (self == other)

	def __repr__(self):
		fields = ("{seq=", str(self.seq), ", title=", str(self.title), ", pars=", str(self.pars), "}")
		field_repr = "".join(fields)
		return self.__class__.__name__ + field_repr


def natural_keys(text: str) -> Tuple[Union[int, str], ...]:
	"""
	alist.sort(key=natural_keys) sorts in human order

	:see: http://nedbatchelder.com/blog/200712/human_sorting.html
	:see: http://stackoverflow.com/a/5967539/1391325
	"""
	return tuple(__atoi(c) for c in __DIGITS_PATTERN.split(text))


def __atoi(text: str) -> Union[int, str]:
	"""
	:see: http://stackoverflow.com/a/5967539/1391325
	"""
	return int(text) if text.isdigit() else text
