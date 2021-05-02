import os
import bpy

from bpy.types import PropertyGroup, Operator
from bpy.props import (
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty
)
from bpy_extras.io_utils import ImportHelper

from .armature import rename_bones


class NKT_CharacterAction(PropertyGroup):
    action: PointerProperty(
        type=bpy.types.Action,
        name="Action",
        description="The pointer to associated action."
    )

    def set_action_name(self, value):
        new_name = value
        self.action.name = new_name

    def get_action_name(self):
        return self.action.name

    def on_action_name_updated(self, context):
        settings = context.scene.nkt_settings
        characters = settings.characters
        for character in characters:
            character.validate_active_action()

    name: StringProperty(
        name="Name",
        description="The name of the associated action.",
        set=set_action_name,
        get=get_action_name,
        update=on_action_name_updated
    )

    rootmotion_type: EnumProperty(
        items=[
            ('IN_PLACE', "In Place", "No rootmotion configured.",
             'EMPTY_SINGLE_ARROW', 0),
            ('ROOT_OBJECT', "Object Rootmotion",
             "Rootmotion configured on object.", 'OUTLINER_DATA_EMPTY', 1),
            ('ROOT_BONE', "Bone Rootmotion",
             "Rootmotion configured on a bone.", 'GROUP_BONE', 2)
        ],
        name="Rootmotion Type",
        description="The type of rootmotion configured for the action."
        # default='IN_PLACE'
    )


class NKT_Character(PropertyGroup):
    def poll_character_armature_valid(self, object):
        return object.type == 'ARMATURE'

    armature: PointerProperty(
        type=bpy.types.Object,
        name="Armature",
        description="The target armature into which the animations are merged",
        poll=poll_character_armature_valid
    )
    actions: CollectionProperty(
        type=NKT_CharacterAction,
        name="Character Actions",
        description="Collection of actions assigned to target character."
    )

    def get_action_index(self, name):
        idx = -1
        for i, action in enumerate(self.actions):
            if action.name == name:
                idx = i
        return idx

    def on_active_action_index_updated(self, context):
        if self.active_action_index >= 0:
            if not self.armature.animation_data:
                self.armature.animation_data_create()
            action = self.get_active_action().action
            self.armature.animation_data.action = action

            context.scene.frame_start = action.frame_range[0]
            context.scene.frame_end = action.frame_range[1]

    active_action_index: IntProperty(
        name="Active Character Action Index",
        description="Index of the active action on the character.",
        update=on_active_action_index_updated
    )

    def get_active_action(self):
        if self.active_action_index >= 0:
            return self.actions[self.active_action_index]

    def validate_active_action(self):
        curr_action = self.armature.animation_data.action
        active_action = self.get_active_action()
        if curr_action and active_action and curr_action != active_action.action:
            self.active_action_index = self.get_action_index(curr_action.name)

    def set_armature_name(self, value):
        self.armature.name = value

    def get_armature_name(self):
        return self.armature.name

    name: StringProperty(
        name="Name",
        description="The name of the associated armature object.",
        set=set_armature_name,
        get=get_armature_name
    )
    # Armature properies
    root_motion_type: EnumProperty(
        items=[
            ('OBJECT', "Object", "Apply root motion to the armature object."),
            ('BONE', "Bone", "Apply root motion to the root bone of armature.")
        ],
        name="Root Motion Type",
        description="The type of root motion to be used for baking.",
        default='BONE'
    )
    root_bone_name: StringProperty(
        name="Root Bone Name",
        description="The name of the root motion bone",
        maxlen=1024,
        default="root"
    )
    hip_bone_name: StringProperty(
        name="Hip Bone Name",
        description=(
            "Bone which will used to bake the root motion." +
            " Usually hips or pelvis"
        ),
        default="pelvis"
    )

    # Export properties
    export_name: StringProperty(
        name="Export Name",
        description="The name of the character, used as name of the export",
        default="nkt_character"
    )
    export_path: StringProperty(
        name="Export Path",
        description="The path for quick character export",
        subtype="DIR_PATH",
        default="//"
    )
    export_format: EnumProperty(
        items=[
            (
                'GLB', "glTF Binary (.glb)",
                "Exports a single file, with all data packed in binary form. " +
                "Most efficient and portable, but more difficult to edit later."
            ),
            (
                'GLTF_EMBEDDED', "glTF Embedded (.gltf)",
                "Exports a single file, with all data packed in JSON. " +
                "Less efficient than binary, but easier to edit later."
            ),
            (
                'GLTF_SEPARATE', "glTF Separate (.gltf + .bin + textures)",
                "Exports multiple files, with separate JSON, binary and " +
                "texture data. Easiest to edit later."
            )
        ],
        description="Output format and embedding options. " +
        "Binary is most efficient, but JSON (embedded or separate) " +
        "may be easier to edit later",
        name="Export Format",
        default='GLTF_SEPARATE'
    )


