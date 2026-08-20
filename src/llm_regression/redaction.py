import re


def redact(value: str, patterns: str) -> str:
    for pattern in patterns.split("||"):
        try:
            value = re.sub(pattern, "[REDACTED]", value)
        except re.error:
            continue
    return value
