import bpy

from bl_ui.properties_object import ObjectButtonsPanel
from bpy.types import (UIList, Panel)

from ..utils import validate_target_armature


class NCT_PT_main_panel(Panel, ObjectButtonsPanel):
    bl_idname = "OBJECT_PT_main_panel"
    bl_label = "Novkreed Character Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Character"
    bl_context = "objectmode"

    def draw(self, context):
        # Character Armature
        layout = self.layout
        scene = context.scene
        tool = scene.novkreed_character_tools
        box = layout.box()
        box.label(text="Character Setup", icon='ARMATURE_DATA')
        if not validate_target_armature(scene):
            row = box.row()
            row.scale_y = 2.0
            row.operator("nct.init_character", icon='IMPORT')
            row = box.row()
            row.scale_y = 2.0
            row.operator("nct.load_character", icon='IMPORT')
            return
        else:
            box.operator("nct.join_animations", icon='ASSET_MANAGER')
            box.operator("nct.armature_join_mesh", icon='GROUP_BONE')
        layout.separator()

        character_armature = tool.target_object

        # Animation Utils
        layout.template_list(
            "ACTION_UL_character_actions",
            "nct_character_actions",
            bpy.data,
            "actions",
            tool,
            "selected_action_index"
        )

        if 0 <= tool.selected_action_index < len(bpy.data.actions):
            box = layout.box()
            box.operator("nct.animation_play", icon='PLAY')
            box.operator("nct.animation_stop", icon='PAUSE')
            box.operator("nct.animation_delete", icon='TRASH')

            layout.separator()

            # Trim animation
            box = layout.box()
            box.label(text="Trim Animation", icon='DOCUMENTS')
            box.prop(tool, "trim_animation_from")
            box.prop(tool, "trim_animation_to")
            box.operator("nct.trim_animation", icon="SELECT_SET")

            layout.separator()

            # Rootmotion
            box = layout.box()
            box.label(text="Root Motion Bake", icon='ACTION_TWEAK')
            box.prop(tool, "rootmotion_start_frame")
            box.prop(tool, "rootmotion_use_translation", toggle=True)
            if tool.rootmotion_use_translation[2]:
                box.prop(tool, "rootmotion_on_ground", toggle=True)
            box.prop(tool, "rootmotion_use_rotation", toggle=True)

            box.separator()
            box.column(align=True).prop(tool, "rootmotion_name", text="")
            box.column(align=True).prop_search(
                tool,
                "rootmotion_hip_bone",
                character_armature.data,
                "bones",
                text=""
            )

            box.prop(tool, "is_armature_visible")
            box.prop(tool, "is_rootmotion_all")
            box.separator()
            if tool.rootmotion_hip_bone:
                box.operator("nct.add_rootmotion", icon='BONE_DATA')

        layout.separator()

        # Quick Export
        box = layout.box()
        box.label(text="Quick Export Utils", icon='MESH_MONKEY')
        box.prop(tool, "character_export_character_name")
        box.prop(tool, "character_export_path")
        box.prop(tool, "character_export_format")
        if tool.character_export_path:
            box.operator("nct.character_export", icon='EXPORT')


class ACTION_UL_character_actions(UIList):
    def draw_item(
        self,
        context,
        layout,
        data,
        item,
        icon,
        active_data,
        active_propname,
        index
    ):
        if item.get('is_nct_processed'):
            if item.get('has_root_motion'):
                layout.prop(item, "name", text="Root", emboss=False, icon='ANIM_DATA')
            else:
                layout.prop(item, "name", text="", emboss=False, icon='ANIM_DATA')
        else:
            layout.prop(item, "name", text="Unprocessed", emboss=False, icon='ANIM_DATA')
