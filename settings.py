import bpy

from bpy.types import PropertyGroup
from bpy.props import EnumProperty, IntProperty, PointerProperty

from .character import NKT_Character
from .rootmotion import NKT_RootmotionSettings


class NKT_Settings(PropertyGroup):
    characters: bpy.props.CollectionProperty(
        type=NKT_Character,
        name="NKT Characters",
        description="The collection of characters that are used in this file."
    )

    def validate_characters(self):
        inds_to_remove = [i for i, c in enumerate(
            self.characters) if not c.armature]
        for i in inds_to_remove:
            self.characters.remove(i)

    def get_active_character(self):
        return self.characters[self.active_character_index]

    def on_active_character_index_updated(self, context):
        self.get_active_character().armature.select_set(True)
        context.view_layer.objects.active = self.get_active_character().armature

    active_character_index: IntProperty(
        name="Active Character Index",
        description="The index of the active character in the collection.",
        update=on_active_character_index_updated
    )

    rootmotion: PointerProperty(
        type=NKT_RootmotionSettings,
        name="Rootmotion Settings"
    )
