# SPDX-License-Identifier: Apache-2.0
"""Create or check a private folder for lab state (fake data, evidence, alerts)."""
import os
import stat
import sys
from pathlib import Path


def private_dir(path: str | Path) -> Path:
    """Return `path` as a folder that is yours and not writable by others.

    A new folder is made with mode 700. An existing one is refused if it is a
    symlink, not owned by the current user, or group or other writable.
    """
    p = Path(path)
    if p.is_symlink():
        sys.exit(f"refusing: {p} is a symlink")
    if p.exists():
        st = p.stat()
        if not p.is_dir():
            sys.exit(f"refusing: {p} is not a directory")
        if hasattr(os, "getuid") and st.st_uid != os.getuid():
            sys.exit(f"refusing: {p} is not owned by you")
        if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            sys.exit(f"refusing: {p} is group or other writable")
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.mkdir(mode=0o700)
    return p
