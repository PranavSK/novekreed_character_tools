import bpy

from bpy.types import Operator
from ..utils import (
    push_to_nla_stash,
    validate_target_armature,
    TPOSE_ACTION_NAME
)


class NCT_OT_animation_play(Operator):
    bl_idname = "nct.animation_play"
    bl_label = "Play Animation"
    bl_description = "Play selected armature animation."

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        target_armature = tool.target_object
        bpy.ops.screen.animation_cancel()
        context.view_layer.objects.active = target_armature
        context.scene.frame_start = 1
        if target_armature.animation_data.action:
            bpy.ops.screen.animation_play()
            self.report({'INFO'}, 'Playing Animation')
            return {'FINISHED'}

        return {'CANCELLED'}


class NCT_OT_animation_stop(Operator):
    bl_idname = "nct.animation_stop"
    bl_label = "Stop Animation"
    bl_description = "Stops current animation"

    def execute(self, context):
        context.scene.frame_current = 0
        bpy.ops.screen.animation_cancel(0)
        self.report({'INFO'}, 'Animation Stopped')
        return {'FINISHED'}


class NCT_OT_trim_animation(Operator):
    bl_idname = "nct.trim_animation"
    bl_label = "Trim Animation"
    bl_description = "Trim Selected Animation Into A New One"

    def trim_animation(self, target_armature, from_frame, to_frame):
        target_action = target_armature.animation_data.action
        for group in target_action.groups:
            if not group.select:
                continue
            for channel in group.channels:
                if not channel.select:
                    continue
                keyframePoints = channel.keyframe_points
                for i in range(0, len(keyframePoints)):
                    frame = keyframePoints[i].co[0]
                    if not (from_frame <= frame <= to_frame):
                        target_armature.keyframe_delete(
                            channel.data_path,
                            frame=frame,
                            index=channel.array_index
                        )

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        target_armature = tool.target_object
        new_name = tool.trim_animation_name
        if not new_name:
            self.report(
                {'ERROR'},
                "Invalid name for new animation."
            )
            return {'CANCELLED'}

        from_frame = tool.trim_animation_from
        to_frame = tool.trim_animation_to
        select_action = target_armature.animation_data.action
        if not (
            0 <= tool.selected_action_index < len(bpy.data.actions) and
            select_action
        ):
            self.report(
                {'ERROR'},
                "No selected action on armature."
            )
            return {'CANCELLED'}

        if select_action != bpy.data.actions[tool.selected_action_index]:
            self.report(
                {'INFO'},
                "Active action on armature is not selected action in tool." +
                "Continuing but result may be undesirable."
            )
            target_armature.animation_data.action = \
                bpy.data.actions[tool.selected_action_index]

        anim_frames = int(select_action.frame_range[1])
        if target_armature is None:
            self.report(
                {'ERROR'},
                "Imported character is not valid. Not armature found"
            )
            return {'CANCELLED'}

        if not (from_frame < to_frame < anim_frames):
            self.report({'ERROR'}, 'Choose Valid Animation Frames')
            return {'CANCELLED'}

        action_copy = target_armature.animation_data.action.copy()
        action_copy.name = new_name
        target_armature.animation_data.action = action_copy
        action_copy['is_nct_processed'] = True
        push_to_nla_stash(armature=target_armature, action=action_copy)
        tool.selected_action_index = bpy.data.actions.find(new_name)
        # Trim Animation Frames Choosen By User
        self.trim_animation(target_armature, from_frame, to_frame)

        context.scene.frame_start = from_frame
        context.scene.frame_end = to_frame

        self.report({'INFO'}, 'New Animation Added')

        return {'FINISHED'}


class NCT_OT_animation_delete(Operator):
    bl_idname = "nct.animation_delete"
    bl_label = "Delete Current Animation"
    bl_description = "Deletes Current Selected Animation"

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        target_armature = tool.target_object
        select_action = target_armature.animation_data.action
        if not (
            0 <= tool.selected_action_index < len(bpy.data.actions) and
            select_action
        ):
            self.report(
                {'ERROR'},
                "No selected action on armature."
            )
            return {'CANCELLED'}

        if select_action != bpy.data.actions[tool.selected_action_index]:
            self.report(
                {'INFO'},
                "Active action on armature is not selected action in tool." +
                "Action not deleted."
            )
            return {'CANCELLED'}

        if select_action.name == TPOSE_ACTION_NAME:
            self.report(
                {'INFO'},
                "Deleting the T-Pose action can cause issues."
            )

        bpy.data.actions.remove(select_action)
        # Reset active action to TPose
        tool.selected_action_index = bpy.data.actions.find(TPOSE_ACTION_NAME)
        target_armature.animation_data.action = \
            bpy.data.actions[TPOSE_ACTION_NAME]

        self.report({'INFO'}, 'Animation Deleted')

        return {'FINISHED'}
