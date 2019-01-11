"""Coordinate retrieval, modification and display functionality."""


import collections

import bmesh
import bpy
import mathutils

import mesh_mesh_align_plus.utils.exceptions as maplus_except


def set_item_coords(item, coords_to_set, coords):
    target_data = collections.OrderedDict(
        zip(coords_to_set, coords)
    )
    for key, val in target_data.items():
        setattr(item, key, val)
    return True


def scale_mat_from_vec(vec):
    return (
        mathutils.Matrix.Scale(
            vec[0],
            4,
            mathutils.Vector((1, 0.0, 0.0))
        ) @
        mathutils.Matrix.Scale(
            vec[1],
            4,
            mathutils.Vector((0.0, 1, 0.0))
        ) @
        mathutils.Matrix.Scale(
            vec[2],
            4,
            mathutils.Vector((0.0, 0.0, 1))
        )
    )


def return_selected_verts(mesh_object,
                          verts_to_grab,
                          global_matrix_multiplier=None):
    if type(mesh_object.data) == bpy.types.Mesh:

        # Todo, check for a better way to handle/if this is needed
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()

        # Init source mesh
        src_mesh = bmesh.new()
        src_mesh.from_mesh(mesh_object.data)
        src_mesh.select_history.validate()

        history_indices = []
        history_as_verts = []
        for element in src_mesh.select_history:
            if len(history_as_verts) == verts_to_grab:
                break
            if type(element) == bmesh.types.BMVert:
                if not (element.index in history_indices):
                    history_as_verts.append(element)
            else:
                for item in element.verts:
                    if len(history_as_verts) == verts_to_grab:
                        break
                    if not (item.index in history_indices):
                        history_as_verts.append(item)

        selection = []
        vert_indices = []
        for vert in history_as_verts:
            if len(selection) == verts_to_grab:
                break
            coords = vert.co
            if global_matrix_multiplier:
                coords = global_matrix_multiplier @ coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)

        for vert in (v for v in src_mesh.verts if v.select):
            if len(selection) == verts_to_grab:
                break
            coords = vert.co
            if global_matrix_multiplier:
                coords = global_matrix_multiplier @ coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)

        if len(selection) == verts_to_grab:
            return selection
        else:
            raise maplus_except.InsufficientSelectionError()
    else:
        raise maplus_except.NonMeshGrabError(mesh_object)


def return_normal_coords(mesh_object,
                         global_matrix_multiplier=None):
    if type(mesh_object.data) == bpy.types.Mesh:

        # Todo, check for a better way to handle/if this is needed
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()

        # Init source mesh
        src_mesh = bmesh.new()
        src_mesh.from_mesh(mesh_object.data)
        src_mesh.select_history.validate()

        face_elems = []
        face_indices = []
        normal = []
        for element in src_mesh.select_history:
            if type(element) == bmesh.types.BMFace:
                face_elems.append(element)
                face_indices.append(element.index)
                break

        for face in (f for f in src_mesh.faces if f.select):
            if not (face.index in face_indices):
                face_elems.append(face)
                break

        if not face_elems:
            # Todo, make proper exception or modify old
            raise maplus_except.InsufficientSelectionError()
        if global_matrix_multiplier:
            face_normal_origin = (
                global_matrix_multiplier @
                face_elems[0].calc_center_median()
            )
            face_normal_endpoint = (
                global_matrix_multiplier @
                (face_elems[0].calc_center_median() + face_elems[0].normal)
            )
        else:
            face_normal_origin = face_elems[0].calc_center_median()
            face_normal_endpoint = face_normal_origin + face_elems[0].normal

        normal.extend(
            [face_normal_origin,
             face_normal_endpoint]
        )
        return normal

    else:
        raise maplus_except.NonMeshGrabError(mesh_object)


def return_avg_vert_pos(mesh_object,
                        global_matrix_multiplier=None):
    if type(mesh_object.data) == bpy.types.Mesh:

        # Todo, check for a better way to handle/if this is needed
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()

        # Init source mesh
        src_mesh = bmesh.new()
        src_mesh.from_mesh(mesh_object.data)

        selection = []
        vert_indices = []
        # for vert in (v for v in src_mesh.verts if v.select):
        for vert in (v for v in src_mesh.verts if v.select):
            coords = vert.co
            if global_matrix_multiplier:
                coords = global_matrix_multiplier @ coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)

        if len(selection) > 0:
            average_position = mathutils.Vector((0, 0, 0))
            for item in selection:
                average_position += item
            average_position /= len(selection)
            return [average_position]
        else:
            raise maplus_except.InsufficientSelectionError()
    else:
        raise maplus_except.NonMeshGrabError(mesh_object)


# For the ambiguous "internal storage slots", which can be any geom type in
# [POINT, LINE, PLANE]. Must return at least 1 selected vert (for a point).
def return_at_least_one_selected_vert(mesh_object,
                                      global_matrix_multiplier=None):
    if type(mesh_object.data) == bpy.types.Mesh:

        # Todo, check for a better way to handle/if this is needed
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()

        # Init source mesh
        src_mesh = bmesh.new()
        src_mesh.from_mesh(mesh_object.data)
        src_mesh.select_history.validate()

        history_indices = []
        history_as_verts = []
        for element in src_mesh.select_history:
            if len(history_as_verts) == 3:
                break
            if type(element) == bmesh.types.BMVert:
                if not (element.index in history_indices):
                    history_as_verts.append(element)
            else:
                for item in element.verts:
                    if len(history_as_verts) == 3:
                        break
                    if not (item.index in history_indices):
                        history_as_verts.append(item)

        selection = []
        vert_indices = []
        for vert in history_as_verts:
            if len(selection) == 3:
                break
            coords = vert.co
            if global_matrix_multiplier:
                coords = global_matrix_multiplier @ coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)
        for vert in (v for v in src_mesh.verts if v.select):
            if len(selection) == 3:
                break
            coords = vert.co
            if global_matrix_multiplier:
                coords = global_matrix_multiplier @ coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)

        if len(selection) > 0:
            return selection
        else:
            raise maplus_except.InsufficientSelectionError()
    else:
        raise maplus_except.NonMeshGrabError(mesh_object)


