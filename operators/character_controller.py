import bpy
import os
import re

from bpy.props import (StringProperty, CollectionProperty)
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from ..utils import (
    push_to_nla_stash,
    validate_target_armature,
    TPOSE_ACTION_NAME,
    MIXAMO_GROUP_NAME
)


def xform_mixamo_action(action, bone_name, scale_to_apply):
    data_path = 'pose.bones[\"{}\"].location'.format(bone_name)

    if len(action.groups) > 0:
        action.groups[0].name = MIXAMO_GROUP_NAME

    for axis in range(3):
        fcurve = action.fcurves.find(data_path, index=axis)
        if fcurve is None:
            continue
        for ind in range(len(fcurve.keyframe_points)):
            fcurve.keyframe_points[ind].co[1] *= scale_to_apply[fcurve.array_index]


def prepare_mixamo_rig(context, armature):
    # Apply transformations on selected Armature
    context.view_layer.objects.active = armature
    current_mode = context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(
        location=True,
        rotation=True,
        scale=True
    )

    # Find the root bones in bone hierarchy
    root_bones = set()
    for bone in armature.data.bones:
        if bone.parent == None:
            root_bones.add(bone)
    
    actions = set()
    actions.add(armature.animation_data.action)
    for track in armature.animation_data.nla_tracks:
        for strip in track.strips:
            actions.add(strip.action)
    
    for bone in root_bones:
        for action in actions:
            xform_mixamo_action(
                action=action,
                bone_name=bone.name,
                scale_to_apply=armature.scale
            )
    bpy.ops.object.mode_set(mode=current_mode)


def rename_bones(armature, remove_namespace_only=False):
    """function for renaming the armature bones to a target skeleton"""
    for bone in armature.pose.bones:
        old_name = bone.name
        new_name = remove_namespace(bone.name)
        if not remove_namespace_only:
            new_name = get_mapped_bone_name(new_name)
        
        bone.name = new_name
        
        for mesh in armature.children:
            for vertex_group in mesh.vertex_groups:
                if vertex_group.name == old_name:
                    vertex_group.name = new_name


def remove_namespace(full_name):
    i = re.search(r"[:_]", full_name[::-1])
    if i:
        return full_name[-(i.start())::]
    else:
        return full_name


def get_mapped_bone_name(in_name):
    schema = {
        'unreal': {
            'root': 'Root',
            'Hips': 'Pelvis',
            'Spine': 'spine_01',
            'Spine1': 'spine_02',
            'Spine2': 'spine_03',
            'LeftShoulder': 'clavicle_l',
            'LeftArm': 'upperarm_l',
            'LeftForeArm': 'lowerarm_l',
            'LeftHand': 'hand_l',
            'RightShoulder': 'clavicle_r',
            'RightArm': 'upperarm_r',
            'RightForeArm': 'lowerarm_r',
            'RightHand': 'hand_r',
            'Neck1': 'neck_01',
            'Neck': 'neck_01',
            'Head': 'head',
            'LeftUpLeg': 'thigh_l',
            'LeftLeg': 'calf_l',
            'LeftFoot': 'foot_l',
            'RightUpLeg': 'thigh_r',
            'RightLeg': 'calf_r',
            'RightFoot': 'foot_r',
            'LeftHandIndex1': 'index_01_l',
            'LeftHandIndex2': 'index_02_l',
            'LeftHandIndex3': 'index_03_l',
            'LeftHandMiddle1': 'middle_01_l',
            'LeftHandMiddle2': 'middle_02_l',
            'LeftHandMiddle3': 'middle_03_l',
            'LeftHandPinky1': 'pinky_01_l',
            'LeftHandPinky2': 'pinky_02_l',
            'LeftHandPinky3': 'pinky_03_l',
            'LeftHandRing1': 'ring_01_l',
            'LeftHandRing2': 'ring_02_l',
            'LeftHandRing3': 'ring_03_l',
            'LeftHandThumb1': 'thumb_01_l',
            'LeftHandThumb2': 'thumb_02_l',
            'LeftHandThumb3': 'thumb_03_l',
            'RightHandIndex1': 'index_01_r',
            'RightHandIndex2': 'index_02_r',
            'RightHandIndex3': 'index_03_r',
            'RightHandMiddle1': 'middle_01_r',
            'RightHandMiddle2': 'middle_02_r',
            'RightHandMiddle3': 'middle_03_r',
            'RightHandPinky1': 'pinky_01_r',
            'RightHandPinky2': 'pinky_02_r',
            'RightHandPinky3': 'pinky_03_r',
            'RightHandRing1': 'ring_01_r',
            'RightHandRing2': 'ring_02_r',
            'RightHandRing3': 'ring_03_r',
            'RightHandThumb1': 'thumb_01_r',
            'RightHandThumb2': 'thumb_02_r',
            'RightHandThumb3': 'thumb_03_r',
            'LeftToeBase': 'ball_l',
            'RightToeBase': 'ball_r'
        }
    }
    new_name = schema['unreal'].get(in_name)
    if new_name:
        return new_name
    else:
        return in_name


