import bpy

from bpy.types import PropertyGroup, Operator
from bpy.props import BoolProperty, BoolVectorProperty, IntProperty

from .baker import (
    apply_baker_to_bone,
    extract_constrained_from_bone,
    extract_loc_rot_from_bone
)


def bake_rootmotion(
    armature,
    action,
    hip_bone_name,
    root_bone_name,
    use_x,
    use_y,
    use_z,
    on_ground,
    use_rot,
    start_frame,
    end_frame=None
):
    # Set the scene for curr actions
    armature.animation_data.action = action
    if not end_frame:
        end_frame = int(action.frame_range[1])

    # Create helper to bake the root motion
    root_baker = extract_constrained_from_bone(
        armature=armature,
        action=action,
        bone_name=hip_bone_name,
        use_x=use_x,
        use_y=use_y,
        use_z=use_z,
        on_ground=on_ground,
        use_rot=use_rot,
        start_frame=start_frame,
        end_frame=end_frame,
        baker_name='NKT_root_baker'
    )

    # Create helper to bake hipmotion in Worldspace
    hips_baker = extract_loc_rot_from_bone(
        armature=armature,
        action=action,
        bone_name=hip_bone_name,
        start_frame=start_frame,
        end_frame=end_frame,
        baker_name='NKT_{}_baker'.format(hip_bone_name)
    )

    # Apply the root bone 1st.
    apply_baker_to_bone(
        baker=root_baker,
        armature=armature,
        action=action,
        target_bone_name=root_bone_name,
        use_rot_offset=True, # Apply to maintain parent rotation.
        start_frame=start_frame,
        end_frame=end_frame
    )

    # Since the root bone motion is applied 1st, the baker will ensure that hips
    # have proper anim curves considering the root as parent.
    apply_baker_to_bone(
        baker=hips_baker,
        armature=armature,
        action=action,
        target_bone_name=hip_bone_name,
        use_rot_offset=False, # Ignore as root is adjusted.
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


class NKT_RootmotionSettings(PropertyGroup):
    start_frame: IntProperty(
        name="Start Frame",
        description="The initial frame for rootmotion bake",
        default=1,
        min=-1,
        max=1024
    )
    use_translation: BoolVectorProperty(
        name="Bake Translation",
        description="Process the selected axes for rootmotion bake.",
        subtype='XYZ',
        size=3,
        default=(True, True, True)
    )
    on_ground: BoolProperty(
        name="On Ground",
        description="Use the Z offset and keep the Z axis +ve for rootmotion.",
        default=True
    )
    use_rotation: BoolProperty(
        name="Bake Rotation",
        description="Process the rotation about Z axis for rootmotion bake.",
        default=True
    )


class NKT_OT_add_rootbone(Operator):
    bl_idname = 'nkt.character_add_rootbone'
    bl_label = "Add Root Bone"
    bl_description = "Adds armature root bone for root motion"

    def execute(self, context):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()

        context.view_layer.objects.active = character.armature
        current_mode = context.object.mode
        bpy.ops.object.mode_set(mode='EDIT')
        editbones = character.armature.data.edit_bones
        if character.root_bone_name in editbones.keys():
            self.report({'INFO'}, 'Root Bone Exists.')
            return {'FINISHED'}
        # Bone Setup
        rootmotion_bone = editbones.new(character.root_bone_name)
        rootmotion_bone.head = (0.0, 0.0, 0.0)
        rootmotion_bone.tail = (0.0, 0.0, 0.2)

        editbones[character.hip_bone_name].parent = rootmotion_bone
        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Bone Added')

        return {'FINISHED'}


class NKT_OT_add_rootmotion(Operator):
    bl_idname = 'nkt.character_add_rootmotion'
    bl_label = "Add Root Motion"
    bl_description = "Adds Root Motion to Animations"

    def execute(self, context):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()

        context.view_layer.objects.active = character.armature
        current_mode = context.object.mode

        is_bone_exists = character.root_bone_name in character.armature.pose.bones.keys()
        if not is_bone_exists:
            bpy.ops.nkt.character_add_rootbone()

        bake_rootmotion(
            armature=character.armature,
            action=character.get_active_action().action,
            hip_bone_name=character.hip_bone_name,
            root_bone_name=character.root_bone_name,
            use_x=settings.rootmotion.use_translation[0],
            use_y=settings.rootmotion.use_translation[1],
            use_z=settings.rootmotion.use_translation[2],
            on_ground=settings.rootmotion.on_ground,
            use_rot=settings.rootmotion.use_rotation,
            start_frame=settings.rootmotion.start_frame
        )

        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Motion Updated')
        return {'FINISHED'}
