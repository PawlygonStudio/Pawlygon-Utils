# Blender addon metadata
bl_info = {
    "name": "Pawlygon Utils",
    "description": "Shapekey manipulation tools",
    "author": "Pawlygon",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Pawlygon Utils",
    "category": "Object",
}

import bpy
from . import constants, operators, panels, properties, utils


def register():
    # Register in dependency order: properties -> operators -> panels
    # Properties must be registered first as operators/panels depend on them
    properties.register()
    operators.register()
    panels.register()


def unregister():
    # Unregister in reverse order to properly clean up dependencies
    panels.unregister()
    operators.unregister()
    properties.unregister()
