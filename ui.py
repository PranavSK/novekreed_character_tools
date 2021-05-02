from bpy.types import UILayout, UIList, Panel


class NKT_PT_toolshelf(Panel):
    bl_label = "Novkreed Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Novkreed"
    bl_context = "objectmode"

    def draw(self, context):
        pass


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
        rootmotion_icon = UILayout.enum_item_icon(
            item, 'rootmotion_type', item.rootmotion_type)
        layout.prop(data=item, property='name', emboss=False,
                    text="", icon_value=rootmotion_icon)


class NKT_PT_character_panel(Panel):
    bl_label = "Character"
    bl_parent_id = 'NKT_PT_toolshelf'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        settings = context.scene.nkt_settings
        settings.validate_characters()

        layout = self.layout
        layout.operator_menu_enum(
            operator='nkt.character_menu',
            property='menu_options',
            icon='COMMUNITY'
        )

        if len(settings.characters) == 0:
            return

        character = settings.get_active_character()
        if character is None:
            return

        layout.prop(
            data=character,
            property='name',
            text="",
            icon='ARMATURE_DATA'
        )

        layout.separator()

        column = layout.column(align=True)
        column.label(text="Character Actions", icon='ANIM')
        column.template_list(
            listtype_name='ACTION_UL_character_actions',
            list_id='nkt_active_character_actions',
            dataptr=character,
            propname='actions',
            active_dataptr=character,
            active_propname='active_action_index'
        )
        row = column.row(align=True)
        row.operator_enum(
            operator='nkt.character_actions_menu',
            property='menu_options',
            # icon='ANIM'
            icon_only=True
        )

        if len(character.actions) == 0:
            return

        if character.get_active_action():
            layout.separator()
            # layout.label(text="No active action selected.")
            box = layout.box()
            box.label(text="Root Motion Bake", icon='ACTION_TWEAK')
            box.prop(settings.rootmotion, 'start_frame')
            box.prop(settings.rootmotion, 'use_translation', toggle=True)
            if settings.rootmotion.use_translation[2]:
                box.prop(settings.rootmotion, 'on_ground', toggle=True)
            box.prop(settings.rootmotion, 'use_rotation', toggle=True)

            box.separator()
            column = box.column(align=True)
            column.prop(character, 'root_bone_name', text="")
            column.prop_search(
                data=character,
                property='hip_bone_name',
                search_data=character.armature.data,
                search_property='bones',
                text=""
            )
            box.operator(
                operator='nkt.character_add_rootmotion', icon='BONE_DATA')

        layout.separator()

        box = layout.box()
        box.label(text="Quick Export Utils", icon='MESH_MONKEY')
        box.prop(character, 'export_name')
        box.prop(character, 'export_path')
        box.prop(character, 'export_format')
        if character.export_path and character.export_name:
            box.operator("nkt.character_quick_export", icon='EXPORT')
