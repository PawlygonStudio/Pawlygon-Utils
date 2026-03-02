import bpy
import tomllib
import pathlib
from bpy.types import AddonPreferences
from bpy.utils import register_class, unregister_class

from . import keymaps, updater


class PU_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout

        # --- Update section ---
        box = layout.box()

        # Current version label — read from the manifest (extensions have no bl_info)
        _manifest = tomllib.loads(
            (pathlib.Path(__file__).parent / "blender_manifest.toml").read_text(encoding="utf-8")
        )
        version_str = _manifest.get("version", "0.0.0")

        row = box.row()
        row.label(text=f"Version {version_str}", icon='INFO')

        # Status label — icon and text vary by state
        status  = updater._update_status
        message = updater._update_message
        _STATUS_ICON = {
            'UP_TO_DATE':       'CHECKMARK',
            'UPDATE_AVAILABLE': 'TRIA_UP',
            'CHECKING':         'TIME',
            'DOWNLOADING':      'TIME',
            'INSTALLED':        'CHECKMARK',
            'ERROR':            'CANCEL',
        }
        if status and message:
            row = box.row()
            row.label(text=message, icon=_STATUS_ICON.get(status, 'NONE'))

        # "Check for Updates" button — greyed out while a check is in flight
        row = box.row(align=True)
        row.enabled = status != 'CHECKING'
        row.operator("pawlygon.check_update", text="Check for Updates", icon='FILE_REFRESH')

        # Source dropdown + Update button — always visible
        sub = box.row(align=True)
        prefs = context.preferences.addons[__package__].preferences
        sub.prop(prefs, "update_source", text="")

        update_row = sub.row()
        # Disabled during active operations or after install.
        # UP_TO_DATE only disables the Latest Release path; Main Branch stays clickable
        # (the operator's invoke() will ask for confirmation in that case).
        main_branch_up_to_date = (
            status == 'UP_TO_DATE'
            and prefs.update_source == 'MAIN_BRANCH'
        )
        update_row.enabled = status not in {'CHECKING', 'DOWNLOADING', 'INSTALLED'} and (
            status != 'UP_TO_DATE' or main_branch_up_to_date
        )
        if status == 'UP_TO_DATE' and not main_branch_up_to_date:
            btn_text = "Up to date"
        elif status == 'INSTALLED':
            btn_text = "Restart Blender"
        else:
            btn_text = "Update"
        op = update_row.operator("pawlygon.update_addon", text=btn_text, icon='IMPORT')
        op.source = prefs.update_source

        layout.separator()

        # --- Keymaps section ---
        keymaps.draw_keymaps(layout, context)

    # Persistent preference for the chosen update source
    update_source: bpy.props.EnumProperty(
        name="Update Source",
        description="Where to download the update from",
        items=[
            ('LATEST_RELEASE', "Latest Release", "Download the latest tagged release (recommended)"),
            ('MAIN_BRANCH',    "Main Branch",    "Download the current tip of the main branch"),
        ],
        default='LATEST_RELEASE',
    )


def register():
    register_class(PU_AddonPreferences)


def unregister():
    unregister_class(PU_AddonPreferences)
