import bpy


def split_shapekey_by_groups(obj: 'bpy.types.Object', group_a_name: str, group_b_name: str):
    """
    Split a shapekey into two separate shapekeys based on vertex groups.
    
    Creates two new shapekeys from the active shapekey, each applying only
    to vertices in the specified vertex group. Useful for splitting symmetric
    shapekeys (e.g., splitting a combined shapekey into Left/Right versions).
    
    Args:
        obj: Blender mesh object with shapekeys
        group_a_name: Name of first vertex group
        group_b_name: Name of second vertex group
    
    Returns:
        Tuple of (new_name_a, new_name_b) or None if split failed
    """
    if not obj or not obj.data.shape_keys:
        return None

    shape_key = obj.active_shape_key
    if not shape_key:
        return None

    group_a = obj.vertex_groups.get(group_a_name)
    group_b = obj.vertex_groups.get(group_b_name)

    # Both vertex groups must exist for the split to work
    if not group_a or not group_b:
        return None

    # Store original position to maintain ordering of new shapekeys
    original_name = shape_key.name
    original_index = obj.active_shape_key_index
    key_count = len(obj.data.shape_keys.key_blocks)
    move_steps = key_count - original_index - 1

    created_names = []

    # Create two new shapekeys, one for each vertex group
    for group_name, suffix in [(group_a_name, group_a_name), (group_b_name, group_b_name)]:
        # Clear any existing mix to start fresh
        bpy.ops.object.shape_key_clear()

        # Select original shapekey and apply vertex group mask
        obj.active_shape_key_index = obj.data.shape_keys.key_blocks.find(original_name)
        # Re-resolve reference each iteration to avoid stale pointer after shape_key_add
        shape_key = obj.data.shape_keys.key_blocks[original_name]
        shape_key.vertex_group = group_name
        shape_key.value = 1.0

        # Create new shapekey from the mix (applies only to masked vertices)
        bpy.ops.object.shape_key_add(from_mix=True)
        new_name = original_name + suffix
        obj.active_shape_key.name = new_name
        created_names.append(new_name)

        # Move new shapekey to maintain original position in list
        for _ in range(move_steps):
            result = bpy.ops.object.shape_key_move(type='UP')
            if 'FINISHED' not in result:
                break

    # Reset shapekey state (clear vertex group assignment)
    bpy.ops.object.shape_key_clear()
    current_index = obj.data.shape_keys.key_blocks.find(original_name)
    obj.active_shape_key_index = current_index
    # Re-resolve reference after all additions to get the current data block
    shape_key = obj.data.shape_keys.key_blocks[original_name]
    shape_key.vertex_group = ''
    
    # Move original shapekey back to its original position if it shifted
    if current_index != original_index:
        if current_index < original_index:
            steps = original_index - current_index
            for _ in range(steps):
                result = bpy.ops.object.shape_key_move(type='DOWN')
                if 'FINISHED' not in result:
                    break
        else:
            steps = current_index - original_index
            for _ in range(steps):
                result = bpy.ops.object.shape_key_move(type='UP')
                if 'FINISHED' not in result:
                    break
    
    obj.active_shape_key_index = original_index

    return (created_names[0], created_names[1])


def get_missing_shapekeys(obj: 'bpy.types.Object', expected_names: list):
    """
    Compare object's existing shapekeys against expected names.
    
    Args:
        obj: Blender mesh object
        expected_names: List of shapekey names to check for
    
    Returns:
        List of missing shapekey names
    """
    if not obj or not obj.data.shape_keys:
        # If no shapekeys exist, all expected names are missing
        return list(expected_names)

    existing = {kb.name for kb in obj.data.shape_keys.key_blocks}
    return [name for name in expected_names if name not in existing]


def move_old_shapekeys_to_bottom(obj: 'bpy.types.Object'):
    """
    Move all shapekeys ending with '.old' suffix to the bottom of the list.
    
    Useful for organizing shapekeys after operations that create backup copies
    with .old suffix (e.g., shapekey transfers or modifications).
    
    Args:
        obj: Blender mesh object with shapekeys
    
    Returns:
        Number of shapekeys moved, or None if no shapekeys exist
    """
    if not obj or not obj.data.shape_keys:
        return None

    key_blocks = obj.data.shape_keys.key_blocks
    moved = 0

    old_names = [kb.name for kb in key_blocks if kb.name.endswith('.old') and kb.name != key_blocks[0].name]

    for name in old_names:
        kb = key_blocks.get(name)
        if not kb:
            continue
        
        obj.active_shape_key_index = list(key_blocks).index(kb)
        last_idx = len(key_blocks) - 1
        
        while obj.active_shape_key_index < last_idx:
            prev_idx = obj.active_shape_key_index
            result = bpy.ops.object.shape_key_move(type='DOWN')
            if 'FINISHED' not in result or obj.active_shape_key_index == prev_idx:
                break
        moved += 1

    return moved


def delete_old_shapekeys(obj: 'bpy.types.Object'):
    """
    Delete all shapekeys ending with '.old' suffix.
    
    Useful for cleanup after shapekey operations that create backup copies.
    
    Args:
        obj: Blender mesh object with shapekeys
    
    Returns:
        Number of shapekeys deleted, or None if no shapekeys exist
    """
    if not obj or not obj.data.shape_keys:
        return None

    key_blocks = obj.data.shape_keys.key_blocks
    deleted = 0

    old_names = [kb.name for kb in key_blocks if kb.name.endswith('.old')]

    for name in reversed(old_names):
        kb = key_blocks.get(name)
        if kb:
            obj.shape_key_remove(kb)
            deleted += 1

    return deleted
