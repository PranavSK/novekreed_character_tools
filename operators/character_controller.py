import bpy
import os

from bpy.props import (StringProperty, CollectionProperty)
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from ..utils import (push_to_nla_stash, validate_target_armature)

TPOSE_ACTION_NAME = "T-Pose"
MIXAMO_GROUP_NAME = "Mixamo"


def xform_mixamo_action(action, hip_bone_name, scale_to_apply):
    req_data_path = 'pose.bones[\"{}\"].location'.format(hip_bone_name)

    if len(action.groups) > 0:
        action.groups[0].name = MIXAMO_GROUP_NAME

    for fcurve in action.fcurves:
        if fcurve.data_path == req_data_path:
            for keyframe in fcurve.keyframe_points:
                keyframe.co[1] *= scale_to_apply[fcurve.array_index]


class NCT_OT_init_character(Operator, ImportHelper):
    bl_idname = "nct.init_character"
    bl_label = "Initialize Character"
    bl_description = (
        "Used to init 'Main' Armature." +
        " Loaded character should have 'T-Pose' animation from Mixamo."
    )
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
        scene = context.scene
        tool = scene.novkreed_character_tools
        if validate_target_armature(scene):
            self.report(
                {'ERROR'},
                "A character armature exists. Only one can worked per scene."
            )
            return {'CANCELLED'}

        self.report({'INFO'}, "Loading Character T-Pose")
        bpy.ops.import_scene.fbx(
            filepath=self.filepath,
            ignore_leaf_bones=True,
            automatic_bone_orientation=True
        )

        imported_objs = context.selected_objects
        target_armature = next(
            (obj for obj in imported_objs if obj.type == 'ARMATURE'),
            None
        )
        if target_armature is None:
            self.report(
                {'ERROR'},
                "Imported character is not valid. No armature found"
            )
            bpy.ops.object.delete({'selected_objects': imported_objs})
            return {'CANCELLED'}

        bone_names = []
        for bone in target_armature.data.bones:
            bone_names.append(bone.name.replace("mixamorig:", ""))
        tool.rootmotion_hip_bone = "Hips" if "Hips" in bone_names else ""
        target_armature.name = "Armature"

        tool.target_object = target_armature
        tpose_action = target_armature.animation_data.action
        tpose_action.name = TPOSE_ACTION_NAME
        tpose_action['is_nct_processed'] = True
        push_to_nla_stash(armature=target_armature, action=tpose_action)

        # xform the action keyframes to avoid issues when rig has its transform
        # applied in 'bpy.ops.nct.prepare_mixamo_rig'
        xform_mixamo_action(
            action=tpose_action,
            hip_bone_name=tool.rootmotion_hip_bone,
            scale_to_apply=target_armature.scale
        )

        # Update list index
        tool.selected_action_index = bpy.data.actions.find(TPOSE_ACTION_NAME)
        target_armature.animation_data.action = tpose_action

        if len(tpose_action.frame_range) > 0:
            context.scene.frame_end = tpose_action.frame_range[1]

        bpy.ops.nct.prepare_mixamo_rig('EXEC_DEFAULT')
        self.report({'INFO'}, "Character Initialized.")
        return {'FINISHED'}


class NCT_OT_prepare_mixamo_rig(Operator):
    bl_idname = "nct.prepare_mixamo_rig"
    bl_label = "Prepare Mixamo Rig"
    bl_description = "Fix mixamo rig to export"

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        target_armature = tool.target_object
        # Apply transformations on selected Armature
        target_armature['nct_applied_rig_scale'] = target_armature.scale
        context.view_layer.objects.active = target_armature
        current_mode = context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(
            location=True,
            rotation=True,
            scale=True
        )
        bpy.ops.object.mode_set(mode=current_mode)

        bpy.ops.nct.rename_rig_bones('EXEC_DEFAULT')
        self.report({'INFO'}, "Rig Armature Prepared")
        return {'FINISHED'}


