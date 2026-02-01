"""Automated code quality checks for MCP tool files.

Detects patterns known to cause bugs:
- Using t.get("type") instead of t.get("audio") for track type detection
- Calling known-buggy D-Bus methods (scriptImportMedia, scriptGetClipProperties, etc.)
- Using GetItemListInTrack with track_idx instead of track_id
- Treating get_clips_on_track() results as list[int] instead of list[dict]
- Using high-level wrapper methods that silently fail
"""

import ast
import os
import re
import sys
import unittest

# All MCP tool files + composite + helpers
MCP_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "..", "mcp_kdenlive", "tools")
MCP_HELPERS = os.path.join(os.path.dirname(__file__), "..", "mcp_kdenlive", "helpers.py")
DBUS_CLIENT = os.path.join(os.path.dirname(__file__), "..", "..", "kdenlive-api", "kdenlive_api", "dbus_client.py")


def _collect_py_files(*dirs_and_files):
    """Collect all .py files from dirs and individual file paths."""
    result = []
    for path in dirs_and_files:
        if os.path.isdir(path):
            for fname in os.listdir(path):
                if fname.endswith(".py") and fname != "__init__.py":
                    result.append(os.path.join(path, fname))
        elif os.path.isfile(path):
            result.append(path)
    return result


class TestNoBuggyDBusCalls(unittest.TestCase):
    """Ensure no tool code calls known-buggy D-Bus scripting methods."""

    BUGGY_METHODS = {
        "scriptImportMedia": "Use addProjectClip per file instead (scriptImportMedia returns folder/sequence IDs)",
        "scriptGetClipProperties": "Causes permanent deadlock in Kdenlive",
        "scriptInsertClipsSequentially": "Returns -1 for all clips; use scriptInsertClip in a loop",
    }

    def test_no_buggy_dbus_calls_in_tools(self):
        files = _collect_py_files(MCP_TOOLS_DIR, MCP_HELPERS)
        errors = []
        for fpath in files:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            for method, reason in self.BUGGY_METHODS.items():
                # Match _call("methodName" or direct .methodName( patterns
                if re.search(rf'["\']({method})["\']', content):
                    errors.append(f"{os.path.basename(fpath)}: calls '{method}' — {reason}")
        self.assertEqual(errors, [], "Buggy D-Bus methods found:\n" + "\n".join(errors))

    @unittest.skipUnless(os.path.isfile(DBUS_CLIENT), "requires kdenlive-api sibling repo")
    def test_no_buggy_dbus_calls_in_dbus_client(self):
        """dbus_client.py may reference buggy methods in disabled/stub code.
        Ensure they are not actually called (only present in comments or stubs)."""
        with open(DBUS_CLIENT, encoding="utf-8") as f:
            content = f.read()
        # scriptGetClipProperties should only appear in the stub that returns {"id": bin_id}
        matches = list(re.finditer(r'self\._call\(["\']scriptGetClipProperties["\']', content))
        self.assertEqual(
            len(matches), 0,
            "dbus_client.py still actively calls scriptGetClipProperties (deadlock risk)"
        )


class TestTrackTypeDetection(unittest.TestCase):
    """Track type must be detected via t.get("audio"), not t.get("type").

    The D-Bus parser returns dicts with 'audio' key ('true'/'false'),
    not a 'type' key. Using t.get("type") silently defaults to "video"
    for ALL tracks, including audio tracks.
    """

    def test_no_type_key_for_track_detection(self):
        files = _collect_py_files(MCP_TOOLS_DIR, MCP_HELPERS)
        errors = []
        for fpath in files:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            # Skip media_table() in helpers — it formats media pool items
            # where "type" is a valid clip property, not a track property.
            in_media_table = False

            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if "def media_table" in stripped:
                    in_media_table = True
                elif in_media_table and stripped.startswith("def "):
                    in_media_table = False
                if in_media_table:
                    continue

                # Detect t.get("type") or .get("type", "video") patterns
                if re.search(r'\.get\(\s*["\']type["\']\s*,\s*["\'](?:video|audio)["\']', line):
                    errors.append(f"{os.path.basename(fpath)}:{i}: {line.strip()}")
                if re.search(r'\.get\(\s*["\']type["\']\s*\)\s*==\s*["\'](?:video|audio)["\']', line):
                    errors.append(f"{os.path.basename(fpath)}:{i}: {line.strip()}")
        self.assertEqual(
            errors, [],
            "Track type detected via .get('type') instead of .get('audio'):\n" + "\n".join(errors)
        )


