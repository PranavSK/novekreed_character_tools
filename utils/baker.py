import bpy
from math import pi
from mathutils import Quaternion


ROOT_BAKER_NAME = 'NCT_root_baker'
BONE_BAKER_NAME = 'NCT_{bone_name}_baker'


def get_all_quaternion_curves(object):
    """
    Returns all quaternion fcurves of object/bones packed together in a touple
    per object/bone
    """
    fcurves = object.animation_data.action.fcurves
    if fcurves.find('rotation_quaternion'):
        yield (
            fcurves.find('rotation_quaternion', index=0),
            fcurves.find('rotation_quaternion', index=1),
            fcurves.find('rotation_quaternion', index=2),
            fcurves.find('rotation_quaternion', index=3)
        )

    if object.type != 'ARMATURE':
        return
    for bone in object.pose.bones:
        data_path = 'pose.bones["' + bone.name + '"].rotation_quaternion'
        if not fcurves.find(data_path):
            continue

        yield (
            fcurves.find(data_path, index=0),
            fcurves.find(data_path, index=1),
            fcurves.find(data_path, index=2),
            fcurves.find(data_path, index=3)
        )


def quaternion_cleanup(object, prevent_flips=True, prevent_inverts=True):
    """fixes signs in quaternion fcurves swapping from one frame to another"""
    for curves in get_all_quaternion_curves(object):
        start = int(min((curves[i].keyframe_points[0].co.x for i in range(4))))
        end = int(max((curves[i].keyframe_points[-1].co.x for i in range(4))))
        for curve in curves:
            for i in range(start, end):
                curve.keyframe_points.insert(
                    i, curve.evaluate(i)).interpolation = 'LINEAR'
        zipped = list(zip(
            curves[0].keyframe_points,
            curves[1].keyframe_points,
            curves[2].keyframe_points,
            curves[3].keyframe_points))
        for i in range(1, len(zipped)):
            if prevent_flips:
                rot_prev = Quaternion((zipped[i-1][j].co.y for j in range(4)))
                rot_cur = Quaternion((zipped[i][j].co.y for j in range(4)))
                diff = rot_prev.rotation_difference(rot_cur)
                if abs(diff.angle - pi) < 0.5:
                    rot_cur.rotate(Quaternion(diff.axis, pi))
                    for j in range(4):
                        zipped[i][j].co.y = rot_cur[j]
            if prevent_inverts:
                change_amount = 0.0
                for j in range(4):
                    change_amount += abs(zipped[i-1]
                                         [j].co.y - zipped[i][j].co.y)
                if change_amount > 1.0:
                    for j in range(4):
                        zipped[i][j].co.y *= -1.0


def extract_loc_rot_from_obj(
    object,
    action,
    start_frame,
    end_frame,
    baker_name
):
    # Set the scene for curr actions
    object.animation_data.action = action

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(
        type='ARROWS', radius=1, align='WORLD', location=(0, 0, 0)
    )

    baker = bpy.context.object
    baker.name = baker_name
    baker.rotation_mode = 'QUATERNION'

    bpy.ops.object.constraint_add(type='COPY_LOCATION')
    baker.constraints["Copy Location"].target = object

    bpy.ops.object.constraint_add(type='COPY_ROTATION')
    baker.constraints["Copy Rotation"].target = object

    bpy.ops.nla.bake(
        frame_start=start_frame,
        frame_end=end_frame,
        step=1,
        only_selected=True,
        visual_keying=True,
        clear_constraints=True,
        clear_parents=False,
        use_current_action=False,
        bake_types={'OBJECT'}
    )

    quaternion_cleanup(baker)
    return baker


