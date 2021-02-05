import bpy
import mathutils

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
        rootmotion_root_name = tool.rootmotion_name
        start_frame = tool.rootmotion_start_frame
        rootmotion_bone_offset = 1
        hips_name = tool.rootmotion_hip_bone

        # Bones
        if not hips_name:
            self.report(
                {'ERROR'},
                "No valid hip bone selected.")
            return {'CANCELLED'}

        # Validates Required Bone Exists In Armature
        if len(target_armature.data.bones) > 0:
            context.view_layer.objects.active = target_armature
            current_mode = context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            context.view_layer.objects.active = target_armature
            editbones = target_armature.data.edit_bones
            if rootmotion_root_name in editbones:
                self.report({'INFO'}, 'Root Bone Exists.')
                return {'FINISHED'}

            hips_bone = editbones[hips_name]
            # Bone Setup
            rootmotion_bone = editbones.new(rootmotion_root_name)
            rootmotion_bone.head = hips_bone.head
            rootmotion_bone.head.y -= rootmotion_bone_offset
            rootmotion_bone.head_radius = hips_bone.head_radius
            rootmotion_bone.tail = hips_bone.tail
            rootmotion_bone.tail.y -= rootmotion_bone_offset
            rootmotion_bone.tail_radius = hips_bone.tail_radius

            editbones[hips_name].parent = rootmotion_bone

            bpy.ops.object.mode_set(mode="POSE")
            bpy.ops.pose.select_all(action='DESELECT')
            target_armature.data.bones[rootmotion_root_name].select = True
            scene.frame_set(start_frame)
            bpy.ops.anim.keyframe_insert_menu(type='Location')
            bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Bone Added')

        return {'FINISHED'}


class NCT_OT_add_rootmotion(Operator):
    bl_idname = "nct.add_rootmotion"
    bl_label = "Add Root Motion"
    bl_description = "Adds Root Motion Bone To Animations"

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        is_rootmotion_all = tool.is_rootmotion_all
        tool = scene.novkreed_character_tools
        target_armature = tool.target_object

        context.view_layer.objects.active = target_armature
        current_mode = context.object.mode

        root_name = tool.rootmotion_name
        is_bone_exists = root_name in target_armature.pose.bones.keys()
        if not is_bone_exists:
            bpy.ops.nct.add_rootbone()

        bpy.ops.object.mode_set(mode='POSE')
        frame_curr = scene.frame_current

        if is_rootmotion_all:
            for action in bpy.data.actions:
                if action.get('is_nct_processed'):
                    self.bake_rootmotion(
                        scene,
                        tool,
                        target_armature,
                        action
                    )
        else:
            idx = tool.selected_action_index
            action = bpy.data.actions[idx]
            if action.get('is_nct_processed'):
                self.bake_rootmotion(
                    scene,
                    tool,
                    target_armature,
                    action
                )

        scene.frame_set(frame_curr)
        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Motion Updated')
        return {'FINISHED'}

    def bake_rootmotion(
        self,
        scene,
        tool,
        target_armature,
        action
    ):
        hips_name = tool.rootmotion_hip_bone
        root_name = tool.rootmotion_name
        hip_bone = target_armature.pose.bones[hips_name]
        root_bone = target_armature.pose.bones[root_name]

        # Set the scene for curr actions
        start_frame = tool.rootmotion_start_frame
        target_armature.animation_data.action = action
        end_frame = int(target_armature.animation_data.action.frame_range[1])
        scene.frame_end = end_frame

        if tool.rootmotion_use_rest_pose:
            # Get the TPose for reference initially
            # This will get proper deltas when the action starts from a pose
            # location diff from TPose
            hip_tpose_loc, hip_tpose_rot, _ = \
                target_armature.data.bones[hips_name].matrix_local.decompose()
        else:
            scene.frame_set(start_frame)
            hip_tpose_loc, hip_tpose_rot, _ = hip_bone.matrix.decompose()
        root_tpose_mtx = target_armature.data.bones[root_name].matrix_local

        # Extract the deltas from hip bone frames
        loc_delta_mtxs = []
        rot_delta_mtxs = []
        for frame in range(start_frame, end_frame + 1):
            # Set the frame to get the save xforms of the bones.
            scene.frame_set(frame)
            # Get the change in hip location along required axes
            hip_curr_loc, hip_curr_rot, _ = hip_bone.matrix.decompose()
            loc_delta = hip_curr_loc - hip_tpose_loc
            if not tool.rootmotion_use_translation[0]:  # X axis
                loc_delta[0] = 0
            if not tool.rootmotion_use_translation[1]:  # Y axis
                loc_delta[1] = 0
            if not tool.rootmotion_use_translation[2]:  # Z axis
                loc_delta[2] = 0
            if (
                tool.rootmotion_on_ground and
                tool.rootmotion_use_translation[2] and
                loc_delta[2] < 0
            ):
                loc_delta[2] = 0
            loc_delta_mtx = mathutils.Matrix.Translation(loc_delta)
            # Get the change in rotation about the selected axes
            rot_delta = (hip_curr_rot @ hip_tpose_rot.inverted()).to_euler()
            if not tool.rootmotion_use_rotation[0]:  # X axis
                rot_delta[0] = 0
            if not tool.rootmotion_use_rotation[1]:  # Y axis
                rot_delta[1] = 0
            if not tool.rootmotion_use_rotation[2]:  # Z axis
                rot_delta[2] = 0
            rot_delta_mtx = rot_delta.to_matrix().to_4x4()

            loc_delta_mtxs.append(loc_delta_mtx)
            rot_delta_mtxs.append(rot_delta_mtx)

            # Note: for proper matrix multiplication ordering apply world-
            # space delta translations 1st, since their rotations are 0, then
            # the delta rotations and finally the current matrix. This is
            # because translations are applied in the new rotational basis of
            # the matrix.

            # Apply to hip 1st then to root. Since hip is a child of root.
            hip_bone.matrix = (
                loc_delta_mtx.inverted() @
                rot_delta_mtx.inverted() @
                hip_bone.matrix
            )
            hip_bone.keyframe_insert(data_path='location')
            hip_bone.keyframe_insert(data_path='rotation_quaternion')
            hip_bone.keyframe_insert(data_path='scale')

        # Next apply the mtxs to the root bone
        index = 0
        for frame in range(start_frame, end_frame + 1):
            root_bone.matrix = (
                loc_delta_mtxs[index] @
                rot_delta_mtxs[index] @
                root_tpose_mtx
            )
            root_bone.keyframe_insert(data_path='location', frame=frame)
            root_bone.keyframe_insert(
                data_path='rotation_quaternion',
                frame=frame
            )
            root_bone.keyframe_insert(data_path='scale', frame=frame)
            index += 1
