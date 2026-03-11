from __future__ import annotations

from collections import Counter, defaultdict
from threading import Lock


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._http_requests: Counter[tuple[str, str, str]] = Counter()
        self._http_durations: defaultdict[tuple[str, str], list[float]] = defaultdict(list)
        self._auth_attempts: Counter[tuple[str, str]] = Counter()

    def record_request(self, method: str, endpoint: str, status_code: int, duration_seconds: float) -> None:
        with self._lock:
            self._http_requests[(method, endpoint, str(status_code))] += 1
            self._http_durations[(method, endpoint)].append(duration_seconds)

    def record_auth_attempt(self, method: str, outcome: str) -> None:
        with self._lock:
            self._auth_attempts[(method, outcome)] += 1

    def render_prometheus(self) -> str:
        lines = [
            '# HELP cap_http_requests_total Total HTTP requests handled by the API.',
            '# TYPE cap_http_requests_total counter',
        ]
        with self._lock:
            for (method, endpoint, status_code), value in sorted(self._http_requests.items()):
                lines.append(
                    f'cap_http_requests_total{{method="{method}",endpoint="{endpoint}",status_code="{status_code}"}} {value}'
                )
            lines.extend(
                [
                    '# HELP cap_http_request_duration_seconds Request duration summary.',
                    '# TYPE cap_http_request_duration_seconds summary',
                ]
            )
            for (method, endpoint), durations in sorted(self._http_durations.items()):
                count = len(durations)
                total = sum(durations)
                avg = total / count if count else 0.0
                lines.append(
                    f'cap_http_request_duration_seconds_count{{method="{method}",endpoint="{endpoint}"}} {count}'
                )
                lines.append(
                    f'cap_http_request_duration_seconds_sum{{method="{method}",endpoint="{endpoint}"}} {total:.6f}'
                )
                lines.append(
                    f'cap_http_request_duration_seconds_avg{{method="{method}",endpoint="{endpoint}"}} {avg:.6f}'
                )
            lines.extend(
                [
                    '# HELP cap_auth_attempts_total Authentication attempts.',
                    '# TYPE cap_auth_attempts_total counter',
                ]
            )
            for (method, outcome), value in sorted(self._auth_attempts.items()):
                lines.append(f'cap_auth_attempts_total{{method="{method}",outcome="{outcome}"}} {value}')
        lines.append('')
        return '\n'.join(lines)


metrics_registry = MetricsRegistry()
