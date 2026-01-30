"""Timeline tools: summary, tracks, insert, append, move, delete, trim, add_track."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def get_timeline_summary(ctx: Context, track_type: str = "all") -> str:
        """Get timeline contents as markdown tables — one per track.

        Args:
            track_type: Filter by "video", "audio", or "all".

        Returns markdown with clip tables per track (~20 tokens/row).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            dbus = resolve._dbus
            fps = helpers.get_fps(ctx)
            tracks = dbus.get_all_tracks_info()
            if not tracks:
                return "Timeline is empty."

            sections: list[str] = []
            for t in tracks:
                is_audio = t.get("audio")
                ttype = "audio" if is_audio in (True, "true") else "video"
                if track_type != "all" and ttype != track_type:
                    continue

                tid = int(t.get("id", t.get("track_id", 0)))
                tname = t.get("name", "")
                label = ttype[0].upper()  # V or A

                # Get clips on this track via D-Bus directly
                clip_dicts = dbus.get_clips_on_track(tid)
                if not clip_dicts:
                    sections.append(f"## {label}{tid}{f' — {tname}' if tname else ''} — 0 clips")
                    continue

                # Enrich clip dicts with info from scriptGetTimelineClipInfo
                clips_info = []
                for cd in clip_dicts:
                    cid = int(cd.get("id", cd.get("clip_id", -1)))
                    info = dbus.get_timeline_clip_info(cid)
                    info["clip_id"] = cid
                    clips_info.append(info)

                total_frames = sum(int(c.get("duration", 0)) for c in clips_info)
                total_tc = helpers.format_tc(total_frames, fps)
                header = f"## {label}{tid}{f' — {tname}' if tname else ''} — {len(clips_info)} clips, {total_frames}f ({total_tc})"

                # Build table with transition info
                table_header = "| # | clip_id | start | end | dur | filename | transition |"
                table_sep = "|---|---------|-------|-----|-----|----------|------------|"
                rows = [header, "", table_header, table_sep]

                for i, c in enumerate(clips_info):
                    cid = c["clip_id"]
                    s = int(c.get("position", 0))
                    d = int(c.get("duration", 0))
                    e = s + d
                    name = c.get("name", f"clip-{cid}")

                    # Detect overlap with previous clip (= transition)
                    trans = "--"
                    if i > 0:
                        prev_s = int(clips_info[i - 1].get("position", 0))
                        prev_d = int(clips_info[i - 1].get("duration", 0))
                        prev_end = prev_s + prev_d
                        overlap = prev_end - s
                        if overlap > 0:
                            trans = f"dissolve {overlap}f"

                    rows.append(
                        f"| {i} | {cid} | {helpers.format_tc(s, fps)} | "
                        f"{helpers.format_tc(e, fps)} | {d} | {name} | {trans} |"
                    )

                sections.append("\n".join(rows))

            return "\n\n".join(sections) if sections else "No matching tracks."
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def get_track_list(ctx: Context) -> str:
        """List all tracks in the timeline.

        Returns a markdown table: track_id | type | name | clips | total_frames
        """
        try:
            resolve = helpers.get_resolve(ctx)
            dbus = resolve._dbus
            tracks = dbus.get_all_tracks_info()
            if not tracks:
                return "No tracks."

            # Enrich with clip counts
            enriched = []
            for t in tracks:
                tid = int(t.get("id", t.get("track_id", 0)))
                is_audio = t.get("audio")
                tname = t.get("name", "")
                clip_dicts = dbus.get_clips_on_track(tid)
                nclips = len(clip_dicts)
                total = 0
                for cd in clip_dicts:
                    cid = int(cd.get("id", cd.get("clip_id", -1)))
                    info = dbus.get_timeline_clip_info(cid)
                    total += int(info.get("duration", 0)) if info else 0
                enriched.append({
                    "id": tid, "audio": is_audio,
                    "name": tname, "clips": nclips, "total_frames": total,
                })
            return helpers.tracks_table(enriched)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def get_clip_info(ctx: Context, clip_id: int) -> str:
        """Get detailed info about a specific timeline clip.

        Args:
            clip_id: The clip's integer ID on the timeline.
        """
        try:
            tl = helpers.get_timeline(ctx)
            fps = helpers.get_fps(ctx)
            # Use D-Bus to get clip info directly
            resolve = helpers.get_resolve(ctx)
            info = resolve._dbus.get_timeline_clip_info(clip_id)
            if not info:
                return f"ERROR: Clip {clip_id} not found."

            s = info.get("start", 0)
            e = info.get("end", 0)
            d = info.get("duration", 0)
            name = info.get("name", "")
            track = info.get("track_id", "")
            bin_id = info.get("bin_id", "")
            in_pt = info.get("in_point", info.get("left_offset", 0))

            lines = [
                f"**Name:** {name}",
                f"**clip_id:** {clip_id}",
                f"**Track:** {track}",
                f"**Start:** {helpers.format_tc(s, fps)} (frame {s})",
                f"**End:** {helpers.format_tc(e, fps)} (frame {e})",
                f"**Duration:** {d} frames",
                f"**In-point:** {in_pt} frames",
                f"**bin_id:** {bin_id}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def insert_clip(ctx: Context, bin_id: str, track_id: int, position: int) -> str:
        """Insert a single clip at position. For assembling a full timeline from scene clips, use the build_timeline tool instead.

        Args:
            bin_id: Media pool clip ID (string).
            track_id: Target track ID.
            position: Position in frames on the timeline.
        """
        try:
            tl = helpers.get_timeline(ctx)
            fps = helpers.get_fps(ctx)
            item = tl.InsertClip(bin_id, track_id, position)
            if item is None:
                return f"ERROR: Could not insert bin_id={bin_id} at track {track_id}, frame {position}"
            tc = helpers.format_tc(position, fps)
            return f"Inserted clip {item.clip_id} at {tc} on track {track_id}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def append_clips(ctx: Context, bin_ids: list[str], track_id: int, start_position: int = 0) -> str:
        """Append multiple clips sequentially on a track. For full assembly with transitions and audio, use build_timeline instead.

        Args:
            bin_ids: List of media pool clip IDs to append in order.
            track_id: Target track ID.
            start_position: Starting frame position (default 0).

        Returns a table of inserted clips.
        """
        try:
            tl = helpers.get_timeline(ctx)
            fps = helpers.get_fps(ctx)
            items = tl.InsertClipsSequentially(bin_ids, track_id, start_position)
            if not items:
                return "ERROR: No clips inserted."
            table = helpers.clips_table(items, fps)
            return f"Appended {len(items)} clip(s):\n\n{table}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def move_clip(ctx: Context, clip_id: int, track_id: int, position: int) -> str:
        """Move a timeline clip to a new track/position.

        Args:
            clip_id: The clip's timeline ID.
            track_id: Target track ID.
            position: New position in frames.
        """
        try:
            tl = helpers.get_timeline(ctx)
            fps = helpers.get_fps(ctx)
            # Get item by iterating tracks
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.move_clip(clip_id, track_id, position)
            if not ok:
                return f"ERROR: Could not move clip {clip_id}"
            tc = helpers.format_tc(position, fps)
            return f"Moved clip {clip_id} to track {track_id} at {tc}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def delete_clip(ctx: Context, clip_id: int) -> str:
        """Delete a clip from the timeline.

        Args:
            clip_id: The clip's timeline ID.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.delete_timeline_clip(clip_id)
            if not ok:
                return f"ERROR: Could not delete clip {clip_id}"
            return f"Deleted clip {clip_id}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def add_track(ctx: Context, name: str = "", audio: bool = False) -> str:
        """Add a new track to the timeline.

        Args:
            name: Track name (optional).
            audio: True for audio track, False for video track.
        """
        try:
            tl = helpers.get_timeline(ctx)
            tid = tl.AddTrack(name, audio)
            kind = "audio" if audio else "video"
            label = f"'{name}' " if name else ""
            return f"Added {kind} track {label}(id: {tid})"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def split_clip(ctx: Context, clip_id: int, frame: int) -> str:
        """Split a clip into two parts at the given frame position.

        Args:
            clip_id: Timeline clip ID.
            frame: Absolute timeline frame position where to cut.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            fps = helpers.get_fps(ctx)
            ok = resolve._dbus.cut_clip(clip_id, frame)
            if not ok:
                return f"ERROR: Could not split clip {clip_id} at frame {frame}"
            tc = helpers.format_tc(frame, fps)
            return f"Split clip {clip_id} at {tc} (frame {frame})"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def trim_clip(ctx: Context, clip_id: int, new_duration: int, from_right: bool = True) -> str:
        """Trim a timeline clip to a new duration.

        Args:
            clip_id: The clip's timeline ID.
            new_duration: Desired duration in frames.
            from_right: If True, trims from the right edge. If False, from the left.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            info = resolve._dbus.get_timeline_clip_info(clip_id)
            old_dur = info.get("duration", 0) if info else 0
            actual = resolve._dbus.resize_clip(clip_id, new_duration, from_right)
            return f"Trimmed {clip_id}: {old_dur} -> {actual} frames"
        except Exception as e:
            return f"ERROR: {e}"