class NCT_OT_rename_rig_bones(Operator):
    bl_idname = "nct.rename_rig_bones"
    bl_label = "Rename Rig Bones"
    bl_description = "Rename rig bones"

    def execute(self, context):
        scene = context.scene
        tool = scene.novkreed_character_tools
        if not validate_target_armature(context.scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        target_armature = tool.target_object
        for mesh in target_armature.children:
            for vertex_group in mesh.vertex_groups:
                # If no ':' probably its already renamed
                if ':' in vertex_group.name:
                    vertex_group.name = vertex_group.name.split(":")[1]

        for bone in target_armature.pose.bones:
            if ':' in bone.name:
                bone.name = bone.name.split(":")[1]

        self.report({'INFO'}, "Character Bones Successfully Renamed")
        return {'FINISHED'}


class NCT_OT_join_animations(Operator, ImportHelper):
    bl_idname = "nct.join_animations"
    bl_label = "Join Animations"
    bl_description = "Join mixamo animations into a single armature"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement)
    directory: StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        tool = context.scene.novkreed_character_tools
        target_armature = tool.target_object
        remove_list = []
        # Debug
        remove_imports = True

        if not validate_target_armature(context.scene):
            self.report({'ERROR'}, "No valid target armature stored.")
            return {'CANCELLED'}

        if len(self.files) <= 0:
            self.report({'ERROR'}, "No files provided.")
            return {'CANCELLED'}

        for file in self.files:
            filename = file.name
            file_basename = os.path.basename(filename)
            action_name, ext = os.path.splitext(file_basename)

            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, "Action: {}".format(action_name))

            if action_name == TPOSE_ACTION_NAME:
                continue

            if (hasattr(bpy.types, bpy.ops.import_scene.fbx.idname())):
                bpy.ops.import_scene.fbx(
                    filepath=os.path.join(self.directory, filename),
                    ignore_leaf_bones=True,
                    automatic_bone_orientation=True
                )
                imported_objs = context.selected_objects
                imported_armature = next(
                    (obj for obj in imported_objs if obj.type == 'ARMATURE'),
                    None
                )
                if imported_armature is None:
                    self.report(
                        {'INFO'},
                        "Imported animation is not valid. No armature found " +
                        "in {}".format(filename)
                    )
                    bpy.ops.object.delete({'selected_objects': imported_objs})
                    continue

                imported_armature.animation_data.action.name = action_name
                # Rename the bones
                for bone in imported_armature.pose.bones:
                    if ':' in bone.name:
                        bone.name = bone.name.split(":")[1]

                remove_list.extend(imported_objs)

                imported_action = imported_armature.animation_data.action

                xform_mixamo_action(
                    action=imported_action,
                    hip_bone_name=tool.rootmotion_hip_bone,
                    scale_to_apply=target_armature['nct_applied_rig_scale']
                )

                imported_action['is_nct_processed'] = True

                push_to_nla_stash(
                    armature=target_armature,
                    action=imported_action
                )

        # Delete Imported Armatures
        if remove_imports:
            bpy.ops.object.delete({"selected_objects": remove_list})
            context.view_layer.objects.active = target_armature

        # Remove Cleared Keyframe Actions - Mixamo Fix
        bpy.ops.anim.clear_useless_actions(only_unused=False)

        # Reset active action to TPose
        tool.selected_action_index = bpy.data.actions.find(TPOSE_ACTION_NAME)
        target_armature.animation_data.action = \
            bpy.data.actions[TPOSE_ACTION_NAME]

        self.report({'INFO'}, "Animations Imported Successfully")
        return {'FINISHED'}


class NCT_OT_armature_join_mesh(Operator):
    bl_idname = "nct.armature_join_mesh"
    bl_label = "Join Armature Meshes"
    bl_description = "Join every children mesh of armature into single object"

    def execute(self, context):
        scene = context.scene
        tool = scene.novkreed_character_tools
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        target_armature = tool.target_object
        current_mode = context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh_to_join = None
        for mesh in target_armature.children:
            if mesh.type == 'MESH':
                mesh.select_set(True)
                mesh_to_join = mesh

        if mesh_to_join:
            context.view_layer.objects.active = mesh_to_join
            bpy.ops.object.join()
            body_mesh = context.view_layer.objects.active
            body_mesh.name = "Mesh"
            self.report({'INFO'}, 'Armature Meshes Joined')

        bpy.ops.object.mode_set(mode=current_mode)

        return {'FINISHED'}
