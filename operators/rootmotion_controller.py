import bpy
from math import pi
from mathutils import Vector, Quaternion

from bpy.types import Operator

from ..utils import validate_target_armature


def get_all_quaternion_curves(object):
    """returns all quaternion fcurves of object/bones packed together in a touple per object/bone"""
    fcurves = object.animation_data.action.fcurves
    if fcurves.find('rotation_quaternion'):
        yield (fcurves.find('rotation_quaternion', index=0), fcurves.find('rotation_quaternion', index=1), fcurves.find('rotation_quaternion', index=2), fcurves.find('rotation_quaternion', index=3))
    if object.type == 'ARMATURE':
        for bone in object.pose.bones:
            data_path = 'pose.bones["' + bone.name + '"].rotation_quaternion'
            if fcurves.find(data_path):
                yield (fcurves.find(data_path, index=0), fcurves.find(data_path, index=1),fcurves.find(data_path, index=2),fcurves.find(data_path, index=3))


def quaternion_cleanup(object, prevent_flips=True, prevent_inverts=True):
    """fixes signs in quaternion fcurves swapping from one frame to another"""
    for curves in get_all_quaternion_curves(object):
        start = int(min((curves[i].keyframe_points[0].co.x for i in range(4))))
        end = int(max((curves[i].keyframe_points[-1].co.x for i in range(4))))
        for curve in curves:
            for i in range(start, end):
                curve.keyframe_points.insert(i, curve.evaluate(i)).interpolation = 'LINEAR'
        zipped = list(zip(
            curves[0].keyframe_points,
            curves[1].keyframe_points,
            curves[2].keyframe_points,
            curves[3].keyframe_points))
        for i in range(1, len(zipped)):
            if prevent_flips:
                rot_prev = Quaternion((zipped[i-1][j].co.y for j in range(4)))
                rot_cur = Quaternion((zipped[i][j].co.y for j in range(4)))
                diff = rot_prev.rotation_difference(rot_cur)
                if abs(diff.angle - pi) < 0.5:
                    rot_cur.rotate(Quaternion(diff.axis, pi))
                    for j in range(4):
                        zipped[i][j].co.y = rot_cur[j]
            if prevent_inverts:
                change_amount = 0.0
                for j in range(4):
                    change_amount += abs(zipped[i-1][j].co.y - zipped[i][j].co.y)
                if change_amount > 1.0:
                    for j in range(4):
                        zipped[i][j].co.y *= -1.0


class NCT_OT_add_rootbone(Operator):
    bl_idname = "nct.add_rootbone"
    bl_label = "Add Root Bone"
    bl_description = "Adds armature root bone for root motion"

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        target_armature = tool.target_object
        rootmotion_root_name = tool.rootmotion_name
        start_frame = tool.rootmotion_start_frame
        hips_name = tool.rootmotion_hip_bone

        # Bones
        if not hips_name:
            self.report(
                {'ERROR'},
                "No valid hip bone selected.")
            return {'CANCELLED'}

        # Validates Required Bone Exists In Armature
        if len(target_armature.data.bones) > 0:
            context.view_layer.objects.active = target_armature
            current_mode = context.object.mode
            bpy.ops.object.mode_set(mode='EDIT')
            context.view_layer.objects.active = target_armature
            editbones = target_armature.data.edit_bones
            if rootmotion_root_name in editbones:
                self.report({'INFO'}, 'Root Bone Exists.')
                return {'FINISHED'}
            # Bone Setup
            rootmotion_bone = editbones.new(rootmotion_root_name)
            rootmotion_bone.head = (0.0, 0.0, 0.0)
            rootmotion_bone.tail = (0.0, 0.0, 10.0)

            editbones[hips_name].parent = rootmotion_bone

            bpy.ops.object.mode_set(mode="POSE")
            bpy.ops.pose.select_all(action='DESELECT')
            target_armature.data.bones[rootmotion_root_name].select = True
            scene.frame_set(start_frame)
            bpy.ops.anim.keyframe_insert_menu(type='Location')
            bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Bone Added')

        return {'FINISHED'}


