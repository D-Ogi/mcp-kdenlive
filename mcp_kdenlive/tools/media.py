"""Media pool tools: import, glob import, listing, bin folders."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def get_media_pool(ctx: Context, folder_id: str = "-1") -> str:
        """List all clips in the media pool (or a specific folder).

        Args:
            folder_id: Bin folder ID. "-1" for all clips.

        Returns a markdown table: bin_id | name | type | duration_frames | duration_tc
        """
        try:
            pool = helpers.get_media_pool(ctx)
            fps = helpers.get_fps(ctx)
            if folder_id == "-1":
                items = pool.GetAllClips()
            else:
                # Get clips from specific folder via D-Bus
                resolve = helpers.get_resolve(ctx)
                dbus = resolve._dbus
                clip_ids = dbus.get_folder_clip_ids(folder_id)
                items = [pool.GetClipById(cid) for cid in clip_ids]
            if not items:
                return "Media pool is empty."
            return helpers.media_table(items, fps)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def import_media(ctx: Context, file_paths: list[str], folder_name: str = "") -> str:
        """Import media files into the media pool. For full import + timeline assembly, use build_timeline instead.

        Args:
            file_paths: List of absolute file paths to import.
            folder_name: Optional folder name to import into (created if missing).

        Returns a markdown table of imported clips.
        """
        try:
            pool = helpers.get_media_pool(ctx)
            fps = helpers.get_fps(ctx)
            folder = None
            if folder_name:
                folder = pool.AddSubFolder(None, folder_name)
            items = pool.ImportMedia(file_paths, folder)
            if not items:
                return "ERROR: No clips imported."
            return f"Imported {len(items)} clip(s):\n\n{helpers.media_table(items, fps)}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def import_media_glob(ctx: Context, directory: str, pattern: str = "*.mp4", folder_name: str = "") -> str:
        """Import media files matching a glob pattern from a directory.

        Args:
            directory: Directory to scan.
            pattern: Glob pattern (e.g. "*.mp4", "scene*-final.mp4").
            folder_name: Optional folder name to import into.

        Returns a markdown table of imported clips.
        """
        try:
            pool = helpers.get_media_pool(ctx)
            fps = helpers.get_fps(ctx)
            folder = None
            if folder_name:
                folder = pool.AddSubFolder(None, folder_name)
            items = pool.ImportMediaFromFolder(directory, pattern, folder)
            if not items:
                return "ERROR: No files matched or import failed."
            return f"Imported {len(items)} clip(s):\n\n{helpers.media_table(items, fps)}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def create_bin_folder(ctx: Context, name: str, parent_id: str = "-1") -> str:
        """Create a folder in the media pool bin.

        Args:
            name: Folder name.
            parent_id: Parent folder ID. "-1" for root.
        """
        try:
            pool = helpers.get_media_pool(ctx)
            parent = None
            if parent_id != "-1":
                # Use root folder as parent; sub-folder navigation limited by D-Bus
                parent = pool.GetRootFolder()
            folder = pool.AddSubFolder(parent, name)
            if folder is None:
                return f"ERROR: Could not create folder '{name}'"
            fid = folder.folder_id if hasattr(folder, "folder_id") else "?"
            return f"Created folder '{name}' (id: {fid})"
        except Exception as e:
            return f"ERROR: {e}"
