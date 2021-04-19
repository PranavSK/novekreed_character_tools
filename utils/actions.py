TPOSE_ACTION_NAME = "_tpose"


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


def trim_animation(armature, action, from_frame, to_frame):
    armature.animation_data.action = action
    for fcurve in action.fcurves:
        keyframePoints = fcurve.keyframe_points
        for i in range(0, len(keyframePoints)):
            frame = keyframePoints[i].co[0]
            if not (from_frame <= frame <= to_frame):
                armature.keyframe_delete(
                    fcurve.data_path,
                    frame=frame,
                    index=fcurve.array_index
                )
        # Shift the remaining frames
        offset = fcurve.keyframe_points[0].co[0]
        for point in fcurve.keyframe_points:
            point.co[0] = point.co[0] - offset
            point.handle_left[0] = point.handle_left[0] - offset
            point.handle_right[0] = point.handle_right[0] - offset
