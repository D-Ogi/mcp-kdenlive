"""Transition tools: add, batch, remove."""

from __future__ import annotations

from mcp.server.fastmcp import Context


def register(mcp, helpers):

    @mcp.tool()
    def add_transition(ctx: Context, clip_id_a: int, clip_id_b: int, duration: int = 13) -> str:
        """Add a dissolve transition between two adjacent clips. For batch transitions on all clips, use add_transitions_batch instead.

        Args:
            clip_id_a: First clip's timeline ID.
            clip_id_b: Second clip's timeline ID.
            duration: Transition duration in frames (default 13 ~ 0.5s at 25fps).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.add_mix(clip_id_a, clip_id_b, duration)
            if not ok:
                return f"ERROR: Could not add transition between {clip_id_a} and {clip_id_b}"
            return f"Added dissolve ({duration}f) between clips {clip_id_a} and {clip_id_b}"
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def add_transitions_batch(ctx: Context, track_id: int, duration: int = 13) -> str:
        """Add dissolve transitions between all adjacent clip pairs on a track.

        Args:
            track_id: Track ID to process.
            duration: Transition duration in frames (default 13).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            clips = resolve._dbus.get_clips_on_track(track_id)
            if not clips or len(clips) < 2:
                return "ERROR: Need at least 2 clips on the track."

            count = 0
            errors = []
            for i in range(len(clips) - 1):
                a_id = clips[i].get("clip_id", clips[i].get("id"))
                b_id = clips[i + 1].get("clip_id", clips[i + 1].get("id"))
                ok = resolve._dbus.add_mix(a_id, b_id, duration)
                if ok:
                    count += 1
                else:
                    errors.append(f"{a_id}->{b_id}")

            result = f"Added {count} transition(s) ({duration}f each)"
            if errors:
                result += f"\nFailed pairs: {', '.join(errors)}"
            return result
        except Exception as e:
            return f"ERROR: {e}"

    @mcp.tool()
    def remove_transition(ctx: Context, clip_id: int) -> str:
        """Remove a transition (mix) from a clip.

        Args:
            clip_id: The clip's timeline ID that has the transition.
        """
        try:
            resolve = helpers.get_resolve(ctx)
            ok = resolve._dbus.remove_mix(clip_id)
            if not ok:
                return f"ERROR: Could not remove transition from clip {clip_id}"
            return f"Removed transition from clip {clip_id}"
        except Exception as e:
            return f"ERROR: {e}"
