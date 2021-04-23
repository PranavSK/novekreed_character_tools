import os
import bpy

from bpy.types import Operator, OperatorFileListElement
from bpy.props import (
    CollectionProperty,
    EnumProperty,
    StringProperty
)
from bpy_extras.io_utils import ImportHelper

from .armature import prepare_anim_rig


class NKT_OT_add_character_animation(Operator):
    bl_idname = 'nkt.character_add_animation'
    bl_label = "Add Character Animation"
    bl_description = (
        "Add the current action as a character action on the active character."
    )

    def execute(self, context):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()
        armature = character.armature
        if not armature.animation_data.action:
            self.report({'ERROR'}, "No valid action on active character.")
            return {'CANCELLED'}

        idx = len(character.actions)
        char_action = character.actions.add()
        char_action.action = armature.animation_data.action
        character.active_action_index = idx

        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context=context)


class NKT_OT_remove_character_action(Operator):
    bl_idname = 'nkt.character_remove_animation'
    bl_label = "Remove Character Animation"
    bl_description = (
        "Remove the active character action on the active character."
    )

    def execute(self, context):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()
        idx = character.active_action_index
        character.actions.remove(idx)
        new_index = max(0, min(idx, len(character.actions)-1))
        character.active_action_index = new_index
        character.validate_active_action()

        self.report({'INFO'}, "Removed character action.")
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context=context)


class NKT_OT_load_character_animation(Operator, ImportHelper):
    bl_idname = 'nkt.character_load_animation'
    bl_label = "Load Character Animations"
    bl_description = "Join mixamo animations into a single armature"
    filename_ext: StringProperty(default=".fbx", options={'HIDDEN'})
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})
    files: CollectionProperty(type=OperatorFileListElement)
    directory: StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()

        if len(self.files) <= 0:
            self.report({'ERROR'}, "No files provided.")
            return {'CANCELLED'}

        current_mode = context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        remove_list = []
        for file in self.files:
            filename = file.name
            file_basename = os.path.basename(filename)
            action_name, ext = os.path.splitext(file_basename)
            bpy.ops.object.select_all(action='DESELECT')
            # self.report({'INFO'}, "Action: {}".format(action_name))

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
                    {'ERROR'},
                    "Imported animation is not valid. No armature found " +
                    "in {}".format(filename)
                )
                bpy.ops.object.delete({'selected_objects': imported_objs})
                continue

            imported_action = imported_armature.animation_data.action
            if not imported_action:
                self.report(
                    {'ERROR'},
                    "Imported animation is not valid in {}.".format(filename)
                )
                bpy.ops.object.delete({'selected_objects': imported_objs})
                continue

            remove_list.extend(imported_objs)
            prepare_anim_rig(context, imported_armature)

            imported_action.name = action_name
            if len(imported_action.groups) > 0:
                imported_action.groups[0].name = "NKT Imported"

            idx = len(character.actions)
            char_action = character.actions.add()
            char_action.action = imported_action
            character.active_action_index = idx

        # Delete Imported Armatures
        bpy.ops.object.delete({"selected_objects": remove_list})
        context.view_layer.objects.active = character.armature

        # Remove Cleared Keyframe Actions - Mixamo Fix
        bpy.ops.anim.clear_useless_actions(only_unused=False)
        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, "Animations Imported Successfully")
        return {'FINISHED'}


class NKT_OT_character_actions_menu(Operator):
    bl_idname = 'nkt.character_actions_menu'
    bl_label = "Actions Menu"
    bl_description = ""
    bl_property = 'menu_options'

    menu_options: EnumProperty(
        items=[
            ('ADD', "Add Active", ""),
            ('LOAD', "Load New", ""),
            ('REMOVE', "Remove Active", ""),
            #('PUSH_NLA', "Push to NLA Stash")
        ],
        name="Character Actions Menu Options",
        description=""
    )

    def execute(self, context):
        if self.menu_options == 'ADD':
            bpy.ops.nkt.character_add_animation('INVOKE_DEFAULT')
        elif self.menu_options == 'LOAD':
            bpy.ops.nkt.character_load_animation('INVOKE_DEFAULT')
        elif self.menu_options == 'REMOVE':
            bpy.ops.nkt.character_remove_animation('INVOKE_DEFAULT')
        return {'FINISHED'}
