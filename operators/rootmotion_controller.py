import bpy

from bpy.props import StringProperty
from bpy.types import Operator
from ..utils.baker import (
    BONE_BAKER_NAME,
    ROOT_BAKER_NAME,
    apply_baker_to_bone,
    extract_constrained_from_bone,
    extract_loc_rot_from_bone
)
from ..utils.armature import validate_target_armature


def bake_rootmotion(
    armature,
    action,
    hips_name,
    root_name,
    use_x,
    use_y,
    use_z,
    on_ground,
    use_rot,
    start_frame
):
    if not action.get('is_nct_processed') or action.get('has_root_motion'):
        return

    # Set the scene for curr actions
    armature.animation_data.action = action
    end_frame = int(armature.animation_data.action.frame_range[1])

    # Create helper to bake the root motion
    root_baker = extract_constrained_from_bone(
        armature=armature,
        action=action,
        bone_name=hips_name,
        use_x=use_x,
        use_y=use_y,
        use_z=use_z,
        on_ground=on_ground,
        use_rot=use_rot,
        start_frame=start_frame,
        end_frame=end_frame,
        baker_name=ROOT_BAKER_NAME
    )

    # Create helper to bake hipmotion in Worldspace
    hips_baker = extract_loc_rot_from_bone(
        armature=armature,
        action=action,
        bone_name=hips_name,
        start_frame=start_frame,
        end_frame=end_frame,
        baker_name=BONE_BAKER_NAME.format(bone_name=hips_name)
    )

    # Apply the root bone 1st.
    apply_baker_to_bone(
        baker=root_baker,
        armature=armature,
        action=action,
        target_bone_name=root_name,
        use_rot_offset=True,
        start_frame=start_frame,
        end_frame=end_frame
    )

    # Since the root bone motion is applied 1st, the baker will ensure that hips
    # have proper anim curves considering the root as parent.
    apply_baker_to_bone(
        baker=hips_baker,
        armature=armature,
        action=action,
        target_bone_name=hips_name,
        use_rot_offset=False,
        start_frame=start_frame,
        end_frame=end_frame
    )

    # Delete helpers
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    hips_baker.select_set(True)
    root_baker.select_set(True)

    bpy.data.actions.remove(hips_baker.animation_data.action)
    bpy.data.actions.remove(root_baker.animation_data.action)

    bpy.ops.object.delete(use_global=False)

    action['has_root_motion'] = True


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

        if not target_armature or target_armature.type != 'ARMATURE':
            self.report({'ERROR'}, "The object is not a valid armature.")
            return {'CANCELLED'}

        rootmotion_root_name = tool.rootmotion_name
        hips_name = tool.rootmotion_hip_bone

        # Bones
        if not hips_name:
            self.report(
                {'ERROR'},
                "No valid hip bone selected.")
            return {'CANCELLED'}

        context.view_layer.objects.active = target_armature
        current_mode = context.object.mode
        bpy.ops.object.mode_set(mode='EDIT')
        context.view_layer.objects.active = target_armature
        editbones = target_armature.data.edit_bones
        if rootmotion_root_name in editbones.keys():
            self.report({'INFO'}, 'Root Bone Exists.')
            return {'FINISHED'}
        # Bone Setup
        rootmotion_bone = editbones.new(rootmotion_root_name)
        rootmotion_bone.head = (0.0, 0.0, 0.0)
        rootmotion_bone.tail = (0.0, 0.0, 0.2)

        editbones[hips_name].parent = rootmotion_bone
        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Bone Added')

        return {'FINISHED'}


class NCT_OT_add_rootmotion(Operator):
    bl_idname = "nct.add_rootmotion"
    bl_label = "Add Root Motion"
    bl_description = "Adds Root Motion to Animations"

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
                bake_rootmotion(
                    armature=target_armature,
                    action=action,
                    hips_name=tool.rootmotion_hip_bone,
                    root_name=tool.rootmotion_name,
                    use_x=tool.rootmotion_use_translation.x,
                    use_y=tool.rootmotion_use_translation.y,
                    use_z=tool.rootmotion_use_translation.z,
                    on_ground=tool.rootmotion_on_ground,
                    use_rot=tool.rootmotion_use_rotation,
                    start_frame=tool.rootmotion_start_frame
                )
        else:
            idx = tool.selected_action_index
            action = bpy.data.actions[idx]
            bake_rootmotion(
                armature=target_armature,
                action=action,
                hips_name=tool.rootmotion_hip_bone,
                root_name=tool.rootmotion_name,
                use_x=tool.rootmotion_use_translation[0],
                use_y=tool.rootmotion_use_translation[1],
                use_z=tool.rootmotion_use_translation[2],
                on_ground=tool.rootmotion_on_ground,
                use_rot=tool.rootmotion_use_rotation,
                start_frame=tool.rootmotion_start_frame
            )

        scene.frame_set(frame_curr)
        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Motion Updated')
        return {'FINISHED'}