class NCT_OT_add_rootmotion(Operator):
    bl_idname = "nct.add_rootmotion"
    bl_label = "Add Root Motion"
    bl_description = "Adds Root Motion to Animations"

    def execute(self, context):
        scene = context.scene
        if not validate_target_armature(scene):
            self.report({'ERROR'}, 'No valid target armature stored.')
            return {'CANCELLED'}

        tool = scene.novkreed_character_tools
        is_rootmotion_all = tool.is_rootmotion_all
        tool = scene.novkreed_character_tools
        target_armature = tool.target_object

        context.view_layer.objects.active = target_armature
        current_mode = context.object.mode

        root_name = tool.rootmotion_name
        is_bone_exists = root_name in target_armature.pose.bones.keys()
        if not is_bone_exists:
            bpy.ops.nct.add_rootbone()

        bpy.ops.object.mode_set(mode='POSE')
        frame_curr = scene.frame_current

        if is_rootmotion_all:
            for action in bpy.data.actions:
                self.bake_rootmotion(
                    scene,
                    tool,
                    target_armature,
                    action
                )
        else:
            idx = tool.selected_action_index
            action = bpy.data.actions[idx]
            self.bake_rootmotion(
                scene,
                tool,
                target_armature,
                action
            )

        scene.frame_set(frame_curr)
        bpy.ops.object.mode_set(mode=current_mode)

        self.report({'INFO'}, 'Root Motion Updated')
        return {'FINISHED'}

    def bake_rootmotion(
        self,
        scene,
        tool,
        target_armature,
        action
    ):
        if not action.get('is_nct_processed') or action.get('has_root_motion'):
            return
        
        hips_name = tool.rootmotion_hip_bone
        root_name = tool.rootmotion_name
        hip_bone = target_armature.pose.bones[hips_name]
        root_bone = target_armature.pose.bones[root_name]

        # Set the scene for curr actions
        start_frame = tool.rootmotion_start_frame
        target_armature.animation_data.action = action
        end_frame = int(target_armature.animation_data.action.frame_range[1])
        scene.frame_end = end_frame

        hip_world_loc = target_armature.matrix_local @ hip_bone.bone.head_local
        z_offset = hip_world_loc[2]

        # Create helper to bake the root motion
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.empty_add(type='ARROWS', radius=1, align='WORLD', location=(0, 0, 0))
        root_baker = bpy.context.object
        root_baker.name = "root_baker"
        root_baker.rotation_mode = 'QUATERNION'

        if tool.rootmotion_use_translation[2]: # use Z axis
            bpy.ops.object.constraint_add(type='COPY_LOCATION')
            bpy.context.object.constraints["Copy Location"].name = "Copy Z_Loc"
            bpy.context.object.constraints["Copy Z_Loc"].target = target_armature
            bpy.context.object.constraints["Copy Z_Loc"].subtarget = hips_name
            bpy.context.object.constraints["Copy Z_Loc"].use_x = False
            bpy.context.object.constraints["Copy Z_Loc"].use_y = False
            bpy.context.object.constraints["Copy Z_Loc"].use_z = True
            bpy.context.object.constraints["Copy Z_Loc"].use_offset = True
            
            root_baker.location[2] = -z_offset
            if tool.rootmotion_on_ground:
                bpy.ops.object.constraint_add(type='LIMIT_LOCATION')
                bpy.context.object.constraints["Limit Location"].use_min_z = True
        
        bpy.ops.object.constraint_add(type='COPY_LOCATION')
        bpy.context.object.constraints["Copy Location"].target = target_armature
        bpy.context.object.constraints["Copy Location"].subtarget = hips_name
        bpy.context.object.constraints["Copy Location"].use_x = tool.rootmotion_use_translation[0]
        bpy.context.object.constraints["Copy Location"].use_y = tool.rootmotion_use_translation[1]
        bpy.context.object.constraints["Copy Location"].use_z = False

        bpy.ops.object.constraint_add(type='COPY_ROTATION')
        bpy.context.object.constraints["Copy Rotation"].target = target_armature
        bpy.context.object.constraints["Copy Rotation"].subtarget = hips_name
        bpy.context.object.constraints["Copy Rotation"].use_y = False
        bpy.context.object.constraints["Copy Rotation"].use_x = False
        bpy.context.object.constraints["Copy Rotation"].use_z = tool.rootmotion_use_rotation

        bpy.ops.nla.bake(frame_start=start_frame, frame_end=end_frame, step=1, only_selected=True, visual_keying=True,
                clear_constraints=True, clear_parents=False, use_current_action=False, bake_types={'OBJECT'})
        
        quaternion_cleanup(root_baker)

        # Create helper to bake hipmotion in Worldspace
        bpy.ops.object.empty_add(type='ARROWS', radius=1, align='WORLD', location=(0, 0, 0))
        hips_baker = bpy.context.object
        hips_baker.name = "hips_baker"
        hips_baker.rotation_mode = 'QUATERNION'

        bpy.ops.object.constraint_add(type='COPY_LOCATION')
        bpy.context.object.constraints["Copy Location"].target = target_armature
        bpy.context.object.constraints["Copy Location"].subtarget = hips_name

        bpy.ops.object.constraint_add(type='COPY_ROTATION')
        bpy.context.object.constraints["Copy Rotation"].target = target_armature
        bpy.context.object.constraints["Copy Rotation"].subtarget = hips_name

        bpy.ops.nla.bake(frame_start=start_frame, frame_end=end_frame, step=1, only_selected=True, visual_keying=True,
                clear_constraints=True, clear_parents=False, use_current_action=False, bake_types={'OBJECT'})
        
        quaternion_cleanup(hips_baker)

        # Select armature
        target_armature.select_set(True)
        root_baker.select_set(False)
        hips_baker.select_set(False)
        bpy.context.view_layer.objects.active = target_armature

        bpy.ops.object.mode_set(mode='POSE')
        root_bone.bone.select = True
        target_armature.data.bones.active = root_bone.bone
        bpy.ops.pose.constraint_add(type='COPY_LOCATION')
        root_bone.constraints["Copy Location"].target = root_baker
        bpy.ops.pose.constraint_add(type='COPY_ROTATION')
        root_bone.constraints["Copy Rotation"].target = root_baker
        root_bone.constraints["Copy Rotation"].use_offset = True

        bpy.ops.nla.bake(frame_start=start_frame, frame_end=end_frame, step=1, only_selected=True, visual_keying=True,
                clear_constraints=True, clear_parents=False, use_current_action=True, bake_types={'POSE'})

        root_bone.bone.select = False
        hip_bone.bone.select = True
        target_armature.data.bones.active = hip_bone.bone

        bpy.ops.pose.constraint_add(type='COPY_LOCATION')
        hip_bone.constraints["Copy Location"].target = hips_baker
        bpy.ops.pose.constraint_add(type='COPY_ROTATION')
        hip_bone.constraints["Copy Rotation"].target = hips_baker

        bpy.ops.nla.bake(frame_start=start_frame, frame_end=end_frame, step=1, only_selected=True, visual_keying=True,
                clear_constraints=True, clear_parents=False, use_current_action=True, bake_types={'POSE'})

        # Delete helpers
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        hips_baker.select_set(True)
        root_baker.select_set(True)

        bpy.data.actions.remove(hips_baker.animation_data.action)
        bpy.data.actions.remove(root_baker.animation_data.action)

        bpy.ops.object.delete(use_global=False)

        action['has_root_motion'] = True