class NCT_OT_init_character(Operator):
    bl_idname = "nct.init_character"
    bl_label = "Initialize Character"
    bl_description = (
        "Used to init 'Main' Armature." +
        " The character should have 'T-Pose' animation from Mixamo."
    )
    bl_options = {'REGISTER', 'UNDO'}

    target_name: StringProperty(name="target_armature")

    def execute(self, context):
        scene = context.scene
        tool = scene.novkreed_character_tools
        if self.target_name:
            target_armature = bpy.data.objects[self.target_name]
        else:
            target_armature = context.view_layer.objects.active

        if not target_armature or target_armature.type != 'ARMATURE':
            self.report(
                {'ERROR'}, 
                "The object is not a valid armature."
            )
            return {'CANCELLED'}

        if validate_target_armature(scene):
            self.report(
                {'ERROR'},
                "A character armature exists. Only one can worked per scene."
            )
            return {'CANCELLED'}
        
        target_armature.name = "Armature"
        target_armature.rotation_mode = 'QUATERNION'
        prepare_mixamo_rig(context, target_armature)
        rename_bones(target_armature)

        hipname = ""
        for hipname in ("Hips", "mixamorig:Hips", "mixamorig_Hips", "Pelvis", hipname):
            hips = target_armature.pose.bones.get(hipname)
            if hips != None:
                break
        tool.rootmotion_hip_bone = hipname

        tool.target_object = target_armature
        tpose_action = target_armature.animation_data.action
        tpose_action.name = TPOSE_ACTION_NAME

        # Reset the tpose to 0.
        for bone in target_armature.data.bones:
            data_path = 'pose.bones[\"{}\"].location'.format(bone.name)
            for axis in range(3):
                fcurve = tpose_action.fcurves.find(data_path=data_path, index=axis)
                if fcurve == None:
                    continue
                for ind in range(len(fcurve.keyframe_points)):
                    # Set the pose position of the bone to 0
                    fcurve.keyframe_points[ind].co[1] = 0.0
        
        tpose_action['is_nct_processed'] = True
        push_to_nla_stash(armature=target_armature, action=tpose_action)

        # Update list index
        tool.selected_action_index = bpy.data.actions.find(TPOSE_ACTION_NAME)
        target_armature.animation_data.action = tpose_action

        if len(tpose_action.frame_range) > 0:
            context.scene.frame_end = tpose_action.frame_range[1]

        self.report({'INFO'}, "Character Initialized.")
        return {'FINISHED'}


