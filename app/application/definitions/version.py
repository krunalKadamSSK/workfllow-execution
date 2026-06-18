def parse_version(value: str | int) -> int:
    """Normalize frontend version strings (e.g. '1.0.0' or '1') to an integer."""
    if isinstance(value, int):
        return value

    normalized = str(value).strip()
    if not normalized:
        raise ValueError("Version cannot be empty")

    if "." in normalized:
        return int(normalized.split(".", maxsplit=1)[0])

    return int(normalized)
