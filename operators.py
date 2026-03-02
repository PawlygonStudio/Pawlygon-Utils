import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy.utils import register_class, unregister_class

from . import constants, utils

# Module-level list to track registered classes for clean unregister
_classes = []

# Modes in which shapekey manipulation operators are available
ALLOWED_MODES = {'OBJECT', 'SCULPT'}


class PU_OT_move_old_shapekeys(Operator):
    """Operator: Move shapekeys ending with .old suffix to bottom of the list."""
    bl_idname = "pawlygon.move_old_shapekeys"
    bl_label = "Move .old Shapekeys to Bottom"
    bl_description = "Move .old shapekeys to the bottom of the list"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only enable for mesh objects with shapekeys in appropriate modes
        obj = context.active_object
        return bool(
            obj
            and obj.type == 'MESH'
            and obj.data.shape_keys
            and obj.mode in ALLOWED_MODES
        )

    def execute(self, context):
        obj = context.active_object
        moved = utils.move_old_shapekeys_to_bottom(obj)

        # Report results to user via Blender's notification system
        if moved > 0:
            self.report({'INFO'}, f"Moved {moved} shapekey(s) to bottom")
        else:
            self.report({'INFO'}, "No .old shapekeys found")

        return {'FINISHED'}


class PU_OT_delete_old_shapekeys(Operator):
    """Operator: Delete all shapekeys ending with .old suffix."""
    bl_idname = "pawlygon.delete_old_shapekeys"
    bl_label = "Delete .old Shapekeys"
    bl_description = "Permanently delete all shapekeys ending with .old"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only enable for mesh objects with shapekeys in appropriate modes
        obj = context.active_object
        return bool(
            obj
            and obj.type == 'MESH'
            and obj.data.shape_keys
            and obj.mode in ALLOWED_MODES
        )

    def execute(self, context):
        obj = context.active_object
        deleted = utils.delete_old_shapekeys(obj)

        if deleted > 0:
            self.report({'INFO'}, f"Deleted {deleted} shapekey(s)")
        else:
            self.report({'INFO'}, "No .old shapekeys found")

        return {'FINISHED'}


class PU_OT_split_shapekey(Operator):
    """Operator: Split active shapekey into two based on vertex groups (e.g., Left/Right)."""
    bl_idname = "pawlygon.split_shapekey"
    bl_label = "Split Shapekey"
    bl_description = "Split the active shapekey into two using vertex groups as masks"
    bl_options = {'UNDO'}

    # Vertex group names passed from panel buttons
    group_a: StringProperty()
    group_b: StringProperty()

    @classmethod
    def poll(cls, context):
        # Requires active shapekey to split (not just any shapekey)
        obj = context.active_object
        return bool(
            obj
            and obj.type == 'MESH'
            and obj.data.shape_keys
            and obj.active_shape_key
        )

    def execute(self, context):
        obj = context.active_object

        if obj.mode not in ALLOWED_MODES:
            mode_name = obj.mode.replace('_', ' ').title()
            self.report({'WARNING'}, f"Split Shapekey is not available in {mode_name} mode. Switch to Object or Sculpt mode.")
            return {'CANCELLED'}

        result = utils.split_shapekey_by_groups(obj, self.group_a, self.group_b)

        if result:
            self.report({'INFO'}, f"Created: {result[0]} and {result[1]}")
        else:
            self.report({'WARNING'}, "Could not split. Check vertex groups exist.")
            return {'CANCELLED'}

        return {'FINISHED'}


class PU_OT_check_missing(Operator):
    """Operator: Check target object against a predefined shapekey list for missing keys."""
    bl_idname = "pawlygon.check_missing"
    bl_label = "Check Missing Shapekeys"
    bl_description = "Compare the target object's shapekeys against the selected list"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # Requires a mesh target object to be set in scene properties
        target = context.scene.pawlygon_target_object
        return bool(target and target.type == 'MESH')

    def execute(self, context):
        target = context.scene.pawlygon_target_object
        list_name = context.scene.pawlygon_list_name
        # Get the expected shapekey names from constants based on selected list
        expected_keys = constants.SHAPEKEY_LISTS.get(list_name, [])

        missing = utils.get_missing_shapekeys(target, expected_keys)
        # Update scene properties with missing shapekey count and list
        context.scene.pawlygon_missing_count = len(missing)
        context.scene.pawlygon_all_present = len(missing) == 0
        context.scene.pawlygon_missing_list.clear()

        # Populate the missing list UI collection
        for name in missing:
            item = context.scene.pawlygon_missing_list.add()
            item.name = name

        if missing:
            self.report({'INFO'}, f"Found {len(missing)} missing shapekeys")
        else:
            self.report({'INFO'}, "All shapekeys present!")

        return {'FINISHED'}


class PU_OT_create_missing(Operator):
    """Operator: Create all missing shapekeys detected by the check operation."""
    bl_idname = "pawlygon.create_missing"
    bl_label = "Create Missing Shapekeys"
    bl_description = "Add all missing shapekeys to the target object as blank keys"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only enable if there are missing shapekeys to create for a mesh in Object mode
        target = context.scene.pawlygon_target_object
        return bool(
            target
            and target.type == 'MESH'
            and target.mode == 'OBJECT'
            and context.scene.pawlygon_missing_count > 0
        )

    def execute(self, context):
        target = context.scene.pawlygon_target_object
        missing_list = context.scene.pawlygon_missing_list

        # Ensure object has a Basis shapekey (required before adding others)
        if not target.data.shape_keys:
            target.shape_key_add(name='Basis', from_mix=False)

        # Create each missing shapekey (empty, from_mix=False)
        # Guard checks in case user manually added keys between Check and Create
        created = 0
        for item in missing_list:
            if item.name not in target.data.shape_keys.key_blocks:
                sk = target.shape_key_add(name=item.name, from_mix=False)
                sk.value = 0.0
                created += 1

        # Clear the missing list after creating
        context.scene.pawlygon_missing_count = 0
        context.scene.pawlygon_missing_list.clear()

        self.report({'INFO'}, f"Created {created} shapekey(s)")
        return {'FINISHED'}


def register():
    # Register all operator classes with Blender
    global _classes
    _classes = [
        PU_OT_move_old_shapekeys,
        PU_OT_delete_old_shapekeys,
        PU_OT_split_shapekey,
        PU_OT_check_missing,
        PU_OT_create_missing,
    ]
    for cls in _classes:
        register_class(cls)


def unregister():
    # Unregister in reverse order for clean removal
    global _classes
    for cls in reversed(_classes):
        unregister_class(cls)
    _classes = []
