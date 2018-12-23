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
class GrabFromGeometryBase(bpy.types.Operator):
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


class GrabSmeNumeric(bpy.types.Operator):
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


class GrabAndSetItemKindBase(bpy.types.Operator):
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


class GrabAverageLocationBase(bpy.types.Operator):
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


class GrabNormalBase(bpy.types.Operator):
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
class GrabFromCursorBase(bpy.types.Operator):
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
class SendCoordToCursorBase(bpy.types.Operator):
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


class GrabAllSlot1(GrabAndSetItemKindBase):
    bl_idname = "maplus.graballslot1"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = True
    target = 'SLOT1'


class GrabAllSlot1Loc(GrabAndSetItemKindBase):
    bl_idname = "maplus.graballslot1loc"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = False
    target = 'SLOT1'


class GrabAllSlot2(GrabAndSetItemKindBase):
    bl_idname = "maplus.graballslot2"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = True
    target = 'SLOT2'


class GrabAllSlot2Loc(GrabAndSetItemKindBase):
    bl_idname = "maplus.graballslot2loc"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = False
    target = 'SLOT2'


class GrabAllCalcResult(GrabAndSetItemKindBase):
    bl_idname = "maplus.graballcalcresult"
    bl_label = "Grab Global Coordinates From Selected Vertices"
    bl_description = (
        "Grabs global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    multiply_by_world_matrix = True
    target = 'CALCRESULT'


class GrabPointFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'


class Slot1GrabPointFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot1grabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = "SLOT1"


class Slot2GrabPointFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot2grabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = "SLOT2"


class CalcResultGrabPointFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = "CALCRESULT"


class QuickAptSrcGrabPointFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickaptsrcgrabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = 'APTSRC'


class QuickAptDestGrabPointFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickaptdestgrabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'
    quick_op_target = 'APTDEST'


class GrabPointFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.grabpointfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False


class GrabPointFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.grabpointfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True


class GrabPointSlot1(GrabFromGeometryBase):
    bl_idname = "maplus.grabpointslot1"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class GrabPointSlot1Loc(GrabFromGeometryBase):
    bl_idname = "maplus.grabpointslot1loc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "SLOT1"


class GrabPointCalcResult(GrabFromGeometryBase):
    bl_idname = "maplus.grabpointcalcresult"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class GrabPointCalcResultLoc(GrabFromGeometryBase):
    bl_idname = "maplus.grabpointcalcresultloc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "CALCRESULT"


class GrabPointSlot2(GrabFromGeometryBase):
    bl_idname = "maplus.grabpointslot2"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class GrabPointSlot2Loc(GrabFromGeometryBase):
    bl_idname = "maplus.grabpointslot2loc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "SLOT2"


class PointGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.pointgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True


class LineStartGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.linestartgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True


class LineEndGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.lineendgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True


class PlaneAGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.planeagrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True


class PlaneBGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.planebgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True


class PlaneCGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.planecgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True


class Slot1PointGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.slot1pointgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class Slot2PointGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.slot2pointgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class CalcResultPointGrabAvg(GrabAverageLocationBase):
    bl_idname = "maplus.calcresultpointgrabavg"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class QuickAptGrabAvgSrc(GrabAverageLocationBase):
    bl_idname = "maplus.quickaptgrabavgsrc"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "APTSRC"


class QuickAptGrabAvgDest(GrabAverageLocationBase):
    bl_idname = "maplus.quickaptgrabavgdest"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "APTDEST"


class QuickAlignPointsGrabSrc(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignpointsgrabsrc"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "APTSRC"


class QuickAlignPointsGrabDest(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignpointsgrabdest"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True
    quick_op_target = "APTDEST"


class QuickAlignPointsGrabSrcLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignpointsgrabsrcloc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "APTSRC"


class QuickAlignPointsGrabDestLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignpointsgrabdestloc"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = False
    quick_op_target = "APTDEST"


class SendPointToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'


class Slot1SendPointToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'SLOT1'


class Slot2SendPointToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'SLOT2'


class CalcResultSendPointToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'CALCRESULT'


class QuickAptSrcSendPointToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickaptsrcsendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'APTSRC'


class QuickAptDestSendPointToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickaptdestsendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'
    quick_op_target = 'APTDEST'


class GrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'


class Slot1GrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot1grablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'SLOT1'


class Slot1GrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot1grablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'SLOT1'


class Slot2GrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot2grablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'SLOT2'


class Slot2GrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot2grablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'SLOT2'


class CalcResultGrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'CALCRESULT'


class CalcResultGrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'CALCRESULT'


class QuickAlnSrcGrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickalnsrcgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'ALNSRC'


class QuickAlnDestGrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickalndestgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'ALNDEST'


class QuickAxrSrcGrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickaxrsrcgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'AXRSRC'


class QuickDsSrcGrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickdssrcgrablinestartfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'DSSRC'


class QuickDsDestGrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickdsdestgrablinestartfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'DSDEST'


class QuickSmeSrcGrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quicksmesrcgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'SMESRC'


class QuickSmeDestGrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quicksmedestgrablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'
    quick_op_target = 'SMEDEST'


class GrabLineStartFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.grablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = False


class GrabLineStartFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.grablinestartfromactiveglobal"
    bl_label = "Grab Global Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs global coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True


class Slot1GrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class Slot2GrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class CalcResultGrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class Slot1GrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class Slot2GrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class CalcResultGrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class Slot1GrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class Slot1GrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class Slot2GrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class Slot2GrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class CalcResultGrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class CalcResultGrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class Slot1GrabAvgLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavglinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class Slot2GrabAvgLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavglinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class CalcResultGrabAvgLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavglinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class Slot1GrabAvgLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavglineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class Slot2GrabAvgLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavglineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class CalcResultGrabAvgLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavglineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class QuickAlnGrabAvgSrcLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.quickalngrabavgsrclinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "ALNSRC"


class QuickAlnGrabAvgDestLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.quickalngrabavgdestlinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "ALNDEST"


class QuickAlnGrabAvgSrcLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.quickalngrabavgsrclineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "ALNSRC"


class QuickAlnGrabAvgDestLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.quickalngrabavgdestlineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "ALNDEST"


class QuickAxrGrabAvgSrcLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.quickaxrgrabavgsrclinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "AXRSRC"


class QuickAxrGrabAvgSrcLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.quickaxrgrabavgsrclineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "AXRSRC"


class QuickDsGrabAvgSrcLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.quickdsgrabavgsrclinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "DSSRC"


class QuickDsGrabAvgSrcLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.quickdsgrabavgsrclineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "DSSRC"


class QuickSmeGrabAvgSrcLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.quicksmegrabavgsrclinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "SMESRC"


class QuickSmeGrabAvgDestLineStart(GrabAverageLocationBase):
    bl_idname = "maplus.quicksmegrabavgdestlinestart"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start',)
    multiply_by_world_matrix = True
    quick_op_target = "SMEDEST"


class QuickSmeGrabAvgSrcLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.quicksmegrabavgsrclineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "SMESRC"


class QuickSmeGrabAvgDestLineEnd(GrabAverageLocationBase):
    bl_idname = "maplus.quicksmegrabavgdestlineend"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True
    quick_op_target = "SMEDEST"


class QuickAlnSrcGrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class QuickAlnSrcGrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class QuickAlnDestGrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class QuickAlnDestGrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class QuickAxrSrcGrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class QuickAxrSrcGrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class QuickDsSrcGrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class QuickDsSrcGrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class QuickDsDestGrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class QuickDsDestGrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class QuickSmeSrcGrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class QuickSmeSrcGrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class QuickSmeDestGrabLineStartFromActiveLocal(GrabFromGeometryBase):
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


class QuickSmeDestGrabLineStartFromActiveGlobal(GrabFromGeometryBase):
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


class SendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'


class Slot1SendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'SLOT1'


class Slot1SendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendlineendtocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'SLOT1'


class Slot2SendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'SLOT2'


class Slot2SendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendlineendtocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'SLOT2'


class CalcResultSendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'CALCRESULT'


class CalcResultSendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'CALCRESULT'


class QuickAlnSrcSendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickalnsrcsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'ALNSRC'


class QuickAlnDestSendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickalndestsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'ALNDEST'


class QuickAxrSrcSendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickaxrsrcsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'AXRSRC'


class QuickDsSrcSendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickdssrcsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'DSSRC'


class QuickDsDestSendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickdsdestsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'DSDEST'


class QuickSmeSrcSendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quicksmesrcsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'SMESRC'


class QuickSmeDestSendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quicksmedestsendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'
    quick_op_target = 'SMEDEST'


class GrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'


class QuickAlnSrcGrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickalnsrcgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'ALNSRC'


class QuickAlnDestGrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickalndestgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'ALNDEST'


class QuickAxrSrcGrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickaxrsrcgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'AXRSRC'


class QuickDsSrcGrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickdssrcgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'DSSRC'


class QuickDsDestGrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickdsdestgrablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'DSDEST'


class QuickSmeSrcGrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quicksmesrcgrablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'SMESRC'


class QuickSmeDestGrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quicksmedestgrablineendfromcursor"
    bl_label = "Grab Line End From Cursor"
    bl_description = "Grabs line end coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'
    quick_op_target = 'SMEDEST'


class GrabLineEndFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.grablineendfromactivelocal"
    bl_label = "Grab From Active Point"
    bl_description = "Grabs coordinates from selected vertex in edit mode"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = False


class GrabLineEndFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.grablineendfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_end',)
    multiply_by_world_matrix = True


class QuickAlnSrcGrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class QuickAlnSrcGrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class QuickAlnDestGrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class QuickAlnDestGrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class QuickAxrSrcGrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class QuickAxrSrcGrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class QuickDsSrcGrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class QuickDsSrcGrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class QuickDsDestGrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class QuickDsDestGrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class QuickSmeSrcGrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class QuickSmeSrcGrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class QuickSmeDestGrabLineEndFromActiveLocal(GrabFromGeometryBase):
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


class QuickSmeDestGrabLineEndFromActiveGlobal(GrabFromGeometryBase):
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


class SendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'


class QuickAlnSrcSendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickalnsrcsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'ALNSRC'


class QuickAlnDestSendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickalndestsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'ALNDEST'


class QuickAxrSrcSendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickaxrsrcsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'AXRSRC'


class QuickDsSrcSendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickdssrcsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'DSSRC'


class QuickDsDestSendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickdsdestsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'DSDEST'


class QuickSmeSrcSendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quicksmesrcsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'SMESRC'


class QuickSmeDestSendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quicksmedestsendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'
    quick_op_target = 'SMEDEST'


class GrabAllVertsLineLocal(GrabFromGeometryBase):
    bl_idname = "maplus.graballvertslinelocal"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False


class GrabAllVertsLineGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.graballvertslineglobal"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True


class GrabLineSlot1(GrabFromGeometryBase):
    bl_idname = "maplus.grablineslot1"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class GrabLineSlot1Loc(GrabFromGeometryBase):
    bl_idname = "maplus.grablineslot1loc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "SLOT1"


class GrabLineSlot2(GrabFromGeometryBase):
    bl_idname = "maplus.grablineslot2"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class GrabLineSlot2Loc(GrabFromGeometryBase):
    bl_idname = "maplus.grablineslot2loc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "SLOT2"


class GrabLineCalcResult(GrabFromGeometryBase):
    bl_idname = "maplus.grablinecalcresult"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class GrabLineCalcResultLoc(GrabFromGeometryBase):
    bl_idname = "maplus.grablinecalcresultloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
        )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "CALCRESULT"


class GrabNormal(GrabNormalBase):
    bl_idname = "maplus.grabnormal"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True


class Slot1GrabNormal(GrabNormalBase):
    bl_idname = "maplus.slot1grabnormal"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class Slot2GrabNormal(GrabNormalBase):
    bl_idname = "maplus.slot2grabnormal"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class CalcResultGrabNormal(GrabNormalBase):
    bl_idname = "maplus.calcresultgrabnormal"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class QuickAlnGrabNormalSrc(GrabNormalBase):
    bl_idname = "maplus.quickalngrabnormalsrc"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "ALNSRC"


class QuickAlnGrabNormalDest(GrabNormalBase):
    bl_idname = "maplus.quickalngrabnormaldest"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "ALNDEST"


class QuickAxrGrabNormalSrc(GrabNormalBase):
    bl_idname = "maplus.quickaxrgrabnormalsrc"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "AXRSRC"


class QuickDsGrabNormalSrc(GrabNormalBase):
    bl_idname = "maplus.quickdsgrabnormalsrc"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "DSSRC"


class QuickSmeGrabNormalSrc(GrabNormalBase):
    bl_idname = "maplus.quicksmegrabnormalsrc"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SMESRC"


class QuickSmeGrabNormalDest(GrabNormalBase):
    bl_idname = "maplus.quicksmegrabnormaldest"
    bl_label = "Grab Normal Coords from Selected Face"
    bl_description = (
        "Grabs normal coordinates from selected face in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SMEDEST"


class QuickAlignLinesGrabSrc(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignlinesgrabsrc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "ALNSRC"


class QuickAlignLinesGrabSrcLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignlinesgrabsrcloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "ALNSRC"


class QuickAlignLinesGrabDest(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignlinesgrabdest"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "ALNDEST"


class QuickAlignLinesGrabDestLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignlinesgrabdestloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "ALNDEST"


class QuickScaleMatchEdgeGrabSrc(GrabFromGeometryBase):
    bl_idname = "maplus.quickscalematchedgegrabsrc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SMESRC"


class QuickScaleMatchEdgeGrabSrcLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickscalematchedgegrabsrcloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "SMESRC"


class QuickScaleMatchEdgeGrabDest(GrabFromGeometryBase):
    bl_idname = "maplus.quickscalematchedgegrabdest"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "SMEDEST"


class QuickScaleMatchEdgeGrabDestLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickscalematchedgegrabdestloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "SMEDEST"


class QuickAxisRotateGrabSrc(GrabFromGeometryBase):
    bl_idname = "maplus.quickaxisrotategrabsrc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "AXRSRC"


class QuickAxisRotateGrabSrcLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickaxisrotategrabsrcloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "AXRSRC"


class QuickDirectionalSlideGrabSrc(GrabFromGeometryBase):
    bl_idname = "maplus.quickdirectionalslidegrabsrc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True
    quick_op_target = "DSSRC"


class QuickDirectionalSlideGrabSrcLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickdirectionalslidegrabsrcloc"
    bl_label = "Grab Line from Selected Verts"
    bl_description = (
        "Grabs line coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = False
    quick_op_target = "DSSRC"


class GrabPlaneAFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'


class Slot1GrabPlaneAFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot1grabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'SLOT1'


class Slot1GrabPlaneBFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot1grabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'SLOT1'


class Slot1GrabPlaneCFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot1grabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'SLOT1'


class Slot2GrabPlaneAFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot2grabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'SLOT2'


class Slot2GrabPlaneBFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot2grabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'SLOT2'


class Slot2GrabPlaneCFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.slot2grabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'SLOT2'


class CalcResultGrabPlaneAFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'CALCRESULT'


class CalcResultGrabPlaneBFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'CALCRESULT'


class CalcResultGrabPlaneCFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.calcresultgrabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'CALCRESULT'


class QuickAplSrcGrabPlaneAFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickaplsrcgrabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'APLSRC'


class QuickAplDestGrabPlaneAFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickapldestgrabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'
    quick_op_target = 'APLDEST'


class GrabPlaneAFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False


class GrabPlaneAFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True


class Slot1GrabPlaneAFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT1'


class Slot1GrabPlaneAFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT1'


class Slot1GrabPlaneBFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT1'


class Slot1GrabPlaneBFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT1'


class Slot1GrabPlaneCFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT1'


class Slot1GrabPlaneCFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.slot1grabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT1'


class Slot2GrabPlaneAFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT2'


class Slot2GrabPlaneAFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT2'


class Slot2GrabPlaneBFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT2'


class Slot2GrabPlaneBFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT2'


class Slot2GrabPlaneCFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'SLOT2'


class Slot2GrabPlaneCFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.slot2grabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'SLOT2'


class CalcResultGrabPlaneAFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'CALCRESULT'


class CalcResultGrabPlaneAFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'CALCRESULT'


class CalcResultGrabPlaneBFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'CALCRESULT'


class CalcResultGrabPlaneBFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'CALCRESULT'


class CalcResultGrabPlaneCFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'CALCRESULT'


class CalcResultGrabPlaneCFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.calcresultgrabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'CALCRESULT'


class Slot1GrabAvgPlaneA(GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavgplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class Slot1GrabAvgPlaneB(GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavgplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class Slot1GrabAvgPlaneC(GrabAverageLocationBase):
    bl_idname = "maplus.slot1grabavgplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class Slot2GrabAvgPlaneA(GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavgplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class Slot2GrabAvgPlaneB(GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavgplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class Slot2GrabAvgPlaneC(GrabAverageLocationBase):
    bl_idname = "maplus.slot2grabavgplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class CalcResultGrabAvgPlaneA(GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavgplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class CalcResultGrabAvgPlaneB(GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavgplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class CalcResultGrabAvgPlaneC(GrabAverageLocationBase):
    bl_idname = "maplus.calcresultgrabavgplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class QuickAplGrabAvgSrcPlaneA(GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgsrcplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "APLSRC"


class QuickAplGrabAvgDestPlaneA(GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgdestplanea"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = "APLDEST"


class QuickAplSrcGrabPlaneAFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLSRC'


class QuickAplSrcGrabPlaneAFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLSRC'


class QuickAplDestGrabPlaneAFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplaneafromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLDEST'


class QuickAplDestGrabPlaneAFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplaneafromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLDEST'


class SendPlaneAToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'


class Slot1SendPlaneAToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'SLOT1'


class Slot1SendPlaneBToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'SLOT1'


class Slot1SendPlaneCToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot1sendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'SLOT1'


class Slot2SendPlaneAToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'SLOT2'


class Slot2SendPlaneBToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'SLOT2'


class Slot2SendPlaneCToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.slot2sendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'SLOT2'


class CalcResultSendPlaneAToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'CALCRESULT'


class CalcResultSendPlaneBToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'CALCRESULT'


class CalcResultSendPlaneCToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.calcresultsendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'CALCRESULT'


class QuickAplSrcSendPlaneAToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickaplsrcsendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'APLSRC'


class QuickAplDestSendPlaneAToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickapldestsendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'
    quick_op_target = 'APLDEST'


class GrabPlaneBFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'


class QuickAplSrcGrabPlaneBFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickaplsrcgrabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'APLSRC'


class QuickAplDestGrabPlaneBFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickapldestgrabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'
    quick_op_target = 'APLDEST'


class GrabPlaneBFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.grabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False


class GrabPlaneBFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.grabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True


class QuickAplGrabAvgSrcPlaneB(GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgsrcplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "APLSRC"


class QuickAplGrabAvgDestPlaneB(GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgdestplaneb"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = "APLDEST"


class QuickAplSrcGrabPlaneBFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLSRC'


class QuickAplSrcGrabPlaneBFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLSRC'


class QuickAplDestGrabPlaneBFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplanebfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLDEST'


class QuickAplDestGrabPlaneBFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplanebfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_b',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLDEST'


class SendPlaneBToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'


class QuickAplSrcSendPlaneBToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickaplsrcsendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'APLSRC'


class QuickAplDestSendPlaneBToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickapldestsendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'
    quick_op_target = 'APLDEST'


class GrabPlaneCFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'


class QuickAplSrcGrabPlaneCFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickaplsrcgrabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'APLSRC'


class QuickAplDestGrabPlaneCFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.quickapldestgrabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'
    quick_op_target = 'APLDEST'


class GrabPlaneCFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.grabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False


class GrabPlaneCFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.grabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True


class QuickAplGrabAvgSrcPlaneC(GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgsrcplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "APLSRC"


class QuickAplGrabAvgDestPlaneC(GrabAverageLocationBase):
    bl_idname = "maplus.quickaplgrabavgdestplanec"
    bl_label = "Grab Average Global Coordinates From Selected Points"
    bl_description = (
        "Grabs average global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = "APLDEST"


class QuickAplSrcGrabPlaneCFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLSRC'


class QuickAplSrcGrabPlaneCFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.quickaplsrcgrabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLSRC'


class QuickAplDestGrabPlaneCFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplanecfromactivelocal"
    bl_label = "Grab Local Coordinates From Active Point"
    bl_description = (
        "Grabs local coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = False
    quick_op_target = 'APLDEST'


class QuickAplDestGrabPlaneCFromActiveGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.quickapldestgrabplanecfromactiveglobal"
    bl_label = "Grab Global Coordinates From Active Point"
    bl_description = (
        "Grabs global coordinates from selected vertex in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_c',)
    multiply_by_world_matrix = True
    quick_op_target = 'APLDEST'


class SendPlaneCToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'


class QuickAplSrcSendPlaneCToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickaplsrcsendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'APLSRC'


class QuickAplDestSendPlaneCToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.quickapldestsendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'
    quick_op_target = 'APLDEST'


class GrabAllVertsPlaneLocal(GrabFromGeometryBase):
    bl_idname = "maplus.graballvertsplanelocal"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False


class GrabAllVertsPlaneGlobal(GrabFromGeometryBase):
    bl_idname = "maplus.graballvertsplaneglobal"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True


class GrabPlaneSlot1Loc(GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneslot1loc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "SLOT1"


class GrabPlaneSlot1(GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneslot1"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT1"


class GrabPlaneSlot2Loc(GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneslot2loc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "SLOT2"


class GrabPlaneSlot2(GrabFromGeometryBase):
    bl_idname = "maplus.grabplaneslot2"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "SLOT2"


class GrabPlaneCalcResultLoc(GrabFromGeometryBase):
    bl_idname = "maplus.grabplanecalcresultloc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "CALCRESULT"


class GrabPlaneCalcResult(GrabFromGeometryBase):
    bl_idname = "maplus.grabplanecalcresult"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "CALCRESULT"


class QuickAlignPlanesGrabSrc(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignplanesgrabsrc"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "APLSRC"


class QuickAlignPlanesGrabDest(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignplanesgrabdest"
    bl_label = "Grab Plane Global Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane global coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True
    quick_op_target = "APLDEST"


class QuickAlignPlanesGrabSrcLoc(GrabFromGeometryBase):
    bl_idname = "maplus.quickalignplanesgrabsrcloc"
    bl_label = "Grab Plane Local Coordinates from Selected Verts"
    bl_description = (
        "Grabs plane local coordinates from selected vertices in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = False
    quick_op_target = "APLSRC"


class QuickAlignPlanesGrabDestLoc(GrabFromGeometryBase):
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
class SwapPointsBase(bpy.types.Operator):
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


class SwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.swaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')


class Slot1SwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.slot1swaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'SLOT1'


class Slot2SwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.slot2swaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'SLOT2'


class CalcResultSwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.calcresultswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'CALCRESULT'


class QuickAlnSrcSwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.quickalnsrcswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'ALNSRC'


class QuickAlnDestSwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.quickalndestswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'ALNDEST'


class QuickAxrSrcSwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.quickaxrsrcswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'AXRSRC'


class QuickDsSrcSwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.quickdssrcswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'DSSRC'


class QuickSmeSrcSwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.quicksmesrcswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'SMESRC'


class QuickSmeDestSwapLinePoints(SwapPointsBase):
    bl_idname = "maplus.quicksmedestswaplinepoints"
    bl_label = "Swap Line Points"
    bl_description = "Swap line points"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('line_start', 'line_end')
    quick_op_target = 'SMEDEST'


class SwapPlaneAPlaneB(SwapPointsBase):
    bl_idname = "maplus.swapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')


class SwapPlaneAPlaneC(SwapPointsBase):
    bl_idname = "maplus.swapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')


class SwapPlaneBPlaneC(SwapPointsBase):
    bl_idname = "maplus.swapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')


class Slot1SwapPlaneAPlaneB(SwapPointsBase):
    bl_idname = "maplus.slot1swapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'SLOT1'


class Slot1SwapPlaneAPlaneC(SwapPointsBase):
    bl_idname = "maplus.slot1swapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'SLOT1'


class Slot1SwapPlaneBPlaneC(SwapPointsBase):
    bl_idname = "maplus.slot1swapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'SLOT1'


class Slot2SwapPlaneAPlaneB(SwapPointsBase):
    bl_idname = "maplus.slot2swapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'SLOT2'


class Slot2SwapPlaneAPlaneC(SwapPointsBase):
    bl_idname = "maplus.slot2swapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'SLOT2'


class Slot2SwapPlaneBPlaneC(SwapPointsBase):
    bl_idname = "maplus.slot2swapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'SLOT2'


class CalcResultSwapPlaneAPlaneB(SwapPointsBase):
    bl_idname = "maplus.calcresultswapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'CALCRESULT'


class CalcResultSwapPlaneAPlaneC(SwapPointsBase):
    bl_idname = "maplus.calcresultswapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'CALCRESULT'


class CalcResultSwapPlaneBPlaneC(SwapPointsBase):
    bl_idname = "maplus.calcresultswapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'CALCRESULT'


class QuickAplSrcSwapPlaneAPlaneB(SwapPointsBase):
    bl_idname = "maplus.quickaplsrcswapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'APLSRC'


class QuickAplSrcSwapPlaneAPlaneC(SwapPointsBase):
    bl_idname = "maplus.quickaplsrcswapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'APLSRC'


class QuickAplSrcSwapPlaneBPlaneC(SwapPointsBase):
    bl_idname = "maplus.quickaplsrcswapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'APLSRC'


class QuickAplDestSwapPlaneAPlaneB(SwapPointsBase):
    bl_idname = "maplus.quickapldestswapplaneaplaneb"
    bl_label = "Swap Plane Point A with Plane Point B"
    bl_description = "Swap plane points A and B"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_b')
    quick_op_target = 'APLDEST'


class QuickAplDestSwapPlaneAPlaneC(SwapPointsBase):
    bl_idname = "maplus.quickapldestswapplaneaplanec"
    bl_label = "Swap Plane Point A with Plane Point C"
    bl_description = "Swap plane points A and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_a', 'plane_pt_c')
    quick_op_target = 'APLDEST'


class QuickAplDestSwapPlaneBPlaneC(SwapPointsBase):
    bl_idname = "maplus.quickapldestswapplanebplanec"
    bl_label = "Swap Plane Point B with Plane Point C"
    bl_description = "Swap plane points B and C"
    bl_options = {'REGISTER', 'UNDO'}
    targets = ('plane_pt_b', 'plane_pt_c')
    quick_op_target = 'APLDEST'


# Every x/y/z coordinate component has these functions on each of the
# geometry primitives (lets users move in one direction easily, etc.)
class SetOtherComponentsBase(bpy.types.Operator):
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


class ZeroOtherPointX(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherpointx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'X', 0)


class ZeroOtherPointY(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherpointy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'Y', 0)


class ZeroOtherPointZ(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherpointz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'Z', 0)


class ZeroOtherLineStartX(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlinestartx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'X', 0)


class ZeroOtherLineStartY(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlinestarty"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'Y', 0)


class ZeroOtherLineStartZ(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlinestartz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'Z', 0)


class ZeroOtherLineEndX(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlineendx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'X', 0)


class ZeroOtherLineEndY(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlineendy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'Y', 0)


class ZeroOtherLineEndZ(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherlineendz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'Z', 0)


class ZeroOtherPlanePointAX(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointax"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'X', 0)


class ZeroOtherPlanePointAY(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointay"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'Y', 0)


class ZeroOtherPlanePointAZ(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointaz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'Z', 0)


class ZeroOtherPlanePointBX(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointbx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'X', 0)


class ZeroOtherPlanePointBY(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointby"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'Y', 0)


class ZeroOtherPlanePointBZ(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointbz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'Z', 0)


class ZeroOtherPlanePointCX(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointcx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'X', 0)


class ZeroOtherPlanePointCY(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointcy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'Y', 0)


class ZeroOtherPlanePointCZ(SetOtherComponentsBase):
    bl_idname = "maplus.zerootherplanepointcz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'Z', 0)


class OneOtherPointX(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherpointx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'X', 1)


class OneOtherPointY(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherpointy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'Y', 1)


class OneOtherPointZ(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherpointz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('point', 'Z', 1)


class OneOtherLineStartX(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlinestartx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'X', 1)


class OneOtherLineStartY(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlinestarty"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'Y', 1)


class OneOtherLineStartZ(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlinestartz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_start', 'Z', 1)


class OneOtherLineEndX(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlineendx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'X', 1)


class OneOtherLineEndY(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlineendy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'Y', 1)


class OneOtherLineEndZ(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherlineendz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('line_end', 'Z', 1)


class OneOtherPlanePointAX(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointax"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'X', 1)


class OneOtherPlanePointAY(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointay"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'Y', 1)


class OneOtherPlanePointAZ(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointaz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_a', 'Z', 1)


class OneOtherPlanePointBX(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointbx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'X', 1)


class OneOtherPlanePointBY(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointby"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'Y', 1)


class OneOtherPlanePointBZ(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointbz"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_b', 'Z', 1)


class OneOtherPlanePointCX(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointcx"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'X', 1)


class OneOtherPlanePointCY(SetOtherComponentsBase):
    bl_idname = "maplus.oneotherplanepointcy"
    bl_label = ""
    bl_description = ""
    bl_options = {'REGISTER', 'UNDO'}
    target_info = ('plane_pt_c', 'Y', 1)


class OneOtherPlanePointCZ(SetOtherComponentsBase):
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


class ApplyGeomModifiers(bpy.types.Operator):
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


class ShowHideQuickGeomBaseClass(bpy.types.Operator):
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


class ShowHideQuickCalcSlot1Geom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickcalcslot1geom"
    bl_label = "Show/hide slot 1 geometry"
    bl_description = "Show/hide slot 1 geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'SLOT1'


class ShowHideQuickCalcSlot2Geom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickcalcslot2geom"
    bl_label = "Show/hide slot 2 geometry"
    bl_description = "Show/hide slot 2 geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'SLOT2'


class ShowHideQuickCalcResultGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickcalcresultgeom"
    bl_label = "Show/hide calculation result geometry"
    bl_description = "Show/hide calculation result geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'CALCRESULT'


class ShowHideQuickAptSrcGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickaptsrcgeom"
    bl_label = "Show/hide quick align points source geometry"
    bl_description = "Show/hide quick align points source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'APTSRC'


class ShowHideQuickAptDestGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickaptdestgeom"
    bl_label = "Show/hide quick align points destination geometry"
    bl_description = "Show/hide quick align points destination geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'APTDEST'


class ShowHideQuickAlnSrcGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickalnsrcgeom"
    bl_label = "Show/hide quick align lines source geometry"
    bl_description = "Show/hide quick align lines source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'ALNSRC'


class ShowHideQuickAlnDestGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickalndestgeom"
    bl_label = "Show/hide quick align lines destination geometry"
    bl_description = "Show/hide quick align lines destination geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'ALNDEST'


class ShowHideQuickAplSrcGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickaplsrcgeom"
    bl_label = "Show/hide quick align planes source geometry"
    bl_description = "Show/hide quick align planes source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'APLSRC'


class ShowHideQuickAplDestGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickapldestgeom"
    bl_label = "Show/hide quick align planes destination geometry"
    bl_description = "Show/hide quick align planes destination geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'APLDEST'


class ShowHideQuickAxrSrcGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickaxrsrcgeom"
    bl_label = "Show/hide quick axis rotate source geometry"
    bl_description = "Show/hide quick axis rotate source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'AXRSRC'


class ShowHideQuickDsSrcGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequickdssrcgeom"
    bl_label = "Show/hide quick directional slide source geometry"
    bl_description = "Show/hide quick directional slide source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'DSSRC'


class ShowHideQuickSmeSrcGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequicksmesrcgeom"
    bl_label = "Show/hide quick scale match edge source geometry"
    bl_description = "Show/hide quick scale match edge source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'SMESRC'


class ShowHideQuickSmeDestGeom(ShowHideQuickGeomBaseClass):
    bl_idname = "maplus.showhidequicksmedestgeom"
    bl_label = "Show/hide quick scale match edge source geometry"
    bl_description = "Show/hide quick scale match edge source geometry"
    bl_options = {'REGISTER', 'UNDO'}
    quick_op_target = 'SMEDEST'
