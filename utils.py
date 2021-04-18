import bpy

TPOSE_ACTION_NAME = "T-Pose"
MIXAMO_GROUP_NAME = "Mixamo"


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


def push_to_nla_stash(armature, action=None):
    """
    Push the given action to the nla stash on armature.
    If no action is given the current action on armature is pushed.
    """
    if action is None:
        action = armature.animation_data.action

    track = armature.animation_data.nla_tracks.new()
    track.name = action.name
    track.strips.new(
        action.name,
        action.frame_range[0],
        action
    )
    track.mute = True
    armature.animation_data.action = None




def rename_bones(armature, remove_namespace_only=False):
    """function for renaming the armature bones to a target skeleton"""
    for bone in armature.pose.bones:
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
    i = re.search(r"[:_]", full_name[::-1])
    if i:
        return full_name[-(i.start())::]
    else:
        return full_name


def get_mapped_bone_name(in_name):
    schema = {
        'unreal': {
            'root': 'root',
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
    }
    new_name = schema['unreal'].get(in_name)
    if new_name:
        return new_name
    else:
        return in_name