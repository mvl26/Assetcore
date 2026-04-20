# Copyright (c) 2026, AssetCore Team
"""Repositories cho User + AC User Profile."""

from .base import BaseRepository


class UserRepo(BaseRepository):
    DOCTYPE = "User"


class UserProfileRepo(BaseRepository):
    DOCTYPE = "AC User Profile"
