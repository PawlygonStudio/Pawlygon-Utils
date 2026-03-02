import bpy
from . import constants, keymaps, operators, panels, preferences, properties, updater


def register():
    # Register in dependency order: properties -> operators -> updater -> panels -> prefs -> keymaps
    properties.register()
    operators.register()
    updater.register()
    panels.register()
    preferences.register()
    keymaps.register()


def unregister():
    # Unregister in reverse order to properly clean up dependencies
    keymaps.unregister()
    preferences.unregister()
    panels.unregister()
    updater.unregister()
    operators.unregister()
    properties.unregister()
