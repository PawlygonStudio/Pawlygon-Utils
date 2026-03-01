import bpy

from . import constants


# Keep references to addon keymap items for clean unregister
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


def _find_user_split_binding(window_manager, group_a, group_b):
    user_kc = window_manager.keyconfigs.user if window_manager and window_manager.keyconfigs else None
    if not user_kc:
        return None

    for km in user_kc.keymaps:
        for kmi in km.keymap_items:
            if not _is_matching_split_item(kmi, group_a, group_b):
                continue
            if kmi.type == 'NONE':
                continue
            return kmi

    return None


def _copy_event_settings(src_kmi, dst_kmi):
    dst_kmi.map_type = src_kmi.map_type
    dst_kmi.type = src_kmi.type
    dst_kmi.value = src_kmi.value
    dst_kmi.shift = src_kmi.shift
    dst_kmi.ctrl = src_kmi.ctrl
    dst_kmi.alt = src_kmi.alt
    dst_kmi.oskey = src_kmi.oskey
    dst_kmi.any = src_kmi.any
    dst_kmi.key_modifier = src_kmi.key_modifier


def register():
    wm = bpy.context.window_manager
    if not wm or not wm.keyconfigs or not wm.keyconfigs.addon:
        return

    _addon_keymaps.clear()

    kc = wm.keyconfigs.addon
    _remove_existing_split_items(kc)

    for km_name, space_type, region_type in _KEYMAP_TARGETS:
        km = kc.keymaps.new(name=km_name, space_type=space_type, region_type=region_type)

        for group_a, group_b in constants.VERTEX_GROUP_PAIRS:
            existing = None
            for kmi in km.keymap_items:
                if _is_matching_split_item(kmi, group_a, group_b):
                    existing = kmi
                    break

            if existing is None:
                kmi = km.keymap_items.new("pawlygon.split_shapekey", 'NONE', 'PRESS')
                kmi.properties.group_a = group_a
                kmi.properties.group_b = group_b

                user_binding = _find_user_split_binding(wm, group_a, group_b)
                if user_binding:
                    _copy_event_settings(user_binding, kmi)

            _addon_keymaps.append((km_name, space_type, region_type, group_a, group_b))


def unregister():
    wm = bpy.context.window_manager
    if not wm or not wm.keyconfigs or not wm.keyconfigs.addon:
        _addon_keymaps.clear()
        return

    kc = wm.keyconfigs.addon
    for km_name, space_type, region_type, group_a, group_b in _addon_keymaps:
        km = _find_keymap(kc, km_name, space_type, region_type)
        if not km:
            continue

        for kmi in list(km.keymap_items):
            if _is_matching_split_item(kmi, group_a, group_b):
                km.keymap_items.remove(kmi)
                break

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

    for km_name, space_type, region_type, group_a, group_b in _addon_keymaps:
        km = _find_keymap(user_kc, km_name, space_type, region_type)
        if not km:
            continue

        found_item = None
        for kmi in km.keymap_items:
            if _is_matching_split_item(kmi, group_a, group_b):
                found_item = kmi
                break

        row = box.row()
        row.label(text=f"Split {group_a}/{group_b}")

        if found_item:
            rna_keymap_ui.draw_kmi([], user_kc, km, found_item, box, 0)
        else:
            row = box.row()
            row.label(text="Keymap item not found", icon='ERROR')
