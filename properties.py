import bpy
from bpy.types import PropertyGroup
from bpy.props import PointerProperty, StringProperty, IntProperty, CollectionProperty, EnumProperty
from bpy.utils import register_class, unregister_class

from . import constants

# Module-level list to track registered classes for clean unregister
_classes = []


class PawlygonMissingItem(PropertyGroup):
    """Property group for storing a single missing shapekey name in the UI list."""
    name: StringProperty()


def get_list_items(self, context):
    """
    Callback function to generate enum items from available shapekey lists.
    
    Used by the EnumProperty to populate the dropdown with list names from constants.
    
    Returns:
        List of (identifier, name, description) tuples for EnumProperty
    """
    return [
        (name, name, f"Check against {name} list")
        for name in constants.SHAPEKEY_LISTS.keys()
    ]


def register():
    # Register property group class first
    global _classes
    _classes = [PawlygonMissingItem]
    for cls in _classes:
        register_class(cls)

    # Scene properties for missing shapekey workflow
    bpy.types.Scene.pawlygon_target_object = PointerProperty(
        type=bpy.types.Object,
        name="Target Object",
        description="Object to check for missing shapekeys"
    )

    bpy.types.Scene.pawlygon_list_name = EnumProperty(
        name="Shapekey List",
        description="Select which shapekey list to check against",
        items=get_list_items
    )

    # Properties for tracking missing shapekey state
    bpy.types.Scene.pawlygon_missing_count = IntProperty(default=0)
    bpy.types.Scene.pawlygon_missing_list = CollectionProperty(type=PawlygonMissingItem)
    bpy.types.Scene.pawlygon_missing_index = IntProperty(default=0)


def unregister():
    # Remove scene properties first, then unregister classes
    del bpy.types.Scene.pawlygon_target_object
    del bpy.types.Scene.pawlygon_list_name
    del bpy.types.Scene.pawlygon_missing_count
    del bpy.types.Scene.pawlygon_missing_list
    del bpy.types.Scene.pawlygon_missing_index

    global _classes
    for cls in reversed(_classes):
        unregister_class(cls)
    _classes = []
