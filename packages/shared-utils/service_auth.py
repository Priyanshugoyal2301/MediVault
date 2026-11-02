"""Fail-closed validation for the current private service boundary.

This authenticates a service, not an end user. Owner-scoped repositories must
still authorize every operation. Replace shared keys with workload identities
before expanding the deployment trust boundary.
"""

from secrets import compare_digest


def service_key_is_configured(key: str) -> bool:
    value = key.strip()
    return len(value) >= 32 and "change" not in value.lower()


def service_key_matches(expected: str, supplied: str | None) -> bool:
    return bool(
        service_key_is_configured(expected)
        and supplied
        and compare_digest(expected.strip().encode(), supplied.encode())
    )
