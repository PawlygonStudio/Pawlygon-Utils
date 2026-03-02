import bpy
import urllib.request
import urllib.error
import json
import tempfile
import os
import threading
import tomllib
import pathlib
from bpy.types import Operator
from bpy.props import EnumProperty
from bpy.utils import register_class, unregister_class

# GitHub repo identifiers
_GITHUB_REPO = "PawlygonStudio/Pawlygon-Utils"
_RELEASES_API_URL = f"https://api.github.com/repos/{_GITHUB_REPO}/releases/latest"
_MAIN_BRANCH_URL  = f"https://github.com/{_GITHUB_REPO}/archive/refs/heads/main.zip"

# Update state — populated by PU_OT_check_update / PU_OT_update_addon
# Status values: '' (unchecked), 'CHECKING', 'UP_TO_DATE', 'UPDATE_AVAILABLE',
#                'DOWNLOADING', 'INSTALLED', 'ERROR'
_update_status: str = ''
_update_message: str = ''
_latest_release_url: str = ''

# Background thread handle — only one update operation runs at a time
_update_thread: threading.Thread | None = None

# Module-level list to track registered classes for clean unregister
_classes = []


def _redraw_timer_callback() -> float | None:
    """bpy.app.timers callback: force preferences area redraws while an update op is running.

    Returns the repeat interval (seconds) while still running, or None to cancel.
    """
    if _update_status in {'CHECKING', 'DOWNLOADING'}:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'PREFERENCES':
                    area.tag_redraw()
        return 0.1  # poll again in 100 ms
    return None  # cancel the timer once the operation finishes


class PU_OT_check_update(Operator):
    """Operator: Query GitHub Releases API to check for a newer version."""
    bl_idname = "pawlygon.check_update"
    bl_label = "Check for Updates"
    bl_description = "Check GitHub for a newer release"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # Prevent re-entry while a check is already in progress
        return _update_status != 'CHECKING'

    def execute(self, context):
        global _update_status, _update_message, _latest_release_url, _update_thread

        _manifest = tomllib.loads(
            (pathlib.Path(__file__).parent / "blender_manifest.toml").read_text(encoding="utf-8")
        )
        current = tuple(int(x) for x in _manifest["version"].split("."))

        _update_status = 'CHECKING'
        _update_message = 'Checking for updates\u2026'

        def _do_check():
            global _update_status, _update_message, _latest_release_url
            try:
                req = urllib.request.Request(
                    _RELEASES_API_URL,
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "Pawlygon-Utils"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
            except urllib.error.URLError as e:
                _update_status = 'ERROR'
                _update_message = f"Could not reach GitHub: {e.reason}"
                return
            except Exception as e:
                _update_status = 'ERROR'
                _update_message = f"Check failed: {e}"
                return

            tag = data.get("tag_name", "")
            numeric = tag.lstrip("vV")
            try:
                latest = tuple(int(x) for x in numeric.split("."))
            except ValueError:
                _update_status = 'ERROR'
                _update_message = f"Unrecognised release tag: {tag!r}"
                return

            zip_asset = next(
                (a["browser_download_url"] for a in data.get("assets", []) if a["name"].endswith(".zip")),
                data.get("zipball_url", ""),
            )
            _latest_release_url = zip_asset

            current_str = ".".join(str(v) for v in current)
            latest_str  = ".".join(str(v) for v in latest)

            if latest > current:
                _update_status = 'UPDATE_AVAILABLE'
                _update_message = f"Update available: v{latest_str} (current: v{current_str})"
            else:
                _update_status = 'UP_TO_DATE'
                _update_message = f"Up to date (v{current_str})"

        _update_thread = threading.Thread(target=_do_check, daemon=True)
        _update_thread.start()

        # Register a timer to keep repainting the preferences panel while checking
        if not bpy.app.timers.is_registered(_redraw_timer_callback):
            bpy.app.timers.register(_redraw_timer_callback, first_interval=0.1)

        return {'FINISHED'}


class PU_OT_update_addon(Operator):
    """Operator: Download and install the addon from GitHub."""
    bl_idname = "pawlygon.update_addon"
    bl_label = "Update Addon"
    bl_description = "Download and install the selected version from GitHub"
    bl_options = {'REGISTER'}

    source: EnumProperty(
        name="Source",
        description="Where to download the update from",
        items=[
            ('LATEST_RELEASE', "Latest Release", "Download the latest tagged release (recommended)"),
            ('MAIN_BRANCH',    "Main Branch",    "Download the current tip of the main branch"),
        ],
        default='LATEST_RELEASE',
    )

    @classmethod
    def poll(cls, context):
        # Always blocked during active operations or after a successful install
        if _update_status in {'CHECKING', 'DOWNLOADING', 'INSTALLED'}:
            return False
        # UP_TO_DATE blocks LATEST_RELEASE (no point re-downloading the same version)
        # but still allows MAIN_BRANCH (user may want bleeding-edge; confirmed via invoke)
        return True

    def invoke(self, context, event):
        # Ask for confirmation only when installing main branch over an up-to-date release
        if self.source == 'MAIN_BRANCH' and _update_status == 'UP_TO_DATE':
            return context.window_manager.invoke_confirm(
                self,
                event,
                message="The addon is already up to date. Install the main branch anyway?",
            )
        return self.execute(context)

    def execute(self, context):
        global _update_status, _update_message, _update_thread

        addon_name = __package__

        if self.source == 'LATEST_RELEASE':
            url = _latest_release_url or f"https://api.github.com/repos/{_GITHUB_REPO}/zipball"
        else:
            url = _MAIN_BRANCH_URL

        _update_status = 'DOWNLOADING'
        _update_message = 'Downloading update\u2026'

        def _do_download():
            global _update_status, _update_message

            # Download zip to a temp file
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Pawlygon-Utils"})
                tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    tmp.write(resp.read())
                tmp.close()
            except Exception as e:
                _update_status = 'ERROR'
                _update_message = f"Download failed: {e}"
                return

            # Install must happen on the main thread — schedule via a one-shot timer
            tmp_path = tmp.name

            def _install_on_main_thread():
                global _update_status, _update_message
                try:
                    bpy.ops.preferences.addon_install(overwrite=True, filepath=tmp_path)
                    bpy.ops.preferences.addon_enable(module=addon_name)
                    bpy.ops.wm.save_userpref()
                    _update_status = 'INSTALLED'
                    _update_message = 'Update installed — restart Blender to apply'
                except Exception as e:
                    _update_status = 'ERROR'
                    _update_message = f"Install failed: {e}"
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                return None  # one-shot: do not repeat

            bpy.app.timers.register(_install_on_main_thread, first_interval=0.0)

        _update_thread = threading.Thread(target=_do_download, daemon=True)
        _update_thread.start()

        # Register the redraw timer (shared with check_update)
        if not bpy.app.timers.is_registered(_redraw_timer_callback):
            bpy.app.timers.register(_redraw_timer_callback, first_interval=0.1)

        return {'FINISHED'}


def register():
    global _classes
    _classes = [
        PU_OT_check_update,
        PU_OT_update_addon,
    ]
    for cls in _classes:
        register_class(cls)


def unregister():
    global _classes
    for cls in reversed(_classes):
        unregister_class(cls)
    _classes = []
