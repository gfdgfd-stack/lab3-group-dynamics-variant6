"""Hypothesis profiles configuration (Task 1.2).

Профиль ``default`` — для локальной разработки.
Профиль ``ci`` — для CI-пайплайна с бОльшим количеством примеров.
"""

from hypothesis import HealthCheck, settings

settings.register_profile(
    "default",
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.register_profile(
    "ci",
    max_examples=500,
    deadline=None,
)

settings.load_profile("default")
