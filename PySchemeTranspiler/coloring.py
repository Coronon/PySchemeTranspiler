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