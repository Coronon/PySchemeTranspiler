from typing import TextIO, List

from ast import parse, Module

class Parser():
    @staticmethod
    def parseFile(file: TextIO) -> Module:
        contents: str = file.read()
        return parse(contents)
        