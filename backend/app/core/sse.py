import json
from typing import Iterable


def format_sse(data: dict, event: str | None = None) -> str:
    lines = []
    if event:
        lines.append(f'event: {event}')
    lines.append(f'data: {json.dumps(data, ensure_ascii=False)}')
    lines.append('')
    return '\n'.join(lines)


def iter_sse(messages: Iterable[dict]):
    for message in messages:
        yield format_sse(message)