# Coordinate grabber, present on all geometry primitives (point, line, plane)
# Todo, design decision: error on too many selected verts or *no*?
class MAPLUS_OT_GrabFromGeometryBase(bpy.types.Operator):
    bl_idname = "maplus.grabfromgeometrybase"
    bl_label = "Grab From Geometry Base Class"
    bl_description = (
        "The base class for grabbing point coords from mesh verts."
    )
    bl_options = {'REGISTER', 'UNDO'}
    # For grabbing global coords
    multiply_by_world_matrix = None
    # A tuple of attribute names (strings) that should be set on the maplus
    # primitive (point, line or plane item). The length of this tuple
    # determines how many verts will be grabbed.
    vert_attribs_to_set = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if not hasattr(self, "quick_op_target"):
            active_item = prims[addon_data.active_list_item]
        else:
            if self.quick_op_target == "APTSRC":
                active_item = addon_data.quick_align_pts_src
            elif self.quick_op_target == "APTDEST":
                active_item = addon_data.quick_align_pts_dest

            elif self.quick_op_target == "DSSRC":
                active_item = addon_data.quick_directional_slide_src

            elif self.quick_op_target == "SMESRC":
                active_item = addon_data.quick_scale_match_edge_src
            elif self.quick_op_target == "SMEDEST":
                active_item = addon_data.quick_scale_match_edge_dest

            elif self.quick_op_target == "ALNSRC":
                active_item = addon_data.quick_align_lines_src
            elif self.quick_op_target == "ALNDEST":
                active_item = addon_data.quick_align_lines_dest

            elif self.quick_op_target == "AXRSRC":
                active_item = addon_data.quick_axis_rotate_src

            elif self.quick_op_target == "APLSRC":
                active_item = addon_data.quick_align_planes_src
            elif self.quick_op_target == "APLDEST":
                active_item = addon_data.quick_align_planes_dest

            elif self.quick_op_target == "SLOT1":
                active_item = addon_data.internal_storage_slot_1
            elif self.quick_op_target == "SLOT2":
                active_item = addon_data.internal_storage_slot_2
            elif self.quick_op_target == "CALCRESULT":
                active_item = addon_data.quick_calc_result_item

        matrix_multiplier = None
        if self.multiply_by_world_matrix:
            matrix_multiplier = get_active_object().matrix_world
        try:
            vert_data = return_selected_verts(
                get_active_object(),
                len(self.vert_attribs_to_set),
                matrix_multiplier
            )
        except maplus_except.InsufficientSelectionError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except maplus_except.NonMeshGrabError:
            self.report(
                {'ERROR'},
                'Cannot grab coords: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        set_item_coords(active_item, self.vert_attribs_to_set, vert_data)

        return {'FINISHED'}


class MAPLUS_OT_GrabSmeNumeric(bpy.types.Operator):
    bl_idname = "maplus.grabsmenumeric"
    bl_label = "Grab Target"
    bl_description = (
        "Grab target for scale match edge numeric mode."
    )
    bl_options = {'REGISTER', 'UNDO'}
    # For grabbing global coords
    multiply_by_world_matrix = True
    # A tuple of attribute names (strings) that should be set on the maplus
    # primitive (point, line or plane item). The length of this tuple
    # determines how many verts will be grabbed.
    vert_attribs_to_set = ('line_start', 'line_end')

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data

        matrix_multiplier = None
        if self.multiply_by_world_matrix:
            matrix_multiplier = get_active_object().matrix_world
        try:
            vert_data = return_selected_verts(
                get_active_object(),
                len(self.vert_attribs_to_set),
                matrix_multiplier
            )
        except maplus_except.InsufficientSelectionError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except maplus_except.NonMeshGrabError:
            self.report(
                {'ERROR'},
                'Cannot grab coords: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        set_item_coords(
            addon_data.quick_sme_numeric_src,
            self.vert_attribs_to_set,
            vert_data
        )
        set_item_coords(
            addon_data.quick_sme_numeric_dest,
            self.vert_attribs_to_set,
            vert_data
        )

        return {'FINISHED'}


class MAPLUS_OT_GrabAndSetItemKindBase(bpy.types.Operator):
    bl_idname = "maplus.grabandsetitemkindbase"
    bl_label = "Grab and Set Item Base Class"
    bl_description = (
        "The base class for grabbing coords and setting item kind"
        " based on the number of selected verts."
    )
    bl_options = {'REGISTER', 'UNDO'}
    # For grabbing global coords
    multiply_by_world_matrix = None
    # A tuple of attribute names (strings) that should be set on the maplus
    # primitive (point, line or plane item). The length of this tuple
    # determines how many verts will be grabbed.
    vert_attribs_to_set = None
    target = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        if self.target == "SLOT1":
            active_item = addon_data.internal_storage_slot_1
        elif self.target == "SLOT2":
            active_item = addon_data.internal_storage_slot_2
        elif self.target == "CALCRESULT":
            active_item = addon_data.quick_calc_result_item

        matrix_multiplier = None
        if self.multiply_by_world_matrix:
            matrix_multiplier = get_active_object().matrix_world
        try:
            vert_data = return_at_least_one_selected_vert(
                get_active_object(),
                matrix_multiplier
            )
        except maplus_except.InsufficientSelectionError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except maplus_except.NonMeshGrabError:
            self.report(
                {'ERROR'},
                'Cannot grab coords: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        if len(vert_data) == 1:
            active_item.kind = 'POINT'
            vert_attribs_to_set = ('point',)
        elif len(vert_data) == 2:
            active_item.kind = 'LINE'
            vert_attribs_to_set = ('line_start', 'line_end')
        elif len(vert_data) == 3:
            active_item.kind = 'PLANE'
            vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')

        set_item_coords(active_item, vert_attribs_to_set, vert_data)

        return {'FINISHED'}


class MAPLUS_OT_GrabAverageLocationBase(bpy.types.Operator):
    bl_idname = "maplus.grabaveragelocationbase"
    bl_label = "Grab Average Location Base Class"
    bl_description = (
        "The base class for grabbing average point coords from mesh verts."
    )
    bl_options = {'REGISTER', 'UNDO'}
    # For grabbing global coords
    multiply_by_world_matrix = None
    # A tuple of attribute names (strings) that should be set on the maplus
    # primitive (point, line or plane item). The length of this tuple
    # determines how many verts will be grabbed.
    vert_attribs_to_set = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if not hasattr(self, "quick_op_target"):
            active_item = prims[addon_data.active_list_item]
        else:
            if self.quick_op_target == "APTSRC":
                active_item = addon_data.quick_align_pts_src
            elif self.quick_op_target == "APTDEST":
                active_item = addon_data.quick_align_pts_dest

            elif self.quick_op_target == "DSSRC":
                active_item = addon_data.quick_directional_slide_src

            elif self.quick_op_target == "SMESRC":
                active_item = addon_data.quick_scale_match_edge_src
            elif self.quick_op_target == "SMEDEST":
                active_item = addon_data.quick_scale_match_edge_dest

            elif self.quick_op_target == "ALNSRC":
                active_item = addon_data.quick_align_lines_src
            elif self.quick_op_target == "ALNDEST":
                active_item = addon_data.quick_align_lines_dest

            elif self.quick_op_target == "AXRSRC":
                active_item = addon_data.quick_axis_rotate_src

            elif self.quick_op_target == "APLSRC":
                active_item = addon_data.quick_align_planes_src
            elif self.quick_op_target == "APLDEST":
                active_item = addon_data.quick_align_planes_dest

            elif self.quick_op_target == "SLOT1":
                active_item = addon_data.internal_storage_slot_1
            elif self.quick_op_target == "SLOT2":
                active_item = addon_data.internal_storage_slot_2
            elif self.quick_op_target == "CALCRESULT":
                active_item = addon_data.quick_calc_result_item

        matrix_multiplier = None
        if self.multiply_by_world_matrix:
            matrix_multiplier = get_active_object().matrix_world
        try:
            vert_data = return_avg_vert_pos(
                get_active_object(),
                matrix_multiplier
            )
        except maplus_except.InsufficientSelectionError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except maplus_except.NonMeshGrabError:
            self.report(
                {'ERROR'},
                'Cannot grab coords: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        set_item_coords(active_item, self.vert_attribs_to_set, vert_data)

        return {'FINISHED'}


class MAPLUS_OT_GrabNormalBase(bpy.types.Operator):
    bl_idname = "maplus.grabnormalbase"
    bl_label = "Grab Normal Base Class"
    bl_description = (
        "The base class for grabbing normal coords from a selected face."
    )
    bl_options = {'REGISTER', 'UNDO'}
    # For grabbing global coords
    multiply_by_world_matrix = None
    # A tuple of attribute names (strings) that should be set on the maplus
    # primitive (point, line or plane item). The length of this tuple
    # determines how many verts will be grabbed.
    vert_attribs_to_set = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if not hasattr(self, "quick_op_target"):
            active_item = prims[addon_data.active_list_item]
        else:
            if self.quick_op_target == "DSSRC":
                active_item = addon_data.quick_directional_slide_src

            elif self.quick_op_target == "SMESRC":
                active_item = addon_data.quick_scale_match_edge_src
            elif self.quick_op_target == "SMEDEST":
                active_item = addon_data.quick_scale_match_edge_dest

            elif self.quick_op_target == "ALNSRC":
                active_item = addon_data.quick_align_lines_src
            elif self.quick_op_target == "ALNDEST":
                active_item = addon_data.quick_align_lines_dest

            elif self.quick_op_target == "AXRSRC":
                active_item = addon_data.quick_axis_rotate_src

            elif self.quick_op_target == "SLOT1":
                active_item = addon_data.internal_storage_slot_1
            elif self.quick_op_target == "SLOT2":
                active_item = addon_data.internal_storage_slot_2
            elif self.quick_op_target == "CALCRESULT":
                active_item = addon_data.quick_calc_result_item

        matrix_multiplier = None
        if self.multiply_by_world_matrix:
            matrix_multiplier = get_active_object().matrix_world
        try:
            vert_data = return_normal_coords(
                get_active_object(),
                matrix_multiplier
            )
        except maplus_except.InsufficientSelectionError:
            self.report(
                {'ERROR'},
                'Select at least one face to grab a face normal.'
            )
            return {'CANCELLED'}
        except maplus_except.NonMeshGrabError:
            self.report(
                {'ERROR'},
                'Cannot grab coords: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        set_item_coords(active_item, self.vert_attribs_to_set, vert_data)

        return {'FINISHED'}


# Coordinate grabber, present on all geometry primitives (point, line, plane)
class MAPLUS_OT_GrabFromCursorBase(bpy.types.Operator):
    bl_idname = "maplus.grabfromcursorbase"
    bl_label = "Grab From Cursor Base Class"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    # String name of (single coordinate) attribute
    vert_attrib_to_set = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, "quick_op_target"):
            if self.quick_op_target == "APTSRC":
                active_item = addon_data.quick_align_pts_src
            elif self.quick_op_target == "APTDEST":
                active_item = addon_data.quick_align_pts_dest

            elif self.quick_op_target == "DSSRC":
                active_item = addon_data.quick_directional_slide_src

            elif self.quick_op_target == "SMESRC":
                active_item = addon_data.quick_scale_match_edge_src
            elif self.quick_op_target == "SMEDEST":
                active_item = addon_data.quick_scale_match_edge_dest

            elif self.quick_op_target == "ALNSRC":
                active_item = addon_data.quick_align_lines_src
            elif self.quick_op_target == "ALNDEST":
                active_item = addon_data.quick_align_lines_dest

            elif self.quick_op_target == "AXRSRC":
                active_item = addon_data.quick_axis_rotate_src

            elif self.quick_op_target == "APLSRC":
                active_item = addon_data.quick_align_planes_src
            elif self.quick_op_target == "APLDEST":
                active_item = addon_data.quick_align_planes_dest

            elif self.quick_op_target == "SLOT1":
                active_item = addon_data.internal_storage_slot_1
            elif self.quick_op_target == "SLOT2":
                active_item = addon_data.internal_storage_slot_2
            elif self.quick_op_target == "CALCRESULT":
                active_item = addon_data.quick_calc_result_item

        else:
            active_item = prims[addon_data.active_list_item]

        setattr(
            active_item,
            self.vert_attrib_to_set,
            bpy.context.scene.cursor_location
        )
        return {'FINISHED'}


# Coordinate sender, present on all geometry primitives (point, line, plane)
class MAPLUS_OT_SendCoordToCursorBase(bpy.types.Operator):
    bl_idname = "maplus.sendcoordtocursorbase"
    bl_label = "Send Coord to Cursor Base Class"
    bl_description = "The base class for sending coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    # String name of the primitive attrib to pull coord data from
    source_coord_attrib = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        if hasattr(self, "quick_op_target"):
            if self.quick_op_target == "APTSRC":
                active_item = addon_data.quick_align_pts_src
            elif self.quick_op_target == "APTDEST":
                active_item = addon_data.quick_align_pts_dest

            elif self.quick_op_target == "DSSRC":
                active_item = addon_data.quick_directional_slide_src

            elif self.quick_op_target == "SMESRC":
                active_item = addon_data.quick_scale_match_edge_src
            elif self.quick_op_target == "SMEDEST":
                active_item = addon_data.quick_scale_match_edge_dest

            elif self.quick_op_target == "ALNSRC":
                active_item = addon_data.quick_align_lines_src
            elif self.quick_op_target == "ALNDEST":
                active_item = addon_data.quick_align_lines_dest

            elif self.quick_op_target == "AXRSRC":
                active_item = addon_data.quick_axis_rotate_src

            elif self.quick_op_target == "APLSRC":
                active_item = addon_data.quick_align_planes_src
            elif self.quick_op_target == "APLDEST":
                active_item = addon_data.quick_align_planes_dest

            elif self.quick_op_target == "SLOT1":
                active_item = addon_data.internal_storage_slot_1
            elif self.quick_op_target == "SLOT2":
                active_item = addon_data.internal_storage_slot_2
            elif self.quick_op_target == "CALCRESULT":
                active_item = addon_data.quick_calc_result_item

        else:
            active_item = prims[addon_data.active_list_item]

        bpy.context.scene.cursor_location = getattr(
            active_item,
            self.source_coord_attrib
        )
        return {'FINISHED'}


class MAPLUS_OT_GrabAllSlot1(MAPLUS_OT_GrabAndSetItemKindBase):
    bl_idname = "maplus.graballslot1"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = True
    target = 'SLOT1'


class MAPLUS_OT_GrabAllSlot1Loc(MAPLUS_OT_GrabAndSetItemKindBase):
    bl_idname = "maplus.graballslot1loc"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = False
    target = 'SLOT1'


class MAPLUS_OT_GrabAllSlot2(MAPLUS_OT_GrabAndSetItemKindBase):
    bl_idname = "maplus.graballslot2"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = True
    target = 'SLOT2'


class MAPLUS_OT_GrabAllSlot2Loc(MAPLUS_OT_GrabAndSetItemKindBase):
    bl_idname = "maplus.graballslot2loc"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = False
    target = 'SLOT2'


class MAPLUS_OT_GrabAllCalcResult(MAPLUS_OT_GrabAndSetItemKindBase):
    bl_idname = "maplus.graballcalcresult"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = True
    target = 'CALCRESULT'


class MAPLUS_OT_GrabPointFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.grabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'


class MAPLUS_OT_Slot1GrabPointFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot1grabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = "SLOT1"


class MAPLUS_OT_Slot2GrabPointFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot2grabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = "SLOT2"


class MAPLUS_OT_CalcResultGrabPointFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_QuickAptSrcGrabPointFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickaptsrcgrabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = 'APTSRC'


class MAPLUS_OT_QuickAptDestGrabPointFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickaptdestgrabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = 'APTDEST'


class MAPLUS_OT_GrabPointFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabpointfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False


class MAPLUS_OT_GrabPointFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabpointfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True


class MAPLUS_OT_GrabPointSlot1(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabpointslot1"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_GrabPointSlot1Loc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabpointslot1loc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "SLOT1"


class MAPLUS_OT_GrabPointCalcResult(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabpointcalcresult"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_GrabPointCalcResultLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabpointcalcresultloc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_GrabPointSlot2(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabpointslot2"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_GrabPointSlot2Loc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabpointslot2loc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "SLOT2"


class MAPLUS_OT_PointGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.pointgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True


class MAPLUS_OT_LineStartGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.linestartgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True


class MAPLUS_OT_LineEndGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.lineendgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True


class MAPLUS_OT_PlaneAGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.planeagrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True


class MAPLUS_OT_PlaneBGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.planebgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True


class MAPLUS_OT_PlaneCGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.planecgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True


class MAPLUS_OT_Slot1PointGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot1pointgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_Slot2PointGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot2pointgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_CalcResultPointGrabAvg(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.calcresultpointgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_QuickAptGrabAvgSrc(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaptgrabavgsrc"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "APTSRC"


class MAPLUS_OT_QuickAptGrabAvgDest(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaptgrabavgdest"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "APTDEST"


class MAPLUS_OT_QuickAlignPointsGrabSrc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignpointsgrabsrc"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "APTSRC"


class MAPLUS_OT_QuickAlignPointsGrabDest(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignpointsgrabdest"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "APTDEST"


class MAPLUS_OT_QuickAlignPointsGrabSrcLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignpointsgrabsrcloc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "APTSRC"


class MAPLUS_OT_QuickAlignPointsGrabDestLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignpointsgrabdestloc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "APTDEST"


class MAPLUS_OT_SendPointToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.sendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'


class MAPLUS_OT_Slot1SendPointToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2SendPointToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultSendPointToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_QuickAptSrcSendPointToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickaptsrcsendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'APTSRC'


class MAPLUS_OT_QuickAptDestSendPointToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickaptdestsendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'APTDEST'


class MAPLUS_OT_GrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.grablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'


class MAPLUS_OT_Slot1GrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot1grablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot1grablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2GrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot2grablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot2grablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultGrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_QuickAlnSrcGrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickalnsrcgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnDestGrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickalndestgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAxrSrcGrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickaxrsrcgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickDsSrcGrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickdssrcgrablinestartfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickDsDestGrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickdsdestgrablinestartfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'DSDEST'


class MAPLUS_OT_QuickSmeSrcGrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quicksmesrcgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeDestGrabLineStartFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quicksmedestgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_GrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False


class MAPLUS_OT_GrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True


class MAPLUS_OT_Slot1GrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2GrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultGrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_Slot1GrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2GrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultGrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_Slot1GrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2GrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultGrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_Slot1GrabAvgLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavglinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_Slot2GrabAvgLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavglinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_CalcResultGrabAvgLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavglinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_Slot1GrabAvgLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavglineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_Slot2GrabAvgLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavglineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_CalcResultGrabAvgLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavglineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_QuickAlnGrabAvgSrcLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickalngrabavgsrclinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "ALNSRC"


class MAPLUS_OT_QuickAlnGrabAvgDestLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickalngrabavgdestlinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "ALNDEST"


class MAPLUS_OT_QuickAlnGrabAvgSrcLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickalngrabavgsrclineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "ALNSRC"


class MAPLUS_OT_QuickAlnGrabAvgDestLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickalngrabavgdestlineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "ALNDEST"


class MAPLUS_OT_QuickAxrGrabAvgSrcLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaxrgrabavgsrclinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "AXRSRC"


class MAPLUS_OT_QuickAxrGrabAvgSrcLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaxrgrabavgsrclineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "AXRSRC"


class MAPLUS_OT_QuickDsGrabAvgSrcLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickdsgrabavgsrclinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "DSSRC"


class MAPLUS_OT_QuickDsGrabAvgSrcLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickdsgrabavgsrclineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "DSSRC"


class MAPLUS_OT_QuickSmeGrabAvgSrcLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quicksmegrabavgsrclinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "SMESRC"


class MAPLUS_OT_QuickSmeGrabAvgDestLineStart(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quicksmegrabavgdestlinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "SMEDEST"


class MAPLUS_OT_QuickSmeGrabAvgSrcLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quicksmegrabavgsrclineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "SMESRC"


class MAPLUS_OT_QuickSmeGrabAvgDestLineEnd(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quicksmegrabavgdestlineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "SMEDEST"


class MAPLUS_OT_QuickAlnSrcGrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalnsrcgrablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnSrcGrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalnsrcgrablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnDestGrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalndestgrablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAlnDestGrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalndestgrablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAxrSrcGrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaxrsrcgrablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickAxrSrcGrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaxrsrcgrablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickDsSrcGrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdssrcgrablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickDsSrcGrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdssrcgrablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickDsDestGrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdsdestgrablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'DSDEST'


class MAPLUS_OT_QuickDsDestGrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdsdestgrablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'DSDEST'


class MAPLUS_OT_QuickSmeSrcGrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quicksmesrcgrablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeSrcGrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quicksmesrcgrablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeDestGrabLineStartFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quicksmedestgrablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_QuickSmeDestGrabLineStartFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quicksmedestgrablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_SendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.sendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'


class MAPLUS_OT_Slot1SendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1SendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendlineendtocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2SendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2SendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendlineendtocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultSendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultSendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_QuickAlnSrcSendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickalnsrcsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnDestSendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickalndestsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAxrSrcSendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickaxrsrcsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickDsSrcSendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickdssrcsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickDsDestSendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickdsdestsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'DSDEST'


class MAPLUS_OT_QuickSmeSrcSendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quicksmesrcsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeDestSendLineStartToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quicksmedestsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_GrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.grablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'


class MAPLUS_OT_QuickAlnSrcGrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickalnsrcgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnDestGrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickalndestgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAxrSrcGrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickaxrsrcgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickDsSrcGrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickdssrcgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickDsDestGrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickdsdestgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'DSDEST'


class MAPLUS_OT_QuickSmeSrcGrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quicksmesrcgrablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeDestGrabLineEndFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quicksmedestgrablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_GrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablineendfromactivelocal"
    bl_label = "Grab From Active Point"
    bl_description = "Grabs coordinates from selected vertex in edit mode"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False


class MAPLUS_OT_GrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablineendfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True


class MAPLUS_OT_QuickAlnSrcGrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalnsrcgrablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs local coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnSrcGrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalnsrcgrablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs global coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnDestGrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalndestgrablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs local coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAlnDestGrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalndestgrablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs global coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAxrSrcGrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaxrsrcgrablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs global coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickAxrSrcGrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaxrsrcgrablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs local coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickDsSrcGrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdssrcgrablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs local coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickDsSrcGrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdssrcgrablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs global coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickDsDestGrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdsdestgrablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs local coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'DSDEST'


class MAPLUS_OT_QuickDsDestGrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdsdestgrablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs global coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'DSDEST'


class MAPLUS_OT_QuickSmeSrcGrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quicksmesrcgrablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs local coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeSrcGrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quicksmesrcgrablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs global coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeDestGrabLineEndFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quicksmedestgrablineendfromactivelocal"
    bl_label = "Grab Local Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs local coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_QuickSmeDestGrabLineEndFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quicksmedestgrablineendfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line End From Active Point"
    bl_description = (
        "Grabs global coordinates for line end from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_SendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.sendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'


class MAPLUS_OT_QuickAlnSrcSendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickalnsrcsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnDestSendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickalndestsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAxrSrcSendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickaxrsrcsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickDsSrcSendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickdssrcsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickDsDestSendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickdsdestsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'DSDEST'


class MAPLUS_OT_QuickSmeSrcSendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quicksmesrcsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeDestSendLineEndToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quicksmedestsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_GrabAllVertsLineLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.graballvertslinelocal"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False


class MAPLUS_OT_GrabAllVertsLineGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.graballvertslineglobal"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True


class MAPLUS_OT_GrabLineSlot1(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablineslot1"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_GrabLineSlot1Loc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablineslot1loc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "SLOT1"


class MAPLUS_OT_GrabLineSlot2(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablineslot2"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_GrabLineSlot2Loc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablineslot2loc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "SLOT2"


class MAPLUS_OT_GrabLineCalcResult(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablinecalcresult"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_GrabLineCalcResultLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grablinecalcresultloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_GrabNormal(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.grabnormal"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True


class MAPLUS_OT_Slot1GrabNormal(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.slot1grabnormal"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_Slot2GrabNormal(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.slot2grabnormal"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_CalcResultGrabNormal(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.calcresultgrabnormal"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_QuickAlnGrabNormalSrc(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.quickalngrabnormalsrc"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "ALNSRC"


class MAPLUS_OT_QuickAlnGrabNormalDest(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.quickalngrabnormaldest"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "ALNDEST"


class MAPLUS_OT_QuickAxrGrabNormalSrc(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.quickaxrgrabnormalsrc"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "AXRSRC"


class MAPLUS_OT_QuickDsGrabNormalSrc(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.quickdsgrabnormalsrc"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "DSSRC"


class MAPLUS_OT_QuickSmeGrabNormalSrc(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.quicksmegrabnormalsrc"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SMESRC"


class MAPLUS_OT_QuickSmeGrabNormalDest(MAPLUS_OT_GrabNormalBase):
    bl_idname = "maplus.quicksmegrabnormaldest"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SMEDEST"


class MAPLUS_OT_QuickAlignLinesGrabSrc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignlinesgrabsrc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "ALNSRC"


class MAPLUS_OT_QuickAlignLinesGrabSrcLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignlinesgrabsrcloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "ALNSRC"


class MAPLUS_OT_QuickAlignLinesGrabDest(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignlinesgrabdest"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "ALNDEST"


class MAPLUS_OT_QuickAlignLinesGrabDestLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignlinesgrabdestloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "ALNDEST"


class MAPLUS_OT_QuickScaleMatchEdgeGrabSrc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickscalematchedgegrabsrc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SMESRC"


class MAPLUS_OT_QuickScaleMatchEdgeGrabSrcLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickscalematchedgegrabsrcloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "SMESRC"


class MAPLUS_OT_QuickScaleMatchEdgeGrabDest(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickscalematchedgegrabdest"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SMEDEST"


class MAPLUS_OT_QuickScaleMatchEdgeGrabDestLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickscalematchedgegrabdestloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "SMEDEST"


class MAPLUS_OT_QuickAxisRotateGrabSrc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaxisrotategrabsrc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "AXRSRC"


class MAPLUS_OT_QuickAxisRotateGrabSrcLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaxisrotategrabsrcloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "AXRSRC"


class MAPLUS_OT_QuickDirectionalSlideGrabSrc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdirectionalslidegrabsrc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "DSSRC"


class MAPLUS_OT_QuickDirectionalSlideGrabSrcLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickdirectionalslidegrabsrcloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "DSSRC"


class MAPLUS_OT_GrabPlaneAFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.grabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'


class MAPLUS_OT_Slot1GrabPlaneAFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot1grabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabPlaneBFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot1grabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabPlaneCFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot1grabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2GrabPlaneAFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot2grabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabPlaneBFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot2grabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabPlaneCFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.slot2grabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultGrabPlaneAFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabPlaneBFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabPlaneCFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_QuickAplSrcGrabPlaneAFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickaplsrcgrabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestGrabPlaneAFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickapldestgrabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'APLDEST'


class MAPLUS_OT_GrabPlaneAFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False


class MAPLUS_OT_GrabPlaneAFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True


class MAPLUS_OT_Slot1GrabPlaneAFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabPlaneAFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabPlaneBFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabPlaneBFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabPlaneCFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1GrabPlaneCFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2GrabPlaneAFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabPlaneAFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabPlaneBFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabPlaneBFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabPlaneCFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2GrabPlaneCFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultGrabPlaneAFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabPlaneAFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabPlaneBFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabPlaneBFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabPlaneCFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultGrabPlaneCFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_Slot1GrabAvgPlaneA(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavgplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_Slot1GrabAvgPlaneB(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavgplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_Slot1GrabAvgPlaneC(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavgplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_Slot2GrabAvgPlaneA(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavgplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_Slot2GrabAvgPlaneB(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavgplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_Slot2GrabAvgPlaneC(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavgplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_CalcResultGrabAvgPlaneA(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavgplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_CalcResultGrabAvgPlaneB(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavgplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_CalcResultGrabAvgPlaneC(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavgplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_QuickAplGrabAvgSrcPlaneA(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgsrcplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "APLSRC"


class MAPLUS_OT_QuickAplGrabAvgDestPlaneA(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgdestplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "APLDEST"


class MAPLUS_OT_QuickAplSrcGrabPlaneAFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplSrcGrabPlaneAFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestGrabPlaneAFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLDEST'


class MAPLUS_OT_QuickAplDestGrabPlaneAFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLDEST'


class MAPLUS_OT_SendPlaneAToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.sendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'


class MAPLUS_OT_Slot1SendPlaneAToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1SendPlaneBToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1SendPlaneCToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2SendPlaneAToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2SendPlaneBToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2SendPlaneCToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultSendPlaneAToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultSendPlaneBToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultSendPlaneCToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_QuickAplSrcSendPlaneAToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickaplsrcsendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestSendPlaneAToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickapldestsendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'APLDEST'


class MAPLUS_OT_GrabPlaneBFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.grabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'


class MAPLUS_OT_QuickAplSrcGrabPlaneBFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickaplsrcgrabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestGrabPlaneBFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickapldestgrabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'APLDEST'


class MAPLUS_OT_GrabPlaneBFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False


class MAPLUS_OT_GrabPlaneBFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True


class MAPLUS_OT_QuickAplGrabAvgSrcPlaneB(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgsrcplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "APLSRC"


class MAPLUS_OT_QuickAplGrabAvgDestPlaneB(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgdestplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "APLDEST"


class MAPLUS_OT_QuickAplSrcGrabPlaneBFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplSrcGrabPlaneBFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestGrabPlaneBFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLDEST'


class MAPLUS_OT_QuickAplDestGrabPlaneBFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLDEST'


class MAPLUS_OT_SendPlaneBToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.sendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'


class MAPLUS_OT_QuickAplSrcSendPlaneBToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickaplsrcsendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestSendPlaneBToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickapldestsendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'APLDEST'


class MAPLUS_OT_GrabPlaneCFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.grabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'


class MAPLUS_OT_QuickAplSrcGrabPlaneCFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickaplsrcgrabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestGrabPlaneCFromCursor(MAPLUS_OT_GrabFromCursorBase):
    bl_idname = "maplus.quickapldestgrabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'APLDEST'


class MAPLUS_OT_GrabPlaneCFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False


class MAPLUS_OT_GrabPlaneCFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True


class MAPLUS_OT_QuickAplGrabAvgSrcPlaneC(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgsrcplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "APLSRC"


class MAPLUS_OT_QuickAplGrabAvgDestPlaneC(MAPLUS_OT_GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgdestplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "APLDEST"


class MAPLUS_OT_QuickAplSrcGrabPlaneCFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplSrcGrabPlaneCFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestGrabPlaneCFromActiveLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLDEST'


class MAPLUS_OT_QuickAplDestGrabPlaneCFromActiveGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLDEST'


class MAPLUS_OT_SendPlaneCToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.sendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'


class MAPLUS_OT_QuickAplSrcSendPlaneCToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickaplsrcsendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestSendPlaneCToCursor(MAPLUS_OT_SendCoordToCursorBase):
    bl_idname = "maplus.quickapldestsendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'APLDEST'


class MAPLUS_OT_GrabAllVertsPlaneLocal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.graballvertsplanelocal"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False


class MAPLUS_OT_GrabAllVertsPlaneGlobal(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.graballvertsplaneglobal"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True


class MAPLUS_OT_GrabPlaneSlot1Loc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneslot1loc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "SLOT1"


class MAPLUS_OT_GrabPlaneSlot1(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneslot1"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class MAPLUS_OT_GrabPlaneSlot2Loc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneslot2loc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "SLOT2"


class MAPLUS_OT_GrabPlaneSlot2(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneslot2"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class MAPLUS_OT_GrabPlaneCalcResultLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplanecalcresultloc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_GrabPlaneCalcResult(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.grabplanecalcresult"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class MAPLUS_OT_QuickAlignPlanesGrabSrc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignplanesgrabsrc"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "APLSRC"


class MAPLUS_OT_QuickAlignPlanesGrabDest(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignplanesgrabdest"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "APLDEST"


class MAPLUS_OT_QuickAlignPlanesGrabSrcLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignplanesgrabsrcloc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "APLSRC"


class MAPLUS_OT_QuickAlignPlanesGrabDestLoc(MAPLUS_OT_GrabFromGeometryBase):
    bl_idname = "maplus.quickalignplanesgrabdestloc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "APLDEST"


# Coordinate swapper, present on all geometry primitives
# that have multiple points (line, plane)
class MAPLUS_OT_SwapPointsBase(bpy.types.Operator):
    bl_idname = "maplus.swappointsbase"
    bl_label = "Swap Points Base"
    bl_description = "Swap points base class"
    bl_options = {'REGISTER', 'UNDO'}
    targets = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, "quick_op_target"):
            if self.quick_op_target == "DSSRC":
                active_item = addon_data.quick_directional_slide_src

            elif self.quick_op_target == "SMESRC":
                active_item = addon_data.quick_scale_match_edge_src
            elif self.quick_op_target == "SMEDEST":
                active_item = addon_data.quick_scale_match_edge_dest

            elif self.quick_op_target == "ALNSRC":
                active_item = addon_data.quick_align_lines_src
            elif self.quick_op_target == "ALNDEST":
                active_item = addon_data.quick_align_lines_dest

            elif self.quick_op_target == "AXRSRC":
                active_item = addon_data.quick_axis_rotate_src

            elif self.quick_op_target == "APLSRC":
                active_item = addon_data.quick_align_planes_src
            elif self.quick_op_target == "APLDEST":
                active_item = addon_data.quick_align_planes_dest

            elif self.quick_op_target == "SLOT1":
                active_item = addon_data.internal_storage_slot_1
            elif self.quick_op_target == "SLOT2":
                active_item = addon_data.internal_storage_slot_2
            elif self.quick_op_target == "CALCRESULT":
                active_item = addon_data.quick_calc_result_item

        else:
            active_item = prims[addon_data.active_list_item]

        source = getattr(active_item, self.targets[0])
        source = mathutils.Vector(
            (source[0],
             source[1],
             source[2])
        )
        dest = getattr(active_item, self.targets[1])
        dest = mathutils.Vector(
            (dest[0],
             dest[1],
             dest[2])
        )

        setattr(
            active_item,
            self.targets[0],
            dest
        )
        setattr(
            active_item,
            self.targets[1],
            source
        )
        return {'FINISHED'}


class MAPLUS_OT_SwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.swaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')


class MAPLUS_OT_Slot1SwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.slot1swaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2SwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.slot2swaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultSwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.calcresultswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_QuickAlnSrcSwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickalnsrcswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_QuickAlnDestSwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickalndestswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_QuickAxrSrcSwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickaxrsrcswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_QuickDsSrcSwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickdssrcswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'DSSRC'


class MAPLUS_OT_QuickSmeSrcSwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quicksmesrcswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'SMESRC'


class MAPLUS_OT_QuickSmeDestSwapLinePoints(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quicksmedestswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'SMEDEST'


class MAPLUS_OT_SwapPlaneAPlaneB(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.swapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')


class MAPLUS_OT_SwapPlaneAPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.swapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')


class MAPLUS_OT_SwapPlaneBPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.swapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')


class MAPLUS_OT_Slot1SwapPlaneAPlaneB(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.slot1swapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1SwapPlaneAPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.slot1swapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot1SwapPlaneBPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.slot1swapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'SLOT1'


class MAPLUS_OT_Slot2SwapPlaneAPlaneB(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.slot2swapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2SwapPlaneAPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.slot2swapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'SLOT2'


class MAPLUS_OT_Slot2SwapPlaneBPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.slot2swapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'SLOT2'


class MAPLUS_OT_CalcResultSwapPlaneAPlaneB(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.calcresultswapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultSwapPlaneAPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.calcresultswapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_CalcResultSwapPlaneBPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.calcresultswapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_QuickAplSrcSwapPlaneAPlaneB(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickaplsrcswapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplSrcSwapPlaneAPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickaplsrcswapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplSrcSwapPlaneBPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickaplsrcswapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'APLSRC'


class MAPLUS_OT_QuickAplDestSwapPlaneAPlaneB(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickapldestswapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'APLDEST'


class MAPLUS_OT_QuickAplDestSwapPlaneAPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickapldestswapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'APLDEST'


class MAPLUS_OT_QuickAplDestSwapPlaneBPlaneC(MAPLUS_OT_SwapPointsBase):
    bl_idname = "maplus.quickapldestswapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'APLDEST'


# Every x/y/z coordinate component has these functions on each of the
# geometry primitives (lets users move in one direction easily, etc.)
class MAPLUS_OT_SetOtherComponentsBase(bpy.types.Operator):
    bl_idname = "maplus.setotherbase"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple containing the geometry attribute name (a string), the
    # coord type in ['X', 'Y', 'Z'], and the value to set (currently
    # 0 and 1 are the planned uses for this...to make building one
    # dimensional moves etc. possible)
    target_info = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if self.target_info[1] == 'X':
            setattr(
                active_item,
                self.target_info[0],
                (getattr(active_item, self.target_info[0])[0],
                 self.target_info[2],
                 self.target_info[2]
                 )
            )
        elif self.target_info[1] == 'Y':
            setattr(
                active_item,
                self.target_info[0],
                (self.target_info[2],
                 getattr(active_item, self.target_info[0])[1],
                 self.target_info[2]
                 )
            )
        elif self.target_info[1] == 'Z':
            setattr(
                active_item,
                self.target_info[0],
                (self.target_info[2],
                 self.target_info[2],
                 getattr(active_item, self.target_info[0])[2]
                 )
            )

        return {'FINISHED'}


class MAPLUS_OT_ZeroOtherPointX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherpointx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'X', 0)


class MAPLUS_OT_ZeroOtherPointY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherpointy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'Y', 0)


class MAPLUS_OT_ZeroOtherPointZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherpointz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'Z', 0)


class MAPLUS_OT_ZeroOtherLineStartX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlinestartx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'X', 0)


class MAPLUS_OT_ZeroOtherLineStartY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlinestarty"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'Y', 0)


class MAPLUS_OT_ZeroOtherLineStartZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlinestartz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'Z', 0)


class MAPLUS_OT_ZeroOtherLineEndX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlineendx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'X', 0)


class MAPLUS_OT_ZeroOtherLineEndY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlineendy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'Y', 0)


class MAPLUS_OT_ZeroOtherLineEndZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlineendz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'Z', 0)


class MAPLUS_OT_ZeroOtherPlanePointAX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointax"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'X', 0)


class MAPLUS_OT_ZeroOtherPlanePointAY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointay"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'Y', 0)


class MAPLUS_OT_ZeroOtherPlanePointAZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointaz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'Z', 0)


class MAPLUS_OT_ZeroOtherPlanePointBX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointbx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'X', 0)


class MAPLUS_OT_ZeroOtherPlanePointBY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointby"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'Y', 0)


class MAPLUS_OT_ZeroOtherPlanePointBZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointbz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'Z', 0)


class MAPLUS_OT_ZeroOtherPlanePointCX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointcx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'X', 0)


class MAPLUS_OT_ZeroOtherPlanePointCY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointcy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'Y', 0)


class MAPLUS_OT_ZeroOtherPlanePointCZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointcz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'Z', 0)


class MAPLUS_OT_OneOtherPointX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherpointx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'X', 1)


class MAPLUS_OT_OneOtherPointY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherpointy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'Y', 1)


class MAPLUS_OT_OneOtherPointZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherpointz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'Z', 1)


class MAPLUS_OT_OneOtherLineStartX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlinestartx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'X', 1)


class MAPLUS_OT_OneOtherLineStartY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlinestarty"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'Y', 1)


class MAPLUS_OT_OneOtherLineStartZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlinestartz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'Z', 1)


class MAPLUS_OT_OneOtherLineEndX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlineendx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'X', 1)


class MAPLUS_OT_OneOtherLineEndY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlineendy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'Y', 1)


class MAPLUS_OT_OneOtherLineEndZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlineendz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'Z', 1)


class MAPLUS_OT_OneOtherPlanePointAX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointax"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'X', 1)


class MAPLUS_OT_OneOtherPlanePointAY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointay"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'Y', 1)


class MAPLUS_OT_OneOtherPlanePointAZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointaz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'Z', 1)


class MAPLUS_OT_OneOtherPlanePointBX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointbx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'X', 1)


class MAPLUS_OT_OneOtherPlanePointBY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointby"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'Y', 1)


class MAPLUS_OT_OneOtherPlanePointBZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointbz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'Z', 1)


class MAPLUS_OT_OneOtherPlanePointCX(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointcx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'X', 1)


class MAPLUS_OT_OneOtherPlanePointCY(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointcy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'Y', 1)


class MAPLUS_OT_OneOtherPlanePointCZ(MAPLUS_OT_SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointcz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'Z', 1)


def get_modified_global_coords(geometry, kind):
    '''Get global coordinates for geometry items with modifiers applied.

    Arguments:
        geometry
            a maplus primitive
        kind
            the type of the geometry item, in ('POINT', 'LINE', 'PLANE')

    Returns:
        Return a list of vectors, where len(list) is in [1, 3]. If
        the kind isn't correct, return an empty list.
    '''
    global_modified = []
    if kind == 'POINT':
        global_modified.append(mathutils.Vector(geometry.point))

        if geometry.pt_make_unit_vec:
            global_modified[0].normalize()
        if geometry.pt_flip_direction:
            global_modified[0].negate()
        global_modified[0] *= geometry.pt_multiplier

    elif kind == 'LINE':
        global_modified.append(mathutils.Vector(geometry.line_start))
        global_modified.append(mathutils.Vector(geometry.line_end))

        line = mathutils.Vector(
            global_modified[1] -
            global_modified[0]
        )
        if geometry.ln_make_unit_vec:
            line.normalize()
        if geometry.ln_flip_direction:
            line.negate()
        line *= geometry.ln_multiplier
        global_modified[1] = (
            global_modified[0] +
            line
        )

    elif kind == 'PLANE':
        global_modified.append(mathutils.Vector(geometry.plane_pt_a))
        global_modified.append(mathutils.Vector(geometry.plane_pt_b))
        global_modified.append(mathutils.Vector(geometry.plane_pt_c))
    else:
        return list()

    return global_modified


class MAPLUS_OT_ApplyGeomModifiers(bpy.types.Operator):
    bl_idname = "maplus.applygeommodifiers"
    bl_label = "Apply Modifiers"
    bl_description = "Applies modifiers on the current geometry item."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = get_active_object().mode
        active_item = prims[addon_data.active_list_item]

        if active_item.kind == 'POINT':
            if active_item.pt_make_unit_vec:
                active_item.point = mathutils.Vector(
                    active_item.point
                ).normalized()
                active_item.pt_make_unit_vec = False
            if active_item.pt_flip_direction:
                flipped = mathutils.Vector(
                    active_item.point
                )
                flipped.negate()
                active_item.point = flipped
                active_item.pt_flip_direction = False
            # Apply multiplier
            active_item.point = mathutils.Vector(
                active_item.point
            ) * active_item.pt_multiplier
            active_item.pt_multiplier = 1
        elif active_item.kind == 'LINE':
            if active_item.ln_make_unit_vec:
                vec = (
                    mathutils.Vector(
                        active_item.line_end
                    ) -
                    mathutils.Vector(
                        active_item.line_start
                    )
                )
                active_item.line_end = (
                    mathutils.Vector(
                        active_item.line_start
                    ) +
                    vec.normalized()
                )
                active_item.ln_make_unit_vec = False
            if active_item.ln_flip_direction:
                vec = (
                    mathutils.Vector(
                        active_item.line_end
                    ) -
                    mathutils.Vector(
                        active_item.line_start
                    )
                )
                vec.negate()
                active_item.line_end = (
                    mathutils.Vector(
                        active_item.line_start
                    ) + vec
                )
                active_item.ln_flip_direction = False
            # Apply multiplier
            vec = (
                mathutils.Vector(
                    active_item.line_end
                ) -
                mathutils.Vector(
                    active_item.line_start
                )
            ) * active_item.ln_multiplier
            active_item.line_end = (
                mathutils.Vector(
                    active_item.line_start
                ) + vec
            )
            active_item.ln_multiplier = 1
        elif active_item.kind == 'PLANE':
            # Apply future plane modifiers here
            pass

        return {'FINISHED'}


# TODO: Remove, 2.7x/2.8x cross compatibility no longer supported
# Blender 2.8 API compatibility var
if str(bpy.app.version[1]).startswith('8'):
    BLENDER_28_PY_API = True
else:
    BLENDER_28_PY_API = False


# Blender 2.8 API compatibility func
def get_active_object():
    if BLENDER_28_PY_API:
        return bpy.context.view_layer.objects.active
    else:
        return bpy.context.active_object


# Blender 2.8 API compatibility func
def get_select_state(item):
    if BLENDER_28_PY_API:
        return item.select_get()
    else:
        return item.select


# Blender 2.8 API compatibility func
def set_select_state(state, item):
    if BLENDER_28_PY_API:
        item.select_set(state)
    else:
        item.select = state


class MAPLUS_OT_ShowHideQuickGeomBaseClass(bpy.types.Operator):
    bl_idname = "maplus.showhidequickgeombaseclass"
    bl_label = "Show/hide quick geometry base class"
    bl_description = "The base class for showing/hiding quick geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        if self.quick_op_target == "APTSRC":
            addon_data.quick_apt_show_src_geom = (
                not addon_data.quick_apt_show_src_geom
            )
        elif self.quick_op_target == "APTDEST":
            addon_data.quick_apt_show_dest_geom = (
                not addon_data.quick_apt_show_dest_geom
            )
        elif self.quick_op_target == "DSSRC":
            addon_data.quick_ds_show_src_geom = (
                not addon_data.quick_ds_show_src_geom
            )

        elif self.quick_op_target == "SMESRC":
            addon_data.quick_sme_show_src_geom = (
                not addon_data.quick_sme_show_src_geom
            )
        elif self.quick_op_target == "SMEDEST":
            addon_data.quick_sme_show_dest_geom = (
                not addon_data.quick_sme_show_dest_geom
            )

        elif self.quick_op_target == "ALNSRC":
            addon_data.quick_aln_show_src_geom = (
                not addon_data.quick_aln_show_src_geom
            )
        elif self.quick_op_target == "ALNDEST":
            addon_data.quick_aln_show_dest_geom = (
                not addon_data.quick_aln_show_dest_geom
            )

        elif self.quick_op_target == "AXRSRC":
            addon_data.quick_axr_show_src_geom = (
                not addon_data.quick_axr_show_src_geom
            )

        elif self.quick_op_target == "APLSRC":
            addon_data.quick_apl_show_src_geom = (
                not addon_data.quick_apl_show_src_geom
            )
        elif self.quick_op_target == "APLDEST":
            addon_data.quick_apl_show_dest_geom = (
                not addon_data.quick_apl_show_dest_geom
            )
        elif self.quick_op_target == "SLOT1":
            addon_data.quick_calc_show_slot1_geom = (
                not addon_data.quick_calc_show_slot1_geom
            )
        elif self.quick_op_target == "SLOT2":
            addon_data.quick_calc_show_slot2_geom = (
                not addon_data.quick_calc_show_slot2_geom
            )
        elif self.quick_op_target == "CALCRESULT":
            addon_data.quick_calc_show_result_geom = (
                not addon_data.quick_calc_show_result_geom
            )

        return {'FINISHED'}


class MAPLUS_OT_ShowHideQuickCalcSlot1Geom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickcalcslot1geom"
    bl_label = "Show/hide slot 1 geometry"
    bl_description = "Show/hide slot 1 geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'SLOT1'


class MAPLUS_OT_ShowHideQuickCalcSlot2Geom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickcalcslot2geom"
    bl_label = "Show/hide slot 2 geometry"
    bl_description = "Show/hide slot 2 geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'SLOT2'


class MAPLUS_OT_ShowHideQuickCalcResultGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickcalcresultgeom"
    bl_label = "Show/hide calculation result geometry"
    bl_description = "Show/hide calculation result geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'CALCRESULT'


class MAPLUS_OT_ShowHideQuickAptSrcGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickaptsrcgeom"
    bl_label = "Show/hide quick align points source geometry"
    bl_description = "Show/hide quick align points source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'APTSRC'


class MAPLUS_OT_ShowHideQuickAptDestGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickaptdestgeom"
    bl_label = "Show/hide quick align points destination geometry"
    bl_description = "Show/hide quick align points destination geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'APTDEST'


class MAPLUS_OT_ShowHideQuickAlnSrcGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickalnsrcgeom"
    bl_label = "Show/hide quick align lines source geometry"
    bl_description = "Show/hide quick align lines source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'ALNSRC'


class MAPLUS_OT_ShowHideQuickAlnDestGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickalndestgeom"
    bl_label = "Show/hide quick align lines destination geometry"
    bl_description = "Show/hide quick align lines destination geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'ALNDEST'


class MAPLUS_OT_ShowHideQuickAplSrcGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickaplsrcgeom"
    bl_label = "Show/hide quick align planes source geometry"
    bl_description = "Show/hide quick align planes source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'APLSRC'


class MAPLUS_OT_ShowHideQuickAplDestGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickapldestgeom"
    bl_label = "Show/hide quick align planes destination geometry"
    bl_description = "Show/hide quick align planes destination geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'APLDEST'


class MAPLUS_OT_ShowHideQuickAxrSrcGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickaxrsrcgeom"
    bl_label = "Show/hide quick axis rotate source geometry"
    bl_description = "Show/hide quick axis rotate source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'AXRSRC'


class MAPLUS_OT_ShowHideQuickDsSrcGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickdssrcgeom"
    bl_label = "Show/hide quick directional slide source geometry"
    bl_description = "Show/hide quick directional slide source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'DSSRC'


class MAPLUS_OT_ShowHideQuickSmeSrcGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequicksmesrcgeom"
    bl_label = "Show/hide quick scale match edge source geometry"
    bl_description = "Show/hide quick scale match edge source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'SMESRC'


class MAPLUS_OT_ShowHideQuickSmeDestGeom(MAPLUS_OT_ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequicksmedestgeom"
    bl_label = "Show/hide quick scale match edge source geometry"
    bl_description = "Show/hide quick scale match edge source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'SMEDEST'
