import bpy

from . import constants


# Keep (km, kmi) pairs for clean unregister — conventional Blender addon pattern
_addon_keymaps = []


_KEYMAP_TARGETS = [
    ("Window", 'EMPTY', 'WINDOW'),
]


def _is_matching_split_item(kmi, group_a, group_b):
    return (
        kmi.idname == "pawlygon.split_shapekey"
        and getattr(kmi.properties, "group_a", "") == group_a
        and getattr(kmi.properties, "group_b", "") == group_b
    )


def _find_keymap(keyconfig, name, space_type, region_type):
    for km in keyconfig.keymaps:
        if km.name == name and km.space_type == space_type and km.region_type == region_type:
            return km
    return None


def _remove_existing_split_items(keyconfig):
    for km in keyconfig.keymaps:
        for kmi in list(km.keymap_items):
            if kmi.idname != "pawlygon.split_shapekey":
                continue

            has_matching_pair = any(
                _is_matching_split_item(kmi, group_a, group_b)
                for group_a, group_b in constants.VERTEX_GROUP_PAIRS
            )
            if has_matching_pair:
                km.keymap_items.remove(kmi)


def register():
    wm = bpy.context.window_manager
    if not wm or not wm.keyconfigs or not wm.keyconfigs.addon:
        return

    _addon_keymaps.clear()

    kc = wm.keyconfigs.addon
    # Remove any leftover items from a previous registration before adding new ones
    _remove_existing_split_items(kc)

    for km_name, space_type, region_type in _KEYMAP_TARGETS:
        km = kc.keymaps.new(name=km_name, space_type=space_type, region_type=region_type)

        for group_a, group_b in constants.VERTEX_GROUP_PAIRS:
            # Register with no key binding ('NONE'). Blender persists user
            # customisations as diffs against this addon baseline in userpref.blend,
            # so the user's chosen key is automatically re-applied on every
            # register — including after addon updates — as long as the idname
            # and properties match.
            kmi = km.keymap_items.new("pawlygon.split_shapekey", 'NONE', 'PRESS')
            kmi.properties.group_a = group_a
            kmi.properties.group_b = group_b

            # Store (km, kmi) pairs — the conventional Blender pattern for clean unregister
            _addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in _addon_keymaps:
        km.keymap_items.remove(kmi)

    _addon_keymaps.clear()


def draw_keymaps(layout, context):
    wm = context.window_manager
    if not wm or not wm.keyconfigs or not wm.keyconfigs.user:
        layout.label(text="Keyconfig unavailable", icon='INFO')
        return

    user_kc = wm.keyconfigs.user

    try:
        import rna_keymap_ui
    except ImportError:
        layout.label(text="Keymap UI unavailable", icon='ERROR')
        return

    box = layout.box()
    box.label(text="Split Shapekey Hotkeys", icon='KEYINGSET')

    for km, kmi in _addon_keymaps:
        # Find the corresponding item in the user keyconfig for display
        user_km = _find_keymap(user_kc, km.name, km.space_type, km.region_type)
        if not user_km:
            continue

        group_a = getattr(kmi.properties, "group_a", "")
        group_b = getattr(kmi.properties, "group_b", "")

        found_item = None
        for user_kmi in user_km.keymap_items:
            if _is_matching_split_item(user_kmi, group_a, group_b):
                found_item = user_kmi
                break

        row = box.row()
        row.label(text=f"Split {group_a}/{group_b}")

        if found_item:
            rna_keymap_ui.draw_kmi([], user_kc, user_km, found_item, box, 0)
        else:
            row = box.row()
            row.label(text="Keymap item not found", icon='ERROR')
