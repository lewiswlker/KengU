#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging utility for RAG Scraper
Adds timestamps to all log messages and saves to file
"""

import os
import threading
from datetime import datetime


class RAGLogger:
    """
    Thread-safe logger with timestamps and file output
    """

    def __init__(self, log_file="rag_scraper.log", verbose=True):
        """
        Initialize logger

        Args:
            log_file: Path to log file
            verbose: Whether to print to console
        """
        self.log_file = log_file
        self.verbose = verbose
        self.lock = threading.Lock()

        # Create or clear log file
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(
                f"=== RAG Scraper Log Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n"
            )

    def log(self, message, force=False, level="INFO"):
        """
        Log a message with timestamp

        Args:
            message: Message to log
            force: Force print even if not verbose
            level: Log level (INFO, WARNING, ERROR, DEBUG)
        """
        if not self.verbose and not force:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        thread_name = threading.current_thread().name

        # Format: [timestamp] [thread] [level] message
        log_line = f"[{timestamp}] [{thread_name}] [{level}] {message}"

        with self.lock:
            # Print to console
            if self.verbose or force:
                print(log_line)

            # Write to file
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_line + "\n")
            except Exception as e:
                print(
                    f"[{timestamp}] [Logger] [ERROR] Failed to write to log file: {e}"
                )

    def info(self, message, force=False):
        """Log info message"""
        self.log(message, force=force, level="INFO")

    def warning(self, message):
        """Log warning message"""
        self.log(message, force=True, level="WARNING")

    def error(self, message):
        """Log error message"""
        self.log(message, force=True, level="ERROR")

    def debug(self, message):
        """Log debug message"""
        self.log(message, force=False, level="DEBUG")


# Global logger instance
_global_logger = None
_logger_lock = threading.Lock()


def get_logger(log_file="rag_scraper.log", verbose=True):
    """
    Get or create global logger instance

    Args:
        log_file: Path to log file
        verbose: Whether to print to console

    Returns:
        RAGLogger instance
    """
    global _global_logger

    with _logger_lock:
        if _global_logger is None:
            _global_logger = RAGLogger(log_file=log_file, verbose=verbose)
        return _global_logger


def reset_logger():
    """Reset global logger (useful for testing)"""
    global _global_logger
    with _logger_lock:
        _global_logger = None
