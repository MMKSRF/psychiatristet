#!/usr/bin/env python3
"""CareBridge Telehealth Server Launcher Alias

Calls runserver.py so both 'python runserver.py' and 'python serverrun.py' work.
"""
from runserver import main

if __name__ == "__main__":
    main()

