from typing import TextIO

from .parser import Parser

class Converter():
    def __init__(self, file: TextIO) -> None:
        self.toks = Parser.parseFile(file).body
        