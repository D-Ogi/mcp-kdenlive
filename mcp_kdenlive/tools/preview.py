"""MCP tools: visual preview — timeline thumbnails, bin clip thumbnails,
contact sheets, and QC crops."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from mcp.server.fastmcp import Context

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PREVIEW_DIR: Path | None = None


def _ensure_preview_dir() -> Path:
    """Return (and create) a temp directory for preview images.

    Cleans files older than 1 hour on each call.
    """
    global _PREVIEW_DIR
    if _PREVIEW_DIR is None:
        _PREVIEW_DIR = Path(os.environ.get("TEMP", "/tmp")) / "kdenlive-mcp-preview"
    _PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # Cleanup stale files (>1 hour)
    cutoff = time.time() - 3600
    for f in _PREVIEW_DIR.iterdir():
        try:
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass

    return _PREVIEW_DIR


def _temp_path(suffix: str = ".jpg") -> str:
    """Return a unique temp file path."""
    d = _ensure_preview_dir()
    return str(d / f"{uuid.uuid4().hex}{suffix}")


def _calc_thumb_size(proj_w: int, proj_h: int, max_short_side: int = 480) -> tuple[int, int]:
    """Calculate thumbnail dimensions preserving aspect ratio.

    The shorter side is capped at max_short_side.
    """
    if proj_w <= 0 or proj_h <= 0:
        return max_short_side, max_short_side
    if proj_w >= proj_h:
        # Landscape — height is short side
        h = min(proj_h, max_short_side)
        w = int(proj_w * h / proj_h)
    else:
        # Portrait — width is short side
        w = min(proj_w, max_short_side)
        h = int(proj_h * w / proj_w)
    return w, h


# Region presets for QC crop (normalized 0-1 coordinates: x, y, w, h)
REGION_PRESETS = {
    "center": (0.25, 0.25, 0.5, 0.5),
    "top-third": (0.25, 0.0, 0.5, 0.333),
    "bottom-third": (0.25, 0.667, 0.5, 0.333),
    "left-third": (0.0, 0.25, 0.333, 0.5),
    "right-third": (0.667, 0.25, 0.333, 0.5),
}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register(mcp, helpers):

    # ── Tool 1: render_frame (timeline thumbnail) ─────────────────────

    @mcp.tool()
    def render_frame(
        ctx: Context,
        frame: int,
        max_short_side: int = 480,
    ) -> str:
        """Render a composited timeline frame as a JPEG thumbnail.

        Returns the file path to the rendered image (attach to response).

        Args:
            frame: Timeline frame number to render.
            max_short_side: Max pixel size of the shorter dimension (default 480).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            dbus = resolve._dbus

            proj_w = dbus.get_project_resolution_width()
            proj_h = dbus.get_project_resolution_height()
            w, h = _calc_thumb_size(proj_w, proj_h, max_short_side)

            out = _temp_path()
            result = dbus.render_timeline_frame(frame, w, h, out)
            if not result:
                return "ERROR: Failed to render timeline frame (D-Bus returned empty)"
            return result
        except Exception as e:
            return f"ERROR: {e}"

    # ── Tool 2: render_bin_frame (bin clip thumbnail) ─────────────────

    @mcp.tool()
    def render_bin_frame(
        ctx: Context,
        bin_id: str,
        frame_position: str = "middle",
        max_short_side: int = 480,
    ) -> str:
        """Render a single frame from a media pool clip as a JPEG thumbnail.

        Args:
            bin_id: Media pool clip ID.
            frame_position: "first", "middle", "last", or an integer frame number.
            max_short_side: Max pixel size of the shorter dimension (default 480).
        """
        try:
            resolve = helpers.get_resolve(ctx)
            dbus = resolve._dbus

            # Resolve frame position
            props = dbus.get_clip_properties(bin_id)
            duration = int(props.get("duration", "0"))

            if frame_position == "first":
                frame = 0
            elif frame_position == "middle":
                frame = max(0, duration // 2)
            elif frame_position == "last":
                frame = max(0, duration - 1)
            else:
                try:
                    frame = int(frame_position)
                except ValueError:
                    return f"ERROR: Invalid frame_position '{frame_position}' — use 'first', 'middle', 'last', or an integer"

            proj_w = dbus.get_project_resolution_width()
            proj_h = dbus.get_project_resolution_height()
            w, h = _calc_thumb_size(proj_w, proj_h, max_short_side)

            out = _temp_path()
            result = dbus.render_bin_frame(bin_id, frame, w, h, out)
            if not result:
                return "ERROR: Failed to render bin frame (D-Bus returned empty)"
            return result
        except Exception as e:
            return f"ERROR: {e}"

    # ── Tool 3: render_contact_sheet (grid of frames) ─────────────────

    @mcp.tool()
    def render_contact_sheet(
        ctx: Context,
        bin_id: str,
        num_frames: int = 8,
        thumb_width: int = 320,
    ) -> str:
        """Render a contact sheet (grid of evenly-spaced frames) from a bin clip.

        Uses Pillow to assemble individual frames into a labeled grid image.
        Returns the file path to the contact sheet JPEG.

        Args:
            bin_id: Media pool clip ID.
            num_frames: Number of frames to sample (default 8, max 16).
            thumb_width: Width of each thumbnail in pixels (default 320).
        """
        try:
            from PIL import Image, ImageDraw, ImageFont

            resolve = helpers.get_resolve(ctx)
            dbus = resolve._dbus
            fps = helpers.get_fps(ctx)

            props = dbus.get_clip_properties(bin_id)
            duration = int(props.get("duration", "0"))
            clip_name = props.get("name", bin_id)

            num_frames = min(max(num_frames, 2), 16)
            if duration <= 0:
                return "ERROR: Clip has zero duration"

            # Calculate evenly-spaced frame positions
            step = max(1, (duration - 1) / (num_frames - 1))
            positions = [int(round(i * step)) for i in range(num_frames)]

            # Project aspect ratio for thumb height
            proj_w = dbus.get_project_resolution_width()
            proj_h = dbus.get_project_resolution_height()
            thumb_h = int(thumb_width * proj_h / proj_w) if proj_w > 0 else int(thumb_width * 9 / 16)

            # Render individual frames
            thumb_paths = []
            for pos in positions:
                p = _temp_path()
                result = dbus.render_bin_frame(bin_id, pos, thumb_width, thumb_h, p)
                if result:
                    thumb_paths.append((pos, result))

            if not thumb_paths:
                return "ERROR: Failed to render any frames"

            # Assemble grid (4 columns)
            cols = 4
            rows = (len(thumb_paths) + cols - 1) // cols
            label_h = 20
            cell_h = thumb_h + label_h
            grid_w = cols * thumb_width
            grid_h = rows * cell_h

            grid = Image.new("RGB", (grid_w, grid_h), (32, 32, 32))
            draw = ImageDraw.Draw(grid)

            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except (IOError, OSError):
                font = ImageFont.load_default()

            for idx, (pos, path) in enumerate(thumb_paths):
                col = idx % cols
                row = idx // cols
                x = col * thumb_width
                y = row * cell_h

                try:
                    thumb = Image.open(path)
                    grid.paste(thumb, (x, y))
                except Exception:
                    pass

                # Label with timecode
                tc = helpers.format_tc(pos, fps)
                draw.text((x + 4, y + thumb_h + 2), f"#{pos} {tc}",
                          fill=(200, 200, 200), font=font)

            # Save contact sheet
            out = _temp_path()
            grid.save(out, "JPEG", quality=90)

            # Clean up individual thumbnails
            for _, path in thumb_paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass

            return out
        except ImportError:
            return "ERROR: Pillow is required for contact sheets. Install with: pip install Pillow"
        except Exception as e:
            return f"ERROR: {e}"

    # ── Tool 4: render_crop (1:1 QC crop) ─────────────────────────────

    @mcp.tool()
    def render_crop(
        ctx: Context,
        frame: int,
        region: str = "center",
        crop_size: int = 480,
        custom_x: int | None = None,
        custom_y: int | None = None,
        custom_w: int | None = None,
        custom_h: int | None = None,
    ) -> str:
        """Render a timeline frame and crop a region for quality control.

        Renders at full project resolution, then crops a crop_size x crop_size
        square at 1:1 pixels (no scaling). Useful for inspecting detail
        (faces, text, artifacts, matching adjacent clips) at native resolution.

        Args:
            frame: Timeline frame number.
            region: Preset region name: "center", "top-third", "bottom-third",
                    "left-third", "right-third". Ignored if custom_x/y/w/h set.
            crop_size: Output crop size in pixels (default 480).
            custom_x: Custom crop X offset in pixels (overrides region preset).
            custom_y: Custom crop Y offset in pixels.
            custom_w: Custom crop width in pixels.
            custom_h: Custom crop height in pixels.
        """
        try:
            from PIL import Image

            resolve = helpers.get_resolve(ctx)
            dbus = resolve._dbus

            proj_w = dbus.get_project_resolution_width()
            proj_h = dbus.get_project_resolution_height()

            # Render at full resolution
            full_path = _temp_path()
            result = dbus.render_timeline_frame(frame, proj_w, proj_h, full_path)
            if not result:
                return "ERROR: Failed to render timeline frame at full resolution"

            img = Image.open(full_path)
            actual_w, actual_h = img.size

            # Determine crop box (always crop_size x crop_size, 1:1 pixels)
            if custom_x is not None and custom_y is not None:
                cx = custom_x
                cy = custom_y
                cw = custom_w if custom_w is not None else crop_size
                ch = custom_h if custom_h is not None else crop_size
            else:
                preset = REGION_PRESETS.get(region)
                if not preset:
                    return f"ERROR: Unknown region '{region}'. Use: {', '.join(REGION_PRESETS.keys())}"
                # Preset gives normalized center point; we cut crop_size x crop_size around it
                rx, ry, rw, rh = preset
                center_x = int((rx + rw / 2) * actual_w)
                center_y = int((ry + rh / 2) * actual_h)
                cx = center_x - crop_size // 2
                cy = center_y - crop_size // 2
                cw = crop_size
                ch = crop_size

            # Clamp to image bounds
            cx = max(0, min(cx, actual_w - cw))
            cy = max(0, min(cy, actual_h - ch))
            cw = min(cw, actual_w - cx)
            ch = min(ch, actual_h - cy)

            cropped = img.crop((cx, cy, cx + cw, cy + ch))

            out = _temp_path()
            cropped.save(out, "JPEG", quality=95)

            # Clean up full-res temp
            try:
                os.unlink(full_path)
            except OSError:
                pass

            return out
        except ImportError:
            return "ERROR: Pillow is required for render_crop. Install with: pip install Pillow"
        except Exception as e:
            return f"ERROR: {e}"
