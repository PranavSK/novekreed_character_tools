import bpy

from .setup import NCT_AddonProperties

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
    NCT_OT_load_character,
    NCT_OT_join_animations,
    NCT_OT_armature_join_mesh
)
from .panels.main_panel import (
    NCT_PT_main_panel,
    ACTION_UL_character_actions,
)


bl_info = {
    "name": "Novkreed Character Tools",
    "version": (0, 1, 1),
    "blender": (2, 92, 0),
    "location": "3D View > Tools > Character",
    "author": "Pranav S Koundinya",
    "category": "Tools"
}


classes = (
    # Panels
    NCT_PT_main_panel,
    # UI Lists
    ACTION_UL_character_actions,
    # Character Controller
    NCT_OT_init_character,
    NCT_OT_load_character,
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
    bpy.types.Scene.novkreed_character_tools = bpy.props.PointerProperty(
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
