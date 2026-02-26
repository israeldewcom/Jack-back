#!/usr/bin/env python3
"""
Run Alembic database migrations.
"""
import subprocess
import sys

def main():
    # Assumes alembic.ini is in the root
    result = subprocess.run(["alembic", "upgrade", "head"])
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
