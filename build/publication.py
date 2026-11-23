"""Recoverable publication of generated site data on the repository volume."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path


NAMES = ("data", "img", "diagnostics")


def _within(root: Path, path: Path) -> Path:
    root, path = root.resolve(), path.resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError(f"Generated path escapes its intended directory: {path}")
    return path


def _remove(root: Path, path: Path):
    target = _within(root, path)
    if target.is_dir():
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()


def _write(path: Path, value):
    pending = path.with_name(path.name + ".next")
    with pending.open("w", encoding="utf-8") as file:
        json.dump(value, file)
        file.flush()
        os.fsync(file.fileno())
    os.replace(pending, path)


def _alive(pid: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
    # os.kill(pid, 0) is not a portable Windows process-presence probe.
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return ctypes.get_last_error() != 87  # ERROR_INVALID_PARAMETER: no such PID
    try:
        code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)):
            return True
        return code.value == 259  # STILL_ACTIVE
    finally:
        kernel.CloseHandle(ctypes.c_void_p(handle))


class BuildLock:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.path = self.workspace / ".hs-map-data.lock"
        self.token = uuid.uuid4().hex

    def __enter__(self):
        state = {"pid": os.getpid(), "token": self.token}
        # A hard link exposes a fully written lock atomically. An incomplete
        # lock is always treated as busy, never deleted as a missing PID.
        candidate = self.workspace / (".hs-map-lock-" + self.token)
        _write(candidate, state)
        try:
            try:
                os.link(candidate, self.path)
            except FileExistsError:
                try:
                    previous = json.loads(self.path.read_text("utf-8"))
                except (OSError, ValueError):
                    raise RuntimeError("Another data build is creating its lock; retry later")
                pid = previous.get("pid")
                if type(pid) is not int or pid <= 0 or _alive(pid):
                    raise RuntimeError("Another site data build is running")
                # Serialize stale-lock recovery so another cleaner cannot
                # remove a fresh owner's lock between read and unlink.
                recovery = self.workspace / ".hs-map-lock-recovery"
                try:
                    descriptor = os.open(recovery, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:
                    raise RuntimeError("Another site data build is recovering its lock")
                try:
                    if json.loads(self.path.read_text("utf-8")) != previous:
                        raise RuntimeError("The data build lock changed; retry later")
                    self.path.unlink()
                    os.link(candidate, self.path)
                finally:
                    os.close(descriptor)
                    recovery.unlink()
        finally:
            candidate.unlink(missing_ok=True)
        return self

    def __exit__(self, *_):
        if self.path.exists():
            current = json.loads(self.path.read_text("utf-8"))
            if current.get("token") == self.token:
                self.path.unlink()


def recover(public: Path):
    workspace = public.absolute().parent.resolve()
    public = _within(workspace, public)
    journal = workspace / ".hs-map-data-update.json"
    if not journal.exists():
        return False
    state = json.loads(journal.read_text("utf-8"))
    if state.get("schema_version") != 1 or not isinstance(state.get("entries"), list):
        raise ValueError("Invalid site data recovery journal")
    backup = _within(workspace, workspace / state["backup"])
    if not backup.name.startswith(".hs-map-backup-"):
        raise ValueError("Invalid site data recovery backup")
    for entry in reversed(state["entries"]):
        if entry.get("name") not in NAMES:
            raise ValueError("Invalid site data recovery target")
        target = _within(public, public / entry["name"])
        old = _within(backup, backup / entry["name"])
        if state.get("phase") != "committed":
            if old.exists():
                _remove(public, target)
                old.rename(target)
            elif not entry["existed"]:
                _remove(public, target)
    if backup.exists():
        _remove(workspace, backup)
    journal.unlink()
    return True


def publish(staging: Path, public: Path, after_install=None):
    workspace = public.absolute().parent.resolve()
    staging, public = staging.resolve(), _within(workspace, public)
    journal = workspace / ".hs-map-data-update.json"
    if journal.exists():
        raise RuntimeError("Recover the previous data publication before installing another")
    for name in NAMES:
        if not _within(staging, staging / name).is_dir():
            raise ValueError(f"Generated folder is missing: {name}")
    public.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=".hs-map-backup-", dir=workspace))
    state = {"schema_version": 1, "phase": "installing", "backup": backup.name,
             "entries": [{"name": name, "existed": (public / name).exists()} for name in NAMES]}
    _write(journal, state)
    try:
        for index, entry in enumerate(state["entries"]):
            name = entry["name"]
            target, source = _within(public, public / name), _within(staging, staging / name)
            if entry["existed"]:
                target.rename(_within(backup, backup / name))
            source.rename(target)
            if after_install:
                after_install(index)
        state["phase"] = "committed"
        _write(journal, state)
    except BaseException:
        recover(public)
        raise
    recover(public)
