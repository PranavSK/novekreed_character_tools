import bpy
import re

from .baker import (
    BONE_BAKER_NAME,
    ROOT_BAKER_NAME,
    apply_baker_to_bone,
    extract_loc_rot_from_bone,
    extract_loc_rot_from_obj
)


bone_map = {
    'Hips': 'pelvis',
    'Spine': 'spine_01',
    'Spine1': 'spine_02',
    'Spine2': 'spine_03',
    'LeftShoulder': 'clavicle_l',
    'LeftArm': 'upperarm_l',
    'LeftForeArm': 'lowerarm_l',
    'LeftHand': 'hand_l',
    'RightShoulder': 'clavicle_r',
    'RightArm': 'upperarm_r',
    'RightForeArm': 'lowerarm_r',
    'RightHand': 'hand_r',
    'Neck1': 'neck_01',
    'Neck': 'neck_01',
    'Head': 'head',
    'LeftUpLeg': 'thigh_l',
    'LeftLeg': 'calf_l',
    'LeftFoot': 'foot_l',
    'RightUpLeg': 'thigh_r',
    'RightLeg': 'calf_r',
    'RightFoot': 'foot_r',
    'LeftHandIndex1': 'index_01_l',
    'LeftHandIndex2': 'index_02_l',
    'LeftHandIndex3': 'index_03_l',
    'LeftHandMiddle1': 'middle_01_l',
    'LeftHandMiddle2': 'middle_02_l',
    'LeftHandMiddle3': 'middle_03_l',
    'LeftHandPinky1': 'pinky_01_l',
    'LeftHandPinky2': 'pinky_02_l',
    'LeftHandPinky3': 'pinky_03_l',
    'LeftHandRing1': 'ring_01_l',
    'LeftHandRing2': 'ring_02_l',
    'LeftHandRing3': 'ring_03_l',
    'LeftHandThumb1': 'thumb_01_l',
    'LeftHandThumb2': 'thumb_02_l',
    'LeftHandThumb3': 'thumb_03_l',
    'RightHandIndex1': 'index_01_r',
    'RightHandIndex2': 'index_02_r',
    'RightHandIndex3': 'index_03_r',
    'RightHandMiddle1': 'middle_01_r',
    'RightHandMiddle2': 'middle_02_r',
    'RightHandMiddle3': 'middle_03_r',
    'RightHandPinky1': 'pinky_01_r',
    'RightHandPinky2': 'pinky_02_r',
    'RightHandPinky3': 'pinky_03_r',
    'RightHandRing1': 'ring_01_r',
    'RightHandRing2': 'ring_02_r',
    'RightHandRing3': 'ring_03_r',
    'RightHandThumb1': 'thumb_01_r',
    'RightHandThumb2': 'thumb_02_r',
    'RightHandThumb3': 'thumb_03_r',
    'LeftToeBase': 'ball_l',
    'RightToeBase': 'ball_r'
}
bone_map_inverse = dict([reversed(i) for i in bone_map.items()])


def get_hip_bone_name(armature):
    hipname = ""
    for hipname in (
        "hips"
        "Hips",
        "mixamorig:Hips",
        "mixamorig_Hips",
        "pelvis",
        "Pelvis"
    ):
        hips = armature.data.bones.get(hipname)
        if hips != None:
            break

    return hipname


def rename_bones(armature, remove_namespace_only=False):
    """function for renaming the armature bones to a target skeleton"""
    for bone in armature.data.bones:
        old_name = bone.name
        new_name = remove_namespace(bone.name)
        if not remove_namespace_only:
            new_name = get_mapped_bone_name(new_name)

        bone.name = new_name

        for mesh in armature.children:
            for vertex_group in mesh.vertex_groups:
                if vertex_group.name == old_name:
                    vertex_group.name = new_name


def remove_namespace(full_name):
    if full_name in bone_map or full_name in bone_map_inverse:
        return full_name
    i = re.search(r"[:_]", full_name[::-1])
    if i:
        return full_name[-(i.start())::]
    else:
        return full_name


