import bpy

from bpy.props import (
    IntProperty,
    StringProperty,
    PointerProperty,
    BoolVectorProperty,
    EnumProperty,
    BoolProperty
)
from bpy.types import PropertyGroup

from .utils import validate_target_armature

from .operators.export_character_controller import (
    NCT_OT_character_export
)
from .operators.animation_controller import (
    NCT_OT_animation_play,
    NCT_OT_animation_stop,
    NCT_OT_trim_animation,
    NCT_OT_animation_delete
)
from .operators.rootmotion_controller import (
    NCT_OT_add_rootbone,
    NCT_OT_add_rootmotion
)
from .operators.character_controller import (
    NCT_OT_init_character,
    NCT_OT_join_animations,
    NCT_OT_armature_join_mesh
)
from .panels.main_panel import (
    NCT_PT_main_panel,
    ACTION_UL_character_actions,
)


bl_info = {
    "name": "Novkreed Character Tools",
    "version": (0, 0, 3),
    "blender": (2, 91, 0),
    "location": "3D View > Tools",
    "warning": "",
    "category": "Character"
}


def toggle_armature_visibility(self, context):
    scene = context.scene
    tool = scene.novkreed_character_tools
    target_armature = tool.target_object
    is_armature_visible = tool.is_armature_visible
    target_armature.hide_viewport = not is_armature_visible
    context.object.show_in_front = not is_armature_visible


def populate_exporters(self, context):
    exporters = []
    exporters.append(("0", "GLTF", ""))
    exporters.append(("1", "GLB", ""))
    return exporters


def on_update_selected_action_index(self, context):
    if not validate_target_armature(context.scene):
        self.report({'WARN'}, "No target armature.")
        return

    tool = context.scene.novkreed_character_tools
    idx = tool.selected_action_index
    if idx is None or not (0 <= idx < len(bpy.data.actions)):
        self.report({'INFO'}, "Nothing selected in the list.")
        return

    target_armature = tool.target_object
    selected_action = bpy.data.actions[idx]
    target_armature.animation_data.action = selected_action
    context.scene.frame_current = 1
    context.scene.frame_end = selected_action.frame_range[1]


class NCT_AddonProperties(PropertyGroup):
    '''Property container for options and paths of Mixamo Tools'''
    target_object: PointerProperty(
        name="Armature",
        description="The target armature into which the animations are merged",
        type=bpy.types.Object
    )
    is_armature_visible: BoolProperty(
        name="Show Armature Bones",
        description="Hides / Show armature bones once animations are loaded",
        default=True,
        update=toggle_armature_visibility
    )
    # Exporters
    character_export_character_name: StringProperty(
        name="Character Name",
        description="The name of the character, used as name of the export",
        default="CharacterName"
    )
    character_export_path: StringProperty(
        name="Export Path",
        description="The path for quick character export",
        subtype="DIR_PATH",
        default="//"
    )
    character_export_format: EnumProperty(
        name="Export Format",
        description="Choose format for quick export",
        items=populate_exporters,
        default=None,
    )
    # Animations
    selected_action_index: IntProperty(
        name="Active Index",
        description="The index of the active animation in list",
        update=on_update_selected_action_index
    )
    trim_animation_name: StringProperty(
        name="New Animation",
        description="New animation name for the trimed action",
        maxlen=1024
    )
    trim_animation_from: IntProperty(
        name="From Frame",
        description="The desired start trim frame",
        default=1,
        min=0,
        max=1024
    )
    trim_animation_to: IntProperty(
        name="To Frame",
        description="The desired end trim frame",
        default=1,
        min=0,
        max=1024
    )
    # RootMotion Variables
    rootmotion_name: StringProperty(
        name="Root Bone Name",
        description="Choose name you want for the RootMotion Bone",
        maxlen=1024,
        default="Root"
    )
    is_rootmotion_all: BoolProperty(
        name="Apply Rootmotion To All",
        description="Apply rootmotion to all animations",
        default=False
    )
    rootmotion_hip_bone: StringProperty(
        name="Hip Bone",
        description=(
            "Bone which will used to bake the root motion." +
            " Usually hips or pelvis"
        )
    )
    rootmotion_start_frame: IntProperty(
        name="Rootmotion Start Frame",
        description="The initial frame for rootmotion bake",
        default=1,
        min=-1,
        max=1024
    )
    rootmotion_use_translation: BoolVectorProperty(
        name="Bake Translation",
        description="Process the selected axes for rootmotion bake.",
        subtype='XYZ',
        size=3,
        default=(True, True, True)
    )
    rootmotion_on_ground: BoolProperty(
        name="On Ground",
        description="Keep the Z axis +ve for rootmotion bake.",
        default=True
    )
    rootmotion_use_rotation: BoolProperty(
        name="Bake Rotation",
        description=(
            "Process the rotation about Z axes" +
            " for rootmotion bake."
        ),
        default=True
    )
    rootmotion_use_rest_pose: BoolProperty(
        name="Use Rest Pose",
        description=(
            "Use rest pose as reference for calculating the change of" +
            " transforms for the hip. This is useful when animation starts" +
            " in air etc."
        ),
        default=False
    )


classes = (
    # Panels
    NCT_PT_main_panel,
    # UI Lists
    ACTION_UL_character_actions,
    # Character Controller
    NCT_OT_init_character,
    NCT_OT_join_animations,
    NCT_OT_armature_join_mesh,
    # Animation Controller
    NCT_OT_animation_play,
    NCT_OT_animation_stop,
    NCT_OT_trim_animation,
    NCT_OT_animation_delete,
    # Quick Export
    NCT_OT_character_export,
    # RootMotion Controller
    NCT_OT_add_rootbone,
    NCT_OT_add_rootmotion,
    # Default Add-On Properties
    NCT_AddonProperties
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.novkreed_character_tools = PointerProperty(
        type=NCT_AddonProperties,
        name="NCT Addon Properties"
    )


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.novkreed_character_tools


if __name__ == "__main__":
    register()
