import bpy
import os

from bpy.types import Operator
from ..utils.armature import validate_target_armature


class NCT_OT_character_export(Operator):
    bl_idname = "nct.character_export"
    bl_label = "Export Character File"
    bl_description = "Exports character."

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        target_armature = tool.target_object
        character_export_format = int(tool.character_export_format)
        if tool.character_export_character_name:
            character_name = tool.character_export_character_name
        else:
            character_name = target_armature.name

        context.view_layer.objects.active = target_armature
        character_export_path = bpy.path.abspath(tool.character_export_path)

        # Generate Filename To Export
        fileName = os.path.join(character_export_path, character_name)

        # GLTF
        if (character_export_format == 0):
            bpy.ops.export_scene.gltf(
                filepath=fileName,
                export_format="GLTF_EMBEDDED",
                export_frame_range=False,
                export_force_sampling=False,
                export_tangents=False,
                export_image_format="PNG",
                export_cameras=False,
                export_lights=False
            )

        # GLB
        if (character_export_format == 1):
            bpy.ops.export_scene.gltf(
                filepath=fileName,
                export_format="GLB",
                export_frame_range=False,
                export_force_sampling=False,
                export_tangents=False,
                export_image_format="PNG",
                export_cameras=False,
                export_lights=False
            )

        self.report({'INFO'}, 'Character File Exported')
        return {'FINISHED'}
