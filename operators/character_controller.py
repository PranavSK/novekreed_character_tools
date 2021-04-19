import bpy
import os

from bpy.props import (StringProperty, CollectionProperty)
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from ..utils.actions import TPOSE_ACTION_NAME, push_to_nla_stash
from ..utils.armature import (
    get_hip_bone_name,
    prepare_anim_rig,
    prepare_tpose_rig,
    validate_target_armature
)


class NCT_OT_init_character(Operator):
    bl_idname = "nct.init_character"
    bl_label = "Initialize Character"
    bl_description = (
        "Used to init 'Main' Armature." +
        " The character should have 'T-Pose' animation from Mixamo."
    )
    bl_options = {'REGISTER', 'UNDO'}

    target_name: StringProperty(name="target_name")

    def execute(self, context):
        scene = context.scene
        tool = scene.novkreed_character_tools
        if self.target_name:
            target_armature = bpy.data.objects[self.target_name]
        else:
            target_armature = context.view_layer.objects.active

        if not target_armature or target_armature.type != 'ARMATURE':
            self.report(
                {'ERROR'},
                "The object is not a valid armature."
            )
            return {'CANCELLED'}

        if validate_target_armature(scene):
            self.report(
                {'ERROR'},
                "A character armature exists. Only one can worked per scene."
            )
            return {'CANCELLED'}

        current_mode = context.object.mode

        target_armature.name = "Armature"
        target_armature.rotation_mode = 'QUATERNION'
        prepare_tpose_rig(context, target_armature)

        tool.rootmotion_hip_bone = get_hip_bone_name(target_armature)

        tool.target_object = target_armature
        tpose_action = target_armature.animation_data.action
        tpose_action.name = TPOSE_ACTION_NAME
        if len(tpose_action.groups) > 0:
            tpose_action.groups[0].name = TPOSE_ACTION_NAME
        tpose_action['is_nct_processed'] = True
        push_to_nla_stash(armature=target_armature, action=tpose_action)

        # Update list index
        tool.selected_action_index = bpy.data.actions.find(TPOSE_ACTION_NAME)
        target_armature.animation_data.action = tpose_action

        if len(tpose_action.frame_range) > 0:
            context.scene.frame_end = tpose_action.frame_range[1]

        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, "Character Initialized.")
        return {'FINISHED'}


class NCT_OT_load_character(Operator, ImportHelper):
    bl_idname = "nct.load_character"
    bl_label = "Load Character"
    bl_description = (
        "Used to load and init 'Main' Armature." +
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
            axis_forward='-Z',
            axis_up='Y',
            bake_space_transform=False,
            use_custom_normals=True,
            use_image_search=True,
            use_alpha_decals=False, decal_offset=0.0,
            use_anim=True, anim_offset=1.0,
            use_custom_props=True,
            use_custom_props_enum_as_string=True,
            force_connect_children=False,
            ignore_leaf_bones=True,
            automatic_bone_orientation=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_prepost_rot=True
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

        bpy.ops.nct.init_character(target_name=target_armature.name)
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

        current_mode = context.object.mode

        for file in self.files:
            filename = file.name
            file_basename = os.path.basename(filename)
            action_name, ext = os.path.splitext(file_basename)

            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, "Action: {}".format(action_name))

            if action_name == TPOSE_ACTION_NAME:
                continue

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

            remove_list.extend(imported_objs)

            prepare_anim_rig(context, imported_armature)
            imported_action = imported_armature.animation_data.action
            imported_action.name = action_name
            if len(imported_action.groups) > 0:
                imported_action.groups[0].name = action_name
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

        bpy.ops.object.mode_set(mode=current_mode)

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
        context.view_layer.objects.active = target_armature
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