class NCT_OT_load_character(Operator, ImportHelper):
    bl_idname = "nct.load_character"
    bl_label = "Load Character"
    bl_description = (
        "Used to load and init 'Main' Armature." +
        " Loaded character should have 'T-Pose' animation from Mixamo."
    )
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
        scene = context.scene
        tool = scene.novkreed_character_tools
        if validate_target_armature(scene):
            self.report(
                {'ERROR'},
                "A character armature exists. Only one can worked per scene."
            )
            return {'CANCELLED'}

        self.report({'INFO'}, "Loading Character T-Pose")
        bpy.ops.import_scene.fbx(
            filepath=self.filepath,
            axis_forward='-Z',
            axis_up='Y',
            bake_space_transform=False,
            use_custom_normals=True,
            use_image_search=True,
            use_alpha_decals=False, decal_offset=0.0,
            use_anim=True, anim_offset=1.0,
            use_custom_props=True,
            use_custom_props_enum_as_string=True,
            force_connect_children=False,
            ignore_leaf_bones=True,
            automatic_bone_orientation=True,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_prepost_rot=True
        )

        imported_objs = context.selected_objects
        target_armature = next(
            (obj for obj in imported_objs if obj.type == 'ARMATURE'),
            None
        )
        if target_armature is None:
            self.report(
                {'ERROR'},
                "Imported character is not valid. No armature found"
            )
            bpy.ops.object.delete({'selected_objects': imported_objs})
            return {'CANCELLED'}
        
        bpy.ops.nct.init_character(target_name=target_armature.name)
        return {'FINISHED'}
        

class NCT_OT_join_animations(Operator, ImportHelper):
    bl_idname = "nct.join_animations"
    bl_label = "Join Animations"
    bl_description = "Join mixamo animations into a single armature"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})
    files: CollectionProperty(type=bpy.types.OperatorFileListElement)
    directory: StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        tool = context.scene.novkreed_character_tools
        target_armature = tool.target_object
        remove_list = []
        # Debug
        remove_imports = True

        if not validate_target_armature(context.scene):
            self.report({'ERROR'}, "No valid target armature stored.")
            return {'CANCELLED'}

        if len(self.files) <= 0:
            self.report({'ERROR'}, "No files provided.")
            return {'CANCELLED'}

        for file in self.files:
            filename = file.name
            file_basename = os.path.basename(filename)
            action_name, ext = os.path.splitext(file_basename)

            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, "Action: {}".format(action_name))

            if action_name == TPOSE_ACTION_NAME:
                continue

            if (hasattr(bpy.types, bpy.ops.import_scene.fbx.idname())):
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
                        {'INFO'},
                        "Imported animation is not valid. No armature found " +
                        "in {}".format(filename)
                    )
                    bpy.ops.object.delete({'selected_objects': imported_objs})
                    continue

                remove_list.extend(imported_objs)

                prepare_mixamo_rig(context, imported_armature)
                rename_bones(imported_armature)
                imported_action = imported_armature.animation_data.action
                imported_action.name = action_name
                imported_action['is_nct_processed'] = True

                push_to_nla_stash(
                    armature=target_armature,
                    action=imported_action
                )

        # Delete Imported Armatures
        if remove_imports:
            bpy.ops.object.delete({"selected_objects": remove_list})
            context.view_layer.objects.active = target_armature

        # Remove Cleared Keyframe Actions - Mixamo Fix
        bpy.ops.anim.clear_useless_actions(only_unused=False)

        # Reset active action to TPose
        tool.selected_action_index = bpy.data.actions.find(TPOSE_ACTION_NAME)
        target_armature.animation_data.action = \
            bpy.data.actions[TPOSE_ACTION_NAME]

        self.report({'INFO'}, "Animations Imported Successfully")
        return {'FINISHED'}


class NCT_OT_armature_join_mesh(Operator):
    bl_idname = "nct.armature_join_mesh"
    bl_label = "Join Armature Meshes"
    bl_description = "Join every children mesh of armature into single object"

    def execute(self, context):
        scene = context.scene
        tool = scene.novkreed_character_tools
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        target_armature = tool.target_object
        context.view_layer.objects.active = target_armature
        current_mode = context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh_to_join = None
        for mesh in target_armature.children:
            if mesh.type == 'MESH':
                mesh.select_set(True)
                mesh_to_join = mesh

        if mesh_to_join:
            context.view_layer.objects.active = mesh_to_join
            bpy.ops.object.join()
            body_mesh = context.view_layer.objects.active
            body_mesh.name = "Mesh"
            self.report({'INFO'}, 'Armature Meshes Joined')

        bpy.ops.object.mode_set(mode=current_mode)

        return {'FINISHED'}
