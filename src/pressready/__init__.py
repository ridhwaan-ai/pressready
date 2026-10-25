"""PressReady: manuscript in, publish-ready book out."""
__version__ = "0.1.0"


def spine_width_in(pages: int, paper: str = "white") -> float:
    """KDP paperback spine width in inches for a page count and paper type."""
    per_page = {"white": 0.002252, "cream": 0.0025}[paper]
    return round(pages * per_page, 4)
