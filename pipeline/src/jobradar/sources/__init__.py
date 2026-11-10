"""Public job sources used by the Day 1 pipeline."""

from jobradar.sources.arbeitnow import ArbeitnowSource
from jobradar.sources.base import JobSource, SourceBatch
from jobradar.sources.remoteok import RemoteOkSource
from jobradar.sources.remotive import RemotiveSource

__all__ = [
    "ArbeitnowSource",
    "JobSource",
    "RemoteOkSource",
    "RemotiveSource",
    "SourceBatch",
    "default_sources",
]


def default_sources() -> list[JobSource]:
    return [RemotiveSource(), RemoteOkSource(), ArbeitnowSource()]
