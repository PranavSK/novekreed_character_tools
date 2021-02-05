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
            tool.target_object = None
            tool.selected_action_index = None
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
