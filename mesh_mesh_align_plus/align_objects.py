"""Align Objects tool, internals & UI."""


import bpy
import mathutils

import mesh_mesh_align_plus.utils.geom as maplus_geom


class MAPLUS_OT_QuickAlignObjects(bpy.types.Operator):
    bl_idname = "maplus.quickalignobjects"
    bl_label = "Align Objects"
    bl_description = "Align Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not maplus_geom.get_active_object():
            self.report(
                {'ERROR'},
                'Cannot complete: no active object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = maplus_geom.get_active_object().mode

        # Get active (target) transformation matrix components
        active_mat = maplus_geom.get_active_object().matrix_world
        active_trs = [
            mathutils.Matrix.Translation(active_mat.decompose()[0]),
            active_mat.decompose()[1].to_matrix(),
            mathutils.Matrix.Scale(active_mat.decompose()[2][0], 4),
        ]
        active_trs[1].resize_4x4()

        # Copy the transform components from the target to the current object
        selected = [
            item
            for item in bpy.context.scene.objects if maplus_geom.get_select_state(item)
        ]
        for item in selected:
            current_mat = item.matrix_world
            current_trs = [
                mathutils.Matrix.Translation(current_mat.decompose()[0]),
                current_mat.decompose()[1].to_matrix(),
                mathutils.Matrix.Scale(current_mat.decompose()[2][0], 4),
            ]
            current_trs[1].resize_4x4()
            item.matrix_world = (
                active_trs[0] @
                active_trs[1] @
                current_trs[2]
            )

        return {'FINISHED'}


class MAPLUS_PT_QuickAlignObjectsGUI(bpy.types.Panel):
    bl_idname = "MAPLUS_PT_QuickAlignObjectsGUI"
    bl_label = "Quick Align Objects"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mesh Align Plus"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        layout.operator(
                "maplus.quickalignobjects",
                text="Align Objects"
        )
