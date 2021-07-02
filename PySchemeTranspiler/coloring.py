# PySchemeTranspiler, Transpile simple Python to Scheme(Racket)
# Copyright (C) 2021  Rubin Raithel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Tuple

class Colors:
    RED    = (245, 90,  66)
    ORANGE = (245, 170, 66)
    YELLOW = (245, 252, 71)
    GREEN  = (92,  252, 71)
    BLUE   = (71,  177, 252)
    PURPLE = (189, 71,  252)
    WHITE  = (255, 255, 255)

def colorT(text: str, rgb: Tuple[int, int, int]):
    return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}\033[0m"


def colorB(text: str, rgb: Tuple[int, int, int]):
    return f"\033[48;2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}\033[0m"
