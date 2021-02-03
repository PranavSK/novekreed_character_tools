import bpy

from bpy.types import Operator

from ..utils import validate_target_armature


class NCT_OT_add_rootbone(Operator):
    bl_idname = "nct.add_rootbone"
    bl_label = "Add Root Bone"
    bl_description = "Adds armature root bone for root motion"

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        target_armature = tool.target_object
        rootmotion_bone_name = tool.rootmotion_name
        start_frame = tool.rootmotion_start_frame
        rootmotion_bone_offset = 1
        hips = tool.rootmotion_hip_bone

        # Bones
        if not hips:
            self.report(
                {'ERROR'},
                "No valid hip bone selected.")
            return {'CANCELLED'}

        # Validates Required Bone Exists In Armature
        if len(target_armature.data.bones) > 0:
            current_mode = context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            context.view_layer.objects.active = target_armature
            editbones = target_armature.data.edit_bones
            if rootmotion_bone_name in editbones:
                self.report({'INFO'}, 'Root Bone Exists.')
                return {'FINISHED'}

            hips_bone = editbones[hips]
            # Bone Setup
            rootmotion_bone = editbones.new(rootmotion_bone_name)
            rootmotion_bone.tail = hips_bone.tail
            rootmotion_bone.head = hips_bone.head
            rootmotion_bone.head.y -= rootmotion_bone_offset
            rootmotion_bone.tail.y -= rootmotion_bone_offset

            editbones[hips].parent = rootmotion_bone

            bpy.ops.object.mode_set(mode="POSE")
            bpy.ops.pose.select_all(action='DESELECT')
            target_armature.data.bones[rootmotion_bone_name].select = True
            scene.frame_set(start_frame)
            bpy.ops.anim.keyframe_insert_menu(type='Location')
            bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Bone Added')

        return {'FINISHED'}


class NCT_OT_add_rootmotion(Operator):
    bl_idname = "nct.add_rootmotion"
    bl_label = "Add Root Motion"
    bl_description = "Adds Root Motion Bone To Animations"

    def bake_rootmotion(self, action, scene):
        tool = scene.novkreed_character_tools
        target_armature = tool.target_object
        start_frame = tool.rootmotion_start_frame
        end_frame = int(target_armature.animation_data.action.frame_range[1])
        target_armature.animation_data.action = action
        scene.frame_end = end_frame

        hips = tool.rootmotion_hip_bone
        bone_name = tool.rootmotion_name
        is_bone_exists = bone_name in target_armature.pose.bones.keys()
        if not is_bone_exists:
            bpy.ops.nct.add_rootbone()

        hip_bone = target_armature.pose.bones[hips]
        root_bone = target_armature.pose.bones[bone_name]

        for index in range(start_frame, end_frame + 1):
            scene.frame_set(index)
            for axis in range(3):
                if tool.rootmotion_use_translation[axis]:
                    if (
                        tool.rootmotion_on_ground and
                        tool.rootmotion_use_translation[2] and
                        axis == 2 and
                        hip_bone.location[axis] < 0
                    ):
                        root_bone.location[axis] = 0
                    else:
                        root_bone.location[axis] = hip_bone.location[axis]
                    hip_bone.location[axis] = 0
                else:
                    root_bone.location[axis] = 0

            root_bone.keyframe_insert(data_path='location')
            hip_bone.keyframe_insert(data_path='location')
            # rotation_quaternion

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        is_rootmotion_all = tool.is_rootmotion_all

        current_mode = context.object.mode
        bpy.ops.object.mode_set(mode="POSE")
        if is_rootmotion_all:
            for action in bpy.data.actions:
                if action.get('is_nct_processed'):
                    self.bake_rootmotion(action, scene)
        else:
            idx = tool.selected_action_index
            action = bpy.data.actions[idx]
            if action.get('is_nct_processed'):
                self.bake_rootmotion(action, scene)

        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Motion Updated')
        return {'FINISHED'}