def get_mapped_bone_name(in_name):
    new_name = bone_map.get(in_name)
    if new_name:
        return new_name
    else:
        return in_name


def validate_target_armature(scene) -> bool:
    """Validate if the target saved is existing."""
    # clear all anims
    tool = scene.novkreed_character_tools
    obj = tool.target_object

    valid = True

    if obj is None:
        valid = False
    else:
        if obj.name not in scene.objects:
            bpy.data.objects.remove(obj)
            valid = False

    return valid


def prepare_tpose_rig(context, armature):
    rename_bones(armature)
    current_mode = context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    armature.select_set(True)
    context.view_layer.objects.active = armature
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Remove fcurves on armature
    fcurves = armature.animation_data.action.fcurves
    for fcurve in fcurves:
        if fcurve.data_path in ('location', 'rotation_quaternion', 'scale'):
            fcurves.remove(fcurve)

    # Reset the bone tpose to 0.
    for bone in armature.data.bones:
        data_path = (
            'pose.bones[\"{}\"].location'.format(bone.name)
        )
        for axis in range(3):
            fcurve = armature.animation_data.action.fcurves\
                .find(data_path=data_path, index=axis)
            if fcurve == None:
                continue
            for ind in range(len(fcurve.keyframe_points)):
                # Set the pose position of the bone to 0
                fcurve.keyframe_points[ind].co[1] = 0.0

    bpy.ops.object.mode_set(mode=current_mode)


def prepare_anim_rig(context, armature):
    rename_bones(armature)
    bpy.ops.object.mode_set(mode='OBJECT')
    action = armature.animation_data.action
    start_frame = int(action.frame_range[0])
    end_frame = int(action.frame_range[1])
    hipname = get_hip_bone_name(armature)

    has_root_anim = False
    fcurves = action.fcurves
    for fcurve in fcurves:
        if fcurve.data_path in ('location', 'rotation_quaternion', 'scale'):
            has_root_anim = True
            break

    root_baker = None
    if has_root_anim:
        root_baker = extract_loc_rot_from_obj(
            object=armature,
            action=action,
            start_frame=start_frame,
            end_frame=end_frame,
            baker_name=ROOT_BAKER_NAME
        )
        for fcurve in fcurves:
            if fcurve.data_path in ('location', 'rotation_quaternion', 'scale'):
                fcurves.remove(fcurve)

    scale_baker = extract_loc_rot_from_bone(
        armature=armature,
        action=action,
        bone_name=hipname,
        start_frame=start_frame,
        end_frame=end_frame,
        baker_name=BONE_BAKER_NAME.format(bone_name="scale")
    )

    # Apply transformations on selected Armature
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    context.view_layer.objects.active = armature
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    target_bone_name = hipname
    if armature.data.bones[hipname].parent:
        target_bone_name = armature.data.bones[hipname].parent

    apply_baker_to_bone(
        baker=scale_baker,
        armature=armature,
        action=action,
        target_bone_name=target_bone_name,
        use_rot_offset=False,
        start_frame=start_frame,
        end_frame=end_frame
    )

    if has_root_anim:
        bpy.ops.nct.add_rootbone()
        tool = context.scene.novkreed_character_tools
        target_armature = tool.target_object
        target_armature.animation_data.action = action
        apply_baker_to_bone(
            baker=root_baker,
            armature=target_armature,
            action=action,
            target_bone_name=target_bone_name,
            use_rot_offset=True,
            start_frame=start_frame,
            end_frame=end_frame
        )

        action['has_root_motion'] = True

    # Delete helpers
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    scale_baker.select_set(True)
    if root_baker:
        root_baker.select_set(True)
        bpy.data.actions.remove(root_baker.animation_data.action)
    bpy.data.actions.remove(scale_baker.animation_data.action)
    bpy.ops.object.delete(use_global=False)
