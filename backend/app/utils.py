def escape_like(text: str) -> str:
    """Make %, _ and \\ match literally inside an ILIKE pattern (use with escape="\\")."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