def extract_loc_rot_from_bone(
    armature,
    action,
    bone_name,
    start_frame,
    end_frame,
    baker_name
):
    # Set the scene for curr actions
    armature.animation_data.action = action

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(
        type='ARROWS', radius=1, align='WORLD', location=(0, 0, 0)
    )
    baker = bpy.context.object
    baker.name = baker_name
    baker.rotation_mode = 'QUATERNION'

    bpy.ops.object.constraint_add(type='COPY_LOCATION')
    baker.constraints["Copy Location"].target = armature
    baker.constraints["Copy Location"].subtarget = bone_name

    bpy.ops.object.constraint_add(type='COPY_ROTATION')
    baker.constraints["Copy Rotation"].target = armature
    baker.constraints["Copy Rotation"].subtarget = bone_name

    bpy.ops.nla.bake(
        frame_start=start_frame,
        frame_end=end_frame,
        step=1,
        only_selected=True,
        visual_keying=True,
        clear_constraints=True,
        clear_parents=False,
        use_current_action=False,
        bake_types={'OBJECT'}
    )

    quaternion_cleanup(baker)
    return baker


def extract_constrained_from_bone(
    armature,
    action,
    bone_name,
    use_x,
    use_y,
    use_z,
    on_ground,
    use_rot,
    start_frame,
    end_frame,
    baker_name
):
    pose_bone = armature.pose.bones[bone_name]
    # Set the scene for curr actions
    armature.animation_data.action = action

    hip_world_loc = armature.matrix_local @ pose_bone.bone.head_local
    z_offset = hip_world_loc.z

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(
        type='ARROWS', radius=1, align='WORLD', location=(0, 0, 0)
    )
    baker = bpy.context.object
    baker.name = baker_name
    baker.rotation_mode = 'QUATERNION'

    if use_z:
        bpy.ops.object.constraint_add(type='COPY_LOCATION')
        baker.constraints["Copy Location"].name = "Copy Location Z"
        baker.constraints["Copy Location Z"].target = armature
        baker.constraints["Copy Location Z"].subtarget = bone_name
        baker.constraints["Copy Location Z"].use_x = False
        baker.constraints["Copy Location Z"].use_y = False
        baker.constraints["Copy Location Z"].use_z = True
        baker.constraints["Copy Location Z"].use_offset = True

        baker.location.z = -z_offset
        if on_ground:
            bpy.ops.object.constraint_add(type='LIMIT_LOCATION')
            baker.constraints["Limit Location"].use_min_z = True

    bpy.ops.object.constraint_add(type='COPY_LOCATION')
    baker.constraints["Copy Location"].target = armature
    baker.constraints["Copy Location"].subtarget = bone_name
    baker.constraints["Copy Location"].use_x = use_x
    baker.constraints["Copy Location"].use_y = use_y
    baker.constraints["Copy Location"].use_z = False

    bpy.ops.object.constraint_add(type='COPY_ROTATION')
    baker.constraints["Copy Rotation"].target = armature
    baker.constraints["Copy Rotation"].subtarget = bone_name
    baker.constraints["Copy Rotation"].use_y = False
    baker.constraints["Copy Rotation"].use_x = False
    baker.constraints["Copy Rotation"].use_z = use_rot

    bpy.ops.nla.bake(
        frame_start=start_frame,
        frame_end=end_frame,
        step=1,
        only_selected=True,
        visual_keying=True,
        clear_constraints=True,
        clear_parents=False,
        use_current_action=False,
        bake_types={'OBJECT'}
    )

    quaternion_cleanup(baker)
    return baker


def apply_baker_to_bone(
    baker,
    armature,
    action,
    target_bone_name,
    use_rot_offset,
    start_frame,
    end_frame
):
    # Set the scene for curr actions
    armature.animation_data.action = action
    pose_bone = armature.pose.bones[target_bone_name]

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature

    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')
    pose_bone.bone.select = True
    armature.data.bones.active = pose_bone.bone
    bpy.ops.pose.constraint_add(type='COPY_LOCATION')
    pose_bone.constraints["Copy Location"].target = baker
    bpy.ops.pose.constraint_add(type='COPY_ROTATION')
    pose_bone.constraints["Copy Rotation"].target = baker
    pose_bone.constraints["Copy Rotation"].use_offset = use_rot_offset

    bpy.ops.nla.bake(
        frame_start=start_frame,
        frame_end=end_frame,
        step=1,
        only_selected=True,
        visual_keying=True,
        clear_constraints=True,
        clear_parents=False,
        use_current_action=True,
        bake_types={'POSE'}
    )
