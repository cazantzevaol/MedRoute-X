"""Compatibility entry point: always rebuild the CURRENT submission report.

Historical v0.4 generator was retired in sprint 6 to prevent stale reports.
"""
from build_submission_report import build

if __name__ == '__main__':
    build()