class NKT_OT_init_character(Operator):
    bl_idname = 'nkt.character_initialize'
    bl_label = "Initialize Character"
    bl_description = (
        "Used to init 'Main' character armature." +
        " The character should have 'T-Pose' animation from Mixamo."
    )
    bl_options = {'REGISTER', 'UNDO'}

    target_name: StringProperty(
        name="Target Name",
        description="The name of target object to initialize as a character."
    )

    def execute(self, context):
        if not self.target_name:
            self.report({'ERROR'}, "The target name is not valid.")
            return {'CANCELLED'}

        target = bpy.data.objects.get(self.target_name)

        if not target or target.type != 'ARMATURE':
            self.report({'ERROR'}, "The target is not a valid armature.")
            return {'CANCELLED'}

        settings = context.scene.nkt_settings
        characters = settings.characters
        if characters.get(target.name):
            self.report(
                {'INFO'}, "The target is already initialized as a character")
            return {'FINISHED'}

        current_mode = context.object.mode

        target.name = 'Character'
        target.rotation_mode = 'QUATERNION'
        target.animation_data_clear()
        rename_bones(target)
        current_mode = context.object.mode

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        target.select_set(True)
        context.view_layer.objects.active = target
        bpy.ops.object.transform_apply(
            location=True, rotation=True, scale=True)

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()

        bpy.ops.object.mode_set(mode=current_mode)
        idx = len(characters)
        character = characters.add()
        character.armature = target
        settings.active_character_index = idx

        self.report({'INFO'}, "Character Initialized.")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.target_name = context.view_layer.objects.active.name
        return self.execute(context)


class NKT_OT_load_character(Operator, ImportHelper):
    bl_idname = 'nkt.character_load'
    bl_label = "Load Character"
    bl_description = (
        "Used to load and initialize 'Main' character armature." +
        " Loaded character should have 'T-Pose'."
    )
    filename_ext: StringProperty(default=".fbx", options={'HIDDEN'})
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
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
            self.report({'ERROR'}, "Imported object has no valid armature.")
            bpy.ops.object.delete({'selected_objects': imported_objs})
            return {'CANCELLED'}

        bpy.ops.nkt.character_initialize(target_name=target_armature.name)
        return {'FINISHED'}


class NKT_OT_search_character(Operator):
    bl_idname = 'nkt.character_search_name'
    bl_label = "Select Active Character"
    bl_description = "Select the active character for the tool operations."
    bl_property = 'active_character_name'

    def populate_character_names(self, context):
        settings = context.scene.nkt_settings
        characters = settings.characters
        names = self['character_names'] = [
            (c.name, c.name, "") for c in characters]
        return names

    active_character_name: EnumProperty(
        items=populate_character_names,
        name="Active Character",
        description="The character that is currently being worked on."
    )

    def execute(self, context):
        settings = context.scene.nkt_settings
        characters = settings.characters
        settings.active_character_index = characters.find(
            self.active_character_name)
        self.report({'INFO'}, "Selected: " + self.active_character_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        settings = context.scene.nkt_settings
        self.active_character_name = settings.get_active_character().name
        context.window_manager.invoke_search_popup(self)
        return {'RUNNING_MODAL'}


class NKT_OT_character_menu(Operator):
    bl_idname = 'nkt.character_menu'
    bl_label = "Character Menu"
    bl_description = ""
    bl_property = 'menu_options'

    menu_options: EnumProperty(
        items=[
            ('INIT', "Initiaize", ""),
            ('LOAD', "Load", ""),
            ('SELECT', "Select", "")
        ],
        name="Character Menu Options",
        description=""
    )

    def execute(self, context):
        if self.menu_options == 'INIT':
            bpy.ops.nkt.character_initialize('INVOKE_DEFAULT')
        elif self.menu_options == 'LOAD':
            bpy.ops.nkt.character_load('INVOKE_DEFAULT')
        elif self.menu_options == 'SELECT':
            bpy.ops.nkt.character_search_name('INVOKE_DEFAULT')
        return {'FINISHED'}


class NKT_OT_character_quick_export(Operator):
    bl_idname = 'nkt.character_quick_export'
    bl_label = "Quick Export Character"
    bl_description = "Exports character."

    def execute(self, context):
        settings = context.scene.nkt_settings
        character = settings.get_active_character()

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        character.armature.select_set(True)
        context.view_layer.objects.active = character.armature

        # Generate Filename To Export
        fileName = os.path.join(
            bpy.path.abspath(character.export_path), character.export_name
        )

        # Push animation to NLA Tracks
        bpy.ops.nkt.character_push_to_nla()

        bpy.ops.export_scene.gltf(
            filepath=fileName,
            export_format=character.export_format,
            export_frame_range=False,
            export_force_sampling=False,
            export_tangents=False,
            export_image_format="AUTO",
            export_cameras=False,
            export_lights=False
        )

        self.report({'INFO'}, 'Character File Exported')
        return {'FINISHED'}
