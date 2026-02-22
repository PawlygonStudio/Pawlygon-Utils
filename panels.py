import bpy
from bpy.types import Panel, UIList
from bpy.utils import register_class, unregister_class

from . import constants

# Module-level list to track registered classes for clean unregister
_classes = []


class PU_UL_missing_list(UIList):
    """UI List widget for displaying missing shapekeys."""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name, icon='SHAPEKEY_DATA')


class PU_PT_split_panel(Panel):
    """Panel: Split shapekey by vertex groups (e.g., Left/Right)."""
    bl_label = "Split Shapekey"
    bl_idname = "PU_PT_split"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pawlygon Utils"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        # Validate current state for button enabling
        is_valid = (
            obj
            and obj.type == 'MESH'
            and obj.data.shape_keys
            and obj.active_shape_key
        )
        is_correct_mode = obj and obj.mode in {'OBJECT', 'SCULPT'}

        # Show status information to user
        if not is_correct_mode:
            layout.label(text="Switch to Object or Sculpt mode", icon='INFO')
        elif is_valid:
            layout.label(text=f"Active: {obj.active_shape_key.name}")
        else:
            layout.label(text="Select a mesh with shapekeys", icon='INFO')

        layout.separator()

        # Get vertex group names for checking availability
        vg_names = [vg.name for vg in obj.vertex_groups] if obj and obj.vertex_groups else []

        # Draw split buttons for each configured vertex group pair
        for group_a, group_b in constants.VERTEX_GROUP_PAIRS:
            has_a = group_a in vg_names
            has_b = group_b in vg_names
            has_both = has_a and has_b

            col = layout.column()

            if is_valid and has_both and is_correct_mode:
                # Button enabled: all conditions met
                op = col.operator(
                    "pawlygon.split_shapekey",
                    text=f"Split {group_a}/{group_b}"
                )
                op.group_a = group_a
                op.group_b = group_b
            else:
                # Button disabled: show why
                row = col.row()
                row.enabled = False
                row.operator("pawlygon.split_shapekey", text=f"Split {group_a}/{group_b}")

                # Show missing vertex groups
                if not has_both:
                    missing = []
                    if not has_a:
                        missing.append(group_a)
                    if not has_b:
                        missing.append(group_b)
                    row = col.row()
                    row.label(text=f"Missing Vertex Group: {', '.join(missing)}", icon='ERROR')


class PU_PT_missing_panel(Panel):
    """Panel: Check and create missing shapekeys against predefined lists."""
    bl_label = "Missing Shapekeys"
    bl_idname = "PU_PT_missing"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pawlygon Utils"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Target object selector
        layout.prop_search(
            scene, "pawlygon_target_object",
            context.scene, "objects",
            text="Target Object"
        )

        # Shapekey list selector (dropdown populated from constants)
        layout.prop(context.scene, "pawlygon_list_name", text="List")

        layout.operator("pawlygon.check_missing", text="Check Missing")

        # Show results if missing shapekeys were found
        missing_count = scene.pawlygon_missing_count
        if missing_count > 0:
            layout.separator()
            layout.label(text=f"Missing: {missing_count} shapekeys", icon='ERROR')

            # Display missing shapekeys in a scrollable list
            layout.template_list(
                "PU_UL_missing_list", "",
                scene, "pawlygon_missing_list",
                scene, "pawlygon_missing_index",
                rows=5
            )

            layout.operator("pawlygon.create_missing", text="Create Missing")


class PU_PT_cleanup_panel(Panel):
    """Panel: Cleanup operations for .old shapekey management."""
    bl_label = "Cleanup"
    bl_idname = "PU_PT_cleanup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pawlygon Utils"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        # Validate current state for button enabling
        is_valid = (
            obj
            and obj.type == 'MESH'
            and obj.data.shape_keys
        )
        is_correct_mode = obj and obj.mode in {'OBJECT', 'SCULPT'}

        # Show status information to user
        if not is_correct_mode:
            layout.label(text="Switch to Object or Sculpt mode", icon='INFO')
        elif not is_valid:
            layout.label(text="Select a mesh with shapekeys", icon='INFO')

        # Cleanup operations column
        col = layout.column()
        col.enabled = is_valid and is_correct_mode
        col.operator("pawlygon.move_old_shapekeys", text="Move .old to Bottom")
        col.operator("pawlygon.delete_old_shapekeys", text="Delete .old Shapekeys")


def register():
    # Register all panel and UIList classes with Blender
    global _classes
    _classes = [PU_UL_missing_list, PU_PT_split_panel, PU_PT_missing_panel, PU_PT_cleanup_panel]
    for cls in _classes:
        register_class(cls)


def unregister():
    # Unregister in reverse order for clean removal
    global _classes
    for cls in reversed(_classes):
        unregister_class(cls)
    _classes = []
