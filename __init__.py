import bpy

from bpy.utils import register_class, unregister_class

from .character import (
    NKT_Character,
    NKT_CharacterAction,

    NKT_OT_init_character,
    NKT_OT_load_character,
    NKT_OT_search_character,
    NKT_OT_character_menu,

    NKT_OT_character_quick_export
)
from .rootmotion import (
    NKT_RootmotionSettings,
    NKT_OT_add_rootbone,
    NKT_OT_add_rootmotion
)
from .settings import NKT_Settings
from .animation import (
    NKT_OT_add_character_animation,
    NKT_OT_remove_character_action,
    NKT_OT_load_character_animation,
    NKT_OT_character_action_move,
    NKT_OT_character_push_to_nla,
    NKT_OT_character_actions_menu
)
from .armature import (
    NKT_OT_mixamo_rename_bones,
    NKT_OT_mixamo_prepare_anim_rig
)
from .ui import (
    NKT_PT_toolshelf,
    ACTION_UL_character_actions,
    NKT_PT_character_panel
)


classes = (
    NKT_CharacterAction,
    NKT_Character,
    NKT_RootmotionSettings,
    NKT_Settings,

    NKT_OT_mixamo_rename_bones,
    NKT_OT_mixamo_prepare_anim_rig,

    NKT_OT_init_character,
    NKT_OT_load_character,

    NKT_OT_add_character_animation,
    NKT_OT_remove_character_action,
    NKT_OT_load_character_animation,
    NKT_OT_character_action_move,

    NKT_OT_character_push_to_nla,
    NKT_OT_character_quick_export,

    NKT_OT_add_rootbone,
    NKT_OT_add_rootmotion,

    NKT_OT_search_character,
    NKT_OT_character_menu,
    NKT_OT_character_actions_menu,

    NKT_PT_toolshelf,
    ACTION_UL_character_actions,
    NKT_PT_character_panel,
)

bl_info = {
    "name": "Novkreed Tools",
    "version": (0, 6, 0),
    "blender": (2, 92, 0),
    "location": "3D View > Tools > Novkreed",
    "author": "Pranav S Koundinya",
    "category": "Tools"
}


def register():
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.nkt_settings = bpy.props.PointerProperty(
        type=NKT_Settings,
        name="Novkreed Tool Settings"
    )


def unregister():
    for cls in classes:
        unregister_class(cls)

    del bpy.types.Scene.nkt_settings


if __name__ == "__main__":
    register()
