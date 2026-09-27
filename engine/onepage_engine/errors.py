"""The errors of the engine, all of them EngineError."""


class EngineError(Exception):
    """A page that the engine cannot render faithfully."""


class FontLoadError(EngineError):
    """A font of the page failed to load, or a required family is missing: missing names them,
    separated by commas, as the page names them."""

    def __init__(self, missing: str):
        super().__init__(f"fonts did not load ({missing})")
        self.missing = missing


class SystemFontError(EngineError):
    """Some text of the PDF was drawn with a font that is not one of the bundled fonts, so the PDF
    depends on the fonts installed on the machine: fonts maps each such font (its PostScript name)
    to the characters it draws."""

    def __init__(self, fonts: dict[str, set[str]]):
        drawn = "; ".join(f"{''.join(sorted(chars))} with {name}" for name, chars in sorted(fonts.items()))
        super().__init__(f"text drawn with system fonts: {drawn}")
        self.fonts = fonts