class TestClipsOnTrackReturnType(unittest.TestCase):
    """get_clips_on_track() returns list[dict], not list[int].

    Any code that indexes into the result and treats it as an int
    (e.g., clip_ids[i] used as clip_id directly) is a bug.
    """

    def test_no_direct_indexing_as_int(self):
        files = _collect_py_files(MCP_TOOLS_DIR)
        errors = []
        for fpath in files:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            # Pattern: get_clips_on_track(...) assigned to var, then var[i] used
            # without .get("id") — heuristic check
            if "get_clips_on_track" in content:
                # After assignment, check if result is indexed and used directly
                # as an int (no .get() call on the indexed result)
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    # Look for patterns like: old_clip_id = clip_ids[idx]
                    # where clip_ids came from get_clips_on_track
                    if re.search(r'=\s*\w+\[\w+\]\s*$', stripped):
                        # Check if the variable is from get_clips_on_track
                        context = "\n".join(lines[max(0, i-10):i+1])
                        if "get_clips_on_track" in context and ".get(" not in stripped:
                            # Check if next line(s) use .get() on the result
                            # (meaning it's correctly treated as dict)
                            next_lines = "\n".join(lines[i+1:i+4]) if i+1 < len(lines) else ""
                            var_name = stripped.split("=")[0].strip()
                            if f"{var_name}.get(" in next_lines:
                                continue  # correctly treated as dict
                            errors.append(
                                f"{os.path.basename(fpath)}:{i+1}: "
                                f"Possible direct indexing of get_clips_on_track result as int: "
                                f"{stripped}"
                            )
        self.assertEqual(
            errors, [],
            "get_clips_on_track() result indexed as int (should use .get('id')):\n"
            + "\n".join(errors)
        )


class TestNoTrackIdxVsTrackId(unittest.TestCase):
    """Ensure tools pass track_id (unique int), not track_idx (positional index).

    GetItemListInTrack has ambiguous index handling. Tools should use
    the track's 'id' field, not 'index' or 'position'.
    """

    def test_no_track_idx_usage(self):
        files = _collect_py_files(MCP_TOOLS_DIR)
        errors = []
        for fpath in files:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            # Detect track_idx or track.*index patterns that indicate
            # using positional index instead of track id.
            # Exclude .get('index') used for undo stack position (checkpoints.py).
            if re.search(r'track_idx|track.*\.get\(\s*["\']index["\']', content):
                errors.append(
                    f"{os.path.basename(fpath)}: uses track index — "
                    f"should use .get('id') for track identification"
                )
        self.assertEqual(
            errors, [],
            "Track 'index' used instead of 'id':\n" + "\n".join(errors)
        )


class TestWrapperConsistency(unittest.TestCase):
    """Check that tools don't mix wrapper and direct D-Bus for the same operation."""

    def test_no_raw_call_for_import(self):
        """Import should use dbus.import_media() or the addProjectClip
        pattern with ID diffing, but not bare _call without diffing."""
        files = _collect_py_files(MCP_TOOLS_DIR)
        errors = []
        for fpath in files:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            # _call("addProjectClip") without get_all_clip_ids nearby = no validation
            if '_call("addProjectClip"' in content or "_call('addProjectClip'" in content:
                if "get_all_clip_ids" not in content:
                    errors.append(
                        f"{os.path.basename(fpath)}: calls addProjectClip without "
                        f"ID diffing (get_all_clip_ids). Import result is unverified."
                    )
        self.assertEqual(errors, [], "Unverified addProjectClip calls:\n" + "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
