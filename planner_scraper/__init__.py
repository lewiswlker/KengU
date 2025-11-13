#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG scraper - HKU Course Materials Downloader

Downloads course materials from HKU Moodle and Exambase
"""

from .calendar import MoodleCalendarCrawler

__version__ = "1.0.0"
__all__ = [
    "MoodleCalendarCrawler"
]
