#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG scraper - HKU Course Materials Downloader

Downloads course materials from HKU Moodle and Exambase
"""

from .scraper import RAGScraper, scrape
from .moodle import HKUMoodleScraper
from .exambase import ExambaseScraper
from .logger import RAGLogger

__version__ = "1.0.0"
__all__ = ["RAGScraper", "scrape", "HKUMoodleScraper", "ExambaseScraper", "RAGLogger"]