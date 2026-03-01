from bpy.types import AddonPreferences
from bpy.utils import register_class, unregister_class

from . import keymaps


class PU_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        keymaps.draw_keymaps(layout, context)


def register():
    register_class(PU_AddonPreferences)


def unregister():
    unregister_class(PU_AddonPreferences)
