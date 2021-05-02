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

    target_name: StringProperty(
        name="Target Action",
        description="The name of the action to add as a character action."
    )

    def execute(self, context):
        if not self.target_name:
            self.report({'ERROR'}, "The target name is not valid.")
            return {'CANCELLED'}

        action = bpy.data.actions.get(self.target_name)
        if not action:
            self.report(
                {'EEROR'},
                "No action named {} is available.".format(self.target_name)
            )
            return {'CANCELLED'}

        settings = context.scene.nkt_settings
        character = settings.get_active_character()
        idx = character.get_action_index(self.target_name)
        if idx >= 0:  # Already exists
            self.report(
                {'ERROR'},
                "A character action with name {} exists on character {}."
                .format(self.target_name, character.name)
            )
            return {'FINISHED'}

        idx = len(character.actions)
        char_action = character.actions.add()
        char_action.action = action
        character.active_action_index = idx
        character.validate_active_action()

        return {'FINISHED'}

    def invoke(self, context, event):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()
        armature = character.armature
        if not armature.animation_data or not armature.animation_data.action:
            self.report({'ERROR'}, "No valid action on active character.")
            return {'CANCELLED'}

        self.target_name = armature.animation_data.action.name

        return self.execute(context=context)


class NKT_OT_remove_character_action(Operator):
    bl_idname = 'nkt.character_remove_animation'
    bl_label = "Remove Character Animation"
    bl_description = (
        "Remove the active character action on the active character."
    )

    target_name: StringProperty(
        name="Target Action",
        description="The name of the action to remove from character actions."
    )

    def execute(self, context):
        if not self.target_name:
            self.report({'ERROR'}, "The target name is not valid.")
            return {'CANCELLED'}

        # action = bpy.data.actions.get(self.target_name)
        # if not action:
        #     self.report(
        #         {'EEROR'},
        #         "No action named {} is available.".format(self.target_name)
        #     )
        #     return {'CANCELLED'}

        settings = context.scene.nkt_settings
        character = settings.get_active_character()
        idx = character.get_action_index(self.target_name)
        if idx < 0:
            self.report(
                {'ERROR'},
                "No character action with name {} was found on character {}."
                .format(self.target_name, character.name)
            )
            return {'CANCELLED'}

        character.actions.remove(idx)
        new_index = max(0, min(idx, len(character.actions)-1))
        character.active_action_index = new_index
        character.validate_active_action()

        self.report({'INFO'}, "Removed character action.")
        return {'FINISHED'}

    def invoke(self, context, event):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()
        armature = character.armature
        if not armature.animation_data or not armature.animation_data.action:
            self.report({'ERROR'}, "No valid action on active character.")
            return {'CANCELLED'}

        self.target_name = armature.animation_data.action.name

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

            bpy.ops.nkt.character_add_animation(
                target_name=imported_action.name)

        # Delete Imported Armatures
        bpy.ops.object.delete({"selected_objects": remove_list})
        context.view_layer.objects.active = character.armature

        # Remove Cleared Keyframe Actions - Mixamo Fix
        bpy.ops.anim.clear_useless_actions(only_unused=False)
        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, "Animations Imported Successfully")
        return {'FINISHED'}


class NKT_OT_character_action_move(Operator):
    bl_idname = 'nkt.character_action_move'
    bl_label = "Move Character Action"
    bl_description = "Move the character action up or down in the actions list."

    move_type: EnumProperty(
        items=[
            ('MOVE_UP', "Move Up",
             "Move the character action up in the list", 'TRIA_UP', 0),
            ('MOVE_DOWN', "Move Down",
             "Move the character action down in the list", 'TRIA_DOWN', 1)
        ],
        name="Move Type",
        description="Move up or move down."
    )

    def execute(self, context):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()
        idx = character.active_action_index

        character.actions.move(
            idx, idx + 1 if self.move_type == 'MOVE_DOWN' else idx - 1)
        character.validate_active_action()

        return {'FINISHED'}


class NKT_OT_character_push_to_nla(Operator):
    bl_idname = 'nkt.character_push_to_nla'
    bl_label = "Push actions to NLA"
    bl_description = "Clear armature animation data and push all character action to NLA tracks."

    def execute(self, context):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()
        armature = character.armature

        if len(character.actions) < 0:
            self.report({'ERROR'}, "No actions linked to character.")
            return {'CANCELLED'}

        armature.animation_data_clear()

        for char_action in character.actions:
            anim_data = armature.animation_data_create()
            track = anim_data.nla_tracks.new()
            track.name = char_action.name
            track.strips.new(
                name=char_action.name,
                start=char_action.action.frame_range[0],
                action=char_action.action
            )

        return {'FINISHED'}


class NKT_OT_character_actions_menu(Operator):
    bl_idname = 'nkt.character_actions_menu'
    bl_label = "Actions Menu"
    bl_description = ""
    bl_property = 'menu_options'

    menu_options: EnumProperty(
        items=[
            ('MOVE_UP', "Move Up",
             "Move the character action up in the list", 'TRIA_UP', 0),
            ('MOVE_DOWN', "Move Down",
             "Move the character action down in the list", 'TRIA_DOWN', 1),
            ('ADD', "Add Active",
             "Add the active action on character armature as a new character action.", 'ADD', 2),
            ('REMOVE', "Remove Active",
             "Unlink and remove the active character action.", 'REMOVE', 3),
            ('LOAD', "Load New", "Load a new file with animation and it as a new character action.", 'NEWFOLDER', 4),
            None,
            ('PUSH_NLA', "Push to NLA Stash", "Push all the actions of the character to NLA tracks.", 'NLA_PUSHDOWN', 5)
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
        elif self.menu_options == 'MOVE_UP':
            bpy.ops.nkt.character_action_move(
                'INVOKE_DEFAULT', move_type='MOVE_UP')
        elif self.menu_options == 'MOVE_DOWN':
            bpy.ops.nkt.character_action_move(
                'INVOKE_DEFAULT', move_type='MOVE_DOWN')
        elif self.menu_options == 'PUSH_NLA':
            bpy.ops.nkt.character_push_to_nla('INVOKE_DEFAULT')
        return {'FINISHED'}
