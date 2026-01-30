"""Checkpoint tools: save/restore project state via SaveAs to temp paths."""

from __future__ import annotations

import os
import time

from mcp.server.fastmcp import Context


# In-process checkpoint registry: {label: file_path}
_checkpoints: dict[str, str] = {}


def register(mcp, helpers):

    @mcp.tool()
    def checkpoint_save(ctx: Context, label: str = "") -> str:
        """Save a checkpoint of the current project state.

        Creates a timestamped copy of the project file that can be restored later.

        Args:
            label: Optional label for the checkpoint. Auto-generated if empty.
        """
        try:
            proj = helpers.get_project(ctx)
            orig_path = proj.GetProjectPath()
            if not orig_path:
                return "ERROR: Project has no path — save it first."

            if not label:
                label = f"ckpt-{int(time.time())}"

            base, ext = os.path.splitext(orig_path)
            ckpt_path = f"{base}__{label}{ext}"

            ok = proj.SaveAs(ckpt_path)
            if not ok:
                return f"ERROR: Could not save checkpoint to {ckpt_path}"

            # Re-save back to original path so we continue working on original
            proj.SaveAs(orig_path)

            _checkpoints[label] = ckpt_path
            return f"Checkpoint saved: {ckpt_path}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def checkpoint_restore(ctx: Context, label: str = "") -> str:
        """Restore a previously saved checkpoint.

        Args:
            label: Checkpoint label to restore. If empty, restores the most recent.
        """
        try:
            if not _checkpoints:
                return "ERROR: No checkpoints available."

            if label:
                ckpt_path = _checkpoints.get(label)
                if not ckpt_path:
                    available = ", ".join(_checkpoints.keys())
                    return f"ERROR: Checkpoint '{label}' not found. Available: {available}"
            else:
                # Most recent
                label = list(_checkpoints.keys())[-1]
                ckpt_path = _checkpoints[label]

            if not os.path.exists(ckpt_path):
                return f"ERROR: Checkpoint file missing: {ckpt_path}"

            resolve = helpers.get_resolve(ctx)
            pm = resolve.GetProjectManager()
            proj = pm.LoadProject(ckpt_path)
            if proj is None:
                return f"ERROR: Could not load checkpoint {ckpt_path}"

            return f"Restored checkpoint '{label}' from {ckpt_path}"
        except Exception as e:
            return f"ERROR: {e}"
