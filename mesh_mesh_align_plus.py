# ##### BEGIN GPL LICENSE BLOCK #####
#
# Mesh Align Plus-Build precision models using scene geometry/measurements.
# Copyright (C) 2015 Eric Gentry
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####
#
# <pep8 compliant>


# Blender requires addons to provide this information.
bl_info = {
    "name": "Mesh Align Plus",
    "description": (
        "Precisely move mesh parts and objects around "
        "based on geometry and measurements from your scene."
    ),
    "author": "Eric Gentry",
    "version": (0, 4, 0),
    "blender": (2, 69, 0),
    "location": (
        "3D View > Tools, and Properties -> Scene -> Mesh Align Plus"
    ),
    "warning": (
        "Operations on objects with non-uniform scaling are "
        "not currently supported."
    ),
    "wiki_url": (
        "https://github.com/egtwobits/mesh-align-plus/wiki"
    ),
    "support": "COMMUNITY",
    "category": "Mesh"
}


import bpy
import bmesh
import math
import mathutils
import collections


# This is the basic data structure for the addon. The item can be a point,
# line, plane, calc, or transf (only one at a time), chosen by the user
# (defaults to point). A MAPlusPrimitive always has data slots for each of
# these types, regardless of which 'kind' the item is currently
class MAPlusPrimitive(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty(
        name="Item name",
        description="The name of this item",
        default="Name"
    )
    kind = bpy.props.EnumProperty(
        items=[
            ('POINT', 'Point', 'Point Primitive'),
            ('LINE', 'Line', 'Line Primitive'),
            ('PLANE', 'Plane', 'Plane Primitive'),
            ('CALCULATION', 'Calculation', 'Calculation Primitive'),
            ('TRANSFORMATION', 'Transformation', 'Transformation Primitive')
        ],
        name="Item Type",
        default='POINT',
        description="The type of this item"
    )

    # Point primitive data/settings
    # DuplicateItemBase depends on a complete list of these attribs
    point = bpy.props.FloatVectorProperty(
        description="Point primitive coordinates",
        precision=6
    )
    pt_make_unit_vec = bpy.props.BoolProperty(
        description="Treat the point like a vector of length 1"
    )
    pt_flip_direction = bpy.props.BoolProperty(
        description=(
            "Treat the point like a vector pointing in"
            " the opposite direction"
        )
    )
    pt_multiplier = bpy.props.FloatProperty(
        description=(
            "Treat the point like a vector and multiply"
            " its length by this value"
        ),
        default=1.0,
        precision=6
    )

    # Line primitive data/settings
    # DuplicateItemBase depends on a complete list of these attribs
    line_start = bpy.props.FloatVectorProperty(
        description="Line primitive, starting point coordinates",
        precision=6
    )
    line_end = bpy.props.FloatVectorProperty(
        description="Line primitive, ending point coordinates",
        precision=6
    )
    ln_make_unit_vec = bpy.props.BoolProperty(
        description="Make the line's length 1"
    )
    ln_flip_direction = bpy.props.BoolProperty(
        description="Point the line in the opposite direction"
    )
    ln_multiplier = bpy.props.FloatProperty(
        description="Multiply the line's length by this amount",
        default=1.0,
        precision=6
    )

    # Plane primitive data
    # DuplicateItemBase depends on a complete list of these attribs
    plane_pt_a = bpy.props.FloatVectorProperty(
        description="Plane primitive, point A coordinates",
        precision=6
    )
    plane_pt_b = bpy.props.FloatVectorProperty(
        description="Plane primitive, point B coordinates",
        precision=6
    )
    plane_pt_c = bpy.props.FloatVectorProperty(
        description="Plane primitive, point C coordinates",
        precision=6
    )

    # Calculation primitive data/settings
    calc_type = bpy.props.EnumProperty(
        items=[
            ('SINGLEITEM',
             'Single',
             'Single item calculation'),
            ('MULTIITEM',
             'Multi',
             'Multi item calculation')
        ],
        name="Calc. Type",
        description="The type of calculation to perform",
        default='MULTIITEM'
    )
    # active item index for the single item calc list
    single_calc_target = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the item that"
            " the calculation will be based on."
        ),
        default=0
    )
    # active item indices for the multi item calc lists
    multi_calc_target_one = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the first item that"
            " the calculation will be based on."
        ),
        default=0
    )
    multi_calc_target_two = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the second item that"
            " the calculation will be based on."
        ),
        default=0
    )

    single_calc_result = bpy.props.FloatProperty(
        description="Single Item Calc. Result",
        default=0,
        precision=6
    )
    multi_calc_result = bpy.props.FloatProperty(
        description="Multi Item Calc. Result",
        default=0,
        precision=6
    )

    # Transformation primitive data/settings (several blocks)
    transf_type = bpy.props.EnumProperty(
        items=[
            ('ALIGNPOINTS',
             'Align Points',
             'Match source vertex location to destination vertex location'),
            ('DIRECTIONALSLIDE',
             'Directional Slide',
             'Move a target in a direction'),
            ('SCALEMATCHEDGE',
             'Match Edge Scale',
             'Match source edge length to destination edge length'),
            ('ALIGNLINES',
             'Align Lines',
             'Make lines collinear'),
            ('AXISROTATE',
             'Axis Rotate',
             'Rotate around a specified axis'),
            ('ALIGNPLANES',
             'Align Planes',
             'Make planes coplanar'),
            ('UNDEFINED',
             'Undefined',
             'The transformation type has not been set')
        ],
        name="Transf. Type",
        description="The type of transformation to perform",
        default='UNDEFINED'
    )

    # "Align Points" (transformation) data/settings
    apt_pt_one = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the source point"
            " (this point will be 'moved' to match the destination)."
        ),
        default=0
    )
    apt_pt_two = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the destination point"
            " (this is a fixed reference location, where"
            " the source point will be 'moved' to)."
        ),
        default=0
    )
    apt_make_unit_vector = bpy.props.BoolProperty(
        description="Set the move distance equal to one",
        default=False
    )
    apt_flip_direction = bpy.props.BoolProperty(
        description="Flip the move direction",
        default=False
    )
    apt_multiplier = bpy.props.FloatProperty(
        description="Multiply the move by this amount",
        default=1.0,
        precision=6
    )

    # "Align Planes" (transformation) data/settings
    apl_src_plane = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the source plane"
            " (this plane will be 'moved' to match the destination)."
        ),
        default=0
    )
    apl_dest_plane = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the destination plane"
            " (this is a fixed reference location, where"
            " the source plane will be 'moved' to)."
        ),
        default=0
    )
    apl_flip_normal = bpy.props.BoolProperty(
        description="Flips the normal of the source plane",
        default=False
    )
    apl_use_custom_orientation = bpy.props.BoolProperty(
        description=(
            "Switches to custom transform orientation upon applying"
            " the operator (oriented to the destination plane)."
        ),
        default=False
    )

    # "Align Lines" (transformation) data/settings
    aln_src_line = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the source line"
            " (this line will be 'moved' to match the destination)."
        ),
        default=0
    )
    aln_dest_line = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the destination line"
            " (this is a fixed reference location, where"
            " the source line will be 'moved' to)."
        ),
        default=0
    )
    aln_flip_direction = bpy.props.BoolProperty(
        description="Flip the source line direction",
        default=False
    )

    # "Axis rotate" (transformation) data/settings
    axr_axis = bpy.props.IntProperty(
        description="The axis to rotate around",
        default=0
    )
    axr_amount = bpy.props.FloatProperty(
        description=(
            "How much to rotate around the specified axis (in radians)"
        ),
        default=0,
        precision=6
    )

    # "Directional slide" (transformation) data/settings
    ds_direction = bpy.props.IntProperty(
        description="The direction to move",
        default=0
    )  # This is a list item pointer
    ds_make_unit_vec = bpy.props.BoolProperty(
        description="Make the line's length 1",
        default=False
    )
    ds_flip_direction = bpy.props.BoolProperty(
        description="Flip source line direction",
        default=False
    )
    ds_multiplier = bpy.props.FloatProperty(
        description="Multiply the source line's length by this amount",
        default=1.0,
        precision=6
    )

    # "Scale Match Edge" (transformation) data/settings
    sme_edge_one = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the source edge"
            " (this edge will be scaled to match"
            " the destination edge's length)."
        ),
        default=0
    )
    sme_edge_two = bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the destination edge"
            " (this is a fixed reference edge, used to determine"
            " how much to scale the source edge so that its length"
            " matches the length of this edge)."
        ),
        default=0
    )


# Defines one instance of the addon data (one per scene)
class MAPlusData(bpy.types.PropertyGroup):
    prim_list = bpy.props.CollectionProperty(type=MAPlusPrimitive)
    # stores index of active primitive in my UIList
    active_list_item = bpy.props.IntProperty()
    use_experimental = bpy.props.BoolProperty(
        description=(
            'Use experimental:'
            ' Mesh transformations are not currently'
            ' supported on objects with non-uniform'
            ' scaling. These are designated experimental'
            ' until non-uniform scaling is supported.'
        )
    )

    # Items for the quick operators
    quick_align_pts_show = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the align points operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_apt_show_src_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_apt_show_dest_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the destination geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_align_pts_auto_grab_src = bpy.props.BoolProperty(
        description=(
            "Automatically grab source point from selected geometry"
        ),
        default=True
    )
    quick_align_pts_src = bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_pts_dest = bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_pts_transf = bpy.props.PointerProperty(type=MAPlusPrimitive)

    quick_directional_slide_show = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the directional slide operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_ds_show_src_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_directional_slide_auto_grab_src = bpy.props.BoolProperty(
        description=(
            "Automatically grab source line from selected geometry"
        ),
        default=True
    )
    quick_directional_slide_src = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_directional_slide_dest = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_directional_slide_transf = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )

    quick_scale_match_edge_show = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the scale match edge operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_sme_show_src_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_sme_show_dest_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the destination geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_scale_match_edge_auto_grab_src = bpy.props.BoolProperty(
        description=(
            "Automatically grab source line from selected geometry"
        ),
        default=True
    )
    quick_scale_match_edge_src = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_scale_match_edge_dest = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_scale_match_edge_transf = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    # Scale Match Edge numeric mode items
    quick_sme_numeric_mode = bpy.props.BoolProperty(
        description=(
            'Use alternate "Numeric Input" mode to type a target edge'
            ' length in directly.'
        ),
        default=False
    )
    quick_sme_numeric_auto = bpy.props.BoolProperty(
        description=(
            "Automatically grab target line from selected geometry"
        ),
        default=True
    )
    quick_sme_numeric_length = bpy.props.FloatProperty(
        description="Desired length for the target edge",
        default=1,
        precision=6
    )
    quick_sme_numeric_src = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_sme_numeric_dest = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )

    quick_align_lines_show = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the align lines operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_aln_show_src_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_aln_show_dest_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the destination geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_align_lines_auto_grab_src = bpy.props.BoolProperty(
        description=(
            "Automatically grab source line from selected geometry"
        ),
        default=True
    )
    quick_align_lines_src = bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_lines_dest = bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_lines_transf = bpy.props.PointerProperty(type=MAPlusPrimitive)

    quick_axis_rotate_show = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the axis rotate operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_axr_show_src_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_axis_rotate_auto_grab_src = bpy.props.BoolProperty(
        description=(
            "Automatically grab source axis from selected geometry"
        ),
        default=True
    )
    quick_axis_rotate_src = bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_axis_rotate_transf = bpy.props.PointerProperty(type=MAPlusPrimitive)

    quick_align_planes_show = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the align planes operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_apl_show_src_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_apl_show_dest_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the destination geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_align_planes_auto_grab_src = bpy.props.BoolProperty(
        description=(
            "Automatically grab source plane from selected geometry"
        ),
        default=True
    )
    quick_align_planes_src = bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_planes_dest = bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_planes_transf = bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )

    # Calculation global settings
    calc_result_to_clipboard = bpy.props.BoolProperty(
        description=(
            "Copy  calculation results (new reference locations or"
            " numeric calculations) to the addon clipboard or the"
            " system clipboard, respectively."
        ),
        default=True
    )

    # Quick Calculation items
    quick_calc_check_types = bpy.props.BoolProperty(
        description=(
            "Check/verify slot types and disable operations that do not"
            " match the type(s) of the current geometry item slots."
            " Uncheck to silently allow calculations on slot data that is"
            " not currently displayed in the interface."
        ),
        default=True
    )
    quick_calc_show_slot1_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the slot 1 geometry editor"
            " in the calculate/compose panel."
        ),
        default=False
    )
    quick_calc_show_slot2_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the slot 2 geometry editor"
            " in the calculate/compose panel."
        ),
        default=False
    )
    quick_calc_show_result_geom = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the calculation result geometry editor"
            " in the calculate/compose panel."
        ),
        default=False
    )
    quick_calc_result_item = bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_calc_result_numeric = bpy.props.FloatProperty(
        description="Quick Calculation numeric result",
        default=0,
        precision=6
    )
    internal_storage_slot_1 = bpy.props.PointerProperty(type=MAPlusPrimitive)
    internal_storage_slot_2 = bpy.props.PointerProperty(type=MAPlusPrimitive)
    internal_storage_clipboard = bpy.props.PointerProperty(type=MAPlusPrimitive)


# Basic type selector functionality, derived classes provide
# the "kind" to switch to (target_type attrib)
class ChangeTypeBaseClass(bpy.types.Operator):
    # Todo...add dotted groups to bl_idname's
    bl_idname = "maplus.changetypebaseclass"
    bl_label = "Change type base class"
    bl_description = "The base class for changing types"
    bl_options = {'REGISTER', 'UNDO'}
    target_type = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        active_item.kind = self.target_type

        return {'FINISHED'}


class ChangeTypeToPointPrim(ChangeTypeBaseClass):
    bl_idname = "maplus.changetypetopointprim"
    bl_label = "Change this to a point primitive"
    bl_description = "Makes this item a point primitive"
    bl_options = {'REGISTER', 'UNDO'}
    target_type = 'POINT'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.kind == cls.target_type:
            return False
        return True


class ChangeTypeToLinePrim(ChangeTypeBaseClass):
    bl_idname = "maplus.changetypetolineprim"
    bl_label = "Change this to a line primitive"
    bl_description = "Makes this item a line primitive"
    bl_options = {'REGISTER', 'UNDO'}
    target_type = 'LINE'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.kind == cls.target_type:
            return False
        return True


class ChangeTypeToPlanePrim(ChangeTypeBaseClass):
    bl_idname = "maplus.changetypetoplaneprim"
    bl_label = "Change this to a plane primitive"
    bl_description = "Makes this item a plane primitive"
    bl_options = {'REGISTER', 'UNDO'}
    target_type = 'PLANE'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.kind == cls.target_type:
            return False
        return True


class ChangeTypeToCalcPrim(ChangeTypeBaseClass):
    bl_idname = "maplus.changetypetocalcprim"
    bl_label = "Change this to a calculation primitive"
    bl_description = "Makes this item a calculation primitive"
    bl_options = {'REGISTER', 'UNDO'}
    target_type = 'CALCULATION'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.kind == cls.target_type:
            return False
        return True


class ChangeTypeToTransfPrim(ChangeTypeBaseClass):
    bl_idname = "maplus.changetypetotransfprim"
    bl_label = "Change this to a transformation primitive"
    bl_description = "Makes this item a transformation primitive"
    bl_options = {'REGISTER', 'UNDO'}
    target_type = 'TRANSFORMATION'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.kind == cls.target_type:
            return False
        return True


class ChangeCalcBaseClass(bpy.types.Operator):
    bl_idname = "maplus.changecalcbaseclass"
    bl_label = "Change calculation base class"
    bl_description = "The base class for changing calc types"
    bl_options = {'REGISTER', 'UNDO'}
    target_calc = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        active_item.calc_type = self.target_calc

        return {'FINISHED'}


class ChangeCalcToSingle(ChangeCalcBaseClass):
    bl_idname = "maplus.changecalctosingle"
    bl_label = "Change to single item calculation"
    bl_description = "Change the calculation type to single item"
    bl_options = {'REGISTER', 'UNDO'}
    target_calc = 'SINGLEITEM'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.calc_type == cls.target_calc:
            return False
        return True


class ChangeCalcToMulti(ChangeCalcBaseClass):
    bl_idname = "maplus.changecalctomulti"
    bl_label = "Change to multi-item calculation"
    bl_description = "Change the calculation type to multi item"
    bl_options = {'REGISTER', 'UNDO'}
    target_calc = 'MULTIITEM'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.calc_type == cls.target_calc:
            return False
        return True


# Basic transformation type selector functionality (a primitive sub-type),
# derived classes provide the transf. to switch to (target_transf attrib)
class ChangeTransfBaseClass(bpy.types.Operator):
    bl_idname = "maplus.changetransfbaseclass"
    bl_label = "Change transformation base class"
    bl_description = "The base class for changing tranf types"
    bl_options = {'REGISTER', 'UNDO'}
    target_transf = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        active_item.transf_type = self.target_transf

        return {'FINISHED'}


class ChangeTransfToAlignPoints(ChangeTransfBaseClass):
    bl_idname = "maplus.changetransftoalignpoints"
    bl_label = "Change transformation to align points"
    bl_description = "Change the transformation type to align points"
    bl_options = {'REGISTER', 'UNDO'}
    target_transf = 'ALIGNPOINTS'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.transf_type == cls.target_transf:
            return False
        return True


class ChangeTransfToDirectionalSlide(ChangeTransfBaseClass):
    bl_idname = "maplus.changetransftodirectionalslide"
    bl_label = "Change transformation to directional slide"
    bl_description = "Change the transformation type to directional slide"
    bl_options = {'REGISTER', 'UNDO'}
    target_transf = 'DIRECTIONALSLIDE'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.transf_type == cls.target_transf:
            return False
        return True


class ChangeTransfToScaleMatchEdge(ChangeTransfBaseClass):
    bl_idname = "maplus.changetransftoscalematchedge"
    bl_label = "Change transformation to scale match edge"
    bl_description = "Change the transformation type to scale match edge"
    bl_options = {'REGISTER', 'UNDO'}
    target_transf = 'SCALEMATCHEDGE'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.transf_type == cls.target_transf:
            return False
        return True


class ChangeTransfToAxisRotate(ChangeTransfBaseClass):
    bl_idname = "maplus.changetransftoaxisrotate"
    bl_label = "Change transformation to axis rotate"
    bl_description = "Change the transformation type to axis rotate"
    bl_options = {'REGISTER', 'UNDO'}
    target_transf = 'AXISROTATE'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.transf_type == cls.target_transf:
            return False
        return True


class ChangeTransfToAlignLines(ChangeTransfBaseClass):
    bl_idname = "maplus.changetransftoalignlines"
    bl_label = "Change transformation to align lines"
    bl_description = "Change the transformation type to align lines"
    bl_options = {'REGISTER', 'UNDO'}
    target_transf = 'ALIGNLINES'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.transf_type == cls.target_transf:
            return False
        return True


class ChangeTransfToAlignPlanes(ChangeTransfBaseClass):
    bl_idname = "maplus.changetransftoalignplanes"
    bl_label = "Change transformation to align planes"
    bl_description = "Change the transformation type to align planes"
    bl_options = {'REGISTER', 'UNDO'}
    target_transf = 'ALIGNPLANES'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        prims = bpy.context.scene.maplus_data.prim_list
        active_item = prims[addon_data.active_list_item]

        if active_item.transf_type == cls.target_transf:
            return False
        return True


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


# Exception when adding new items, if we can't get a unique name
class UniqueNameError(Exception):
    pass


class AddListItemBase(bpy.types.Operator):
    bl_idname = "maplus.addlistitembase"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}

    def add_new_named(self):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        # Add Name.001 or Name.002 (numbers at the end if the name is
        # already in use)
        name_list = {n.name for n in prims}
        name_counter = 0
        num_postfix_group = 1
        base_name = 'Item'
        cur_item_name = base_name
        num_format = '.{0:0>3}'
        keep_naming = True
        while keep_naming:
            name_counter += 1
            cur_item_name = base_name + num_format.format(str(name_counter))
            if num_postfix_group > 16:
                raise UniqueNameError('Cannot add, unique name error.')
            if name_counter == 999:
                name_counter = 0
                base_name += num_format.format('1')
                num_postfix_group += 1

            if not (base_name in name_list):
                cur_item_name = base_name
                keep_naming = False
                continue
            elif cur_item_name in name_list:
                continue
            else:
                keep_naming = False
                continue

        new_item = addon_data.prim_list.add()
        new_item.name = cur_item_name
        new_item.kind = self.new_kind
        addon_data.active_list_item = len(prims) - 1
        return new_item

    def execute(self, context):
        try:
            self.add_new_named()
        except UniqueNameError:
            self.report({'ERROR'}, 'Cannot add item, unique name error.')
            return {'CANCELLED'}

        return {'FINISHED'}


class AddNewPoint(AddListItemBase):
    bl_idname = "maplus.addnewpoint"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "POINT"


class AddNewLine(AddListItemBase):
    bl_idname = "maplus.addnewline"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "LINE"


class AddNewPlane(AddListItemBase):
    bl_idname = "maplus.addnewplane"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "PLANE"


class AddNewCalculation(AddListItemBase):
    bl_idname = "maplus.addnewcalculation"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "CALCULATION"


class AddNewTransformation(AddListItemBase):
    bl_idname = "maplus.addnewtransformation"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "TRANSFORMATION"


def copy_source_attribs_to_dest(source, dest, set_attribs=None):
    if set_attribs:
        for att in set_attribs:
            setattr(dest, att, getattr(source, att))


class CopyToOtherBase(bpy.types.Operator):
    bl_idname = "maplus.copytootherbase"
    bl_label = "Copy to other"
    bl_description = "Copies this item to a destination"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        # Safely set active advanced tools item values...both the item and the
        # kind are needed to set mapping values, so dummy values are used if
        # the prims collections is empty (avoids access exceptions)
        advanced_tools_active_item = None
        active_kind = 'POINT'
        if 'ADVTOOLSACTIVE' in self.source_dest_pair:
            if len(prims) < 1:
                self.report(
                    {'ERROR'},
                    'No stored geometry items exist to copy.'
                )
                return {'CANCELLED'}
            advanced_tools_active_item = prims[addon_data.active_list_item]
            active_kind = advanced_tools_active_item.kind

        string_to_target_mappings = {
            'APTSRC': {
                "item": addon_data.quick_align_pts_src,
                "geom_mode": 'POINT',
            },
            'APTDEST': {
                "item": addon_data.quick_align_pts_dest,
                "geom_mode": 'POINT',
            },
            'ALNSRC': {
                "item": addon_data.quick_align_lines_src,
                "geom_mode": 'LINE',
            },
            'ALNDEST': {
                "item": addon_data.quick_align_lines_dest,
                "geom_mode": 'LINE',
            },
            'APLSRC': {
                "item": addon_data.quick_align_planes_src,
                "geom_mode": 'PLANE',
            },
            'APLDEST': {
                "item": addon_data.quick_align_planes_dest,
                "geom_mode": 'PLANE',
            },
            'AXRSRC': {
                "item": addon_data.quick_axis_rotate_src,
                "geom_mode": 'LINE',
            },
            'DSSRC': {
                "item": addon_data.quick_directional_slide_src,
                "geom_mode": 'LINE',
            },
            'SMESRC': {
                "item": addon_data.quick_scale_match_edge_src,
                "geom_mode": 'LINE',
            },
            'SMEDEST': {
                "item": addon_data.quick_scale_match_edge_dest,
                "geom_mode": 'LINE',
            },
            'ADVTOOLSACTIVE': {
                "item": advanced_tools_active_item,
                "geom_mode": active_kind,
            },
            'INTERNALCLIPBOARD': {
                "item": addon_data.internal_storage_clipboard,
                "geom_mode": (
                    addon_data.internal_storage_clipboard.kind if
                    addon_data.internal_storage_clipboard.kind in
                    ['POINT', 'LINE', 'PLANE'] else
                    'POINT'
                ),
            },
            'SLOT1': {
                "item": addon_data.internal_storage_slot_1,
                "geom_mode": (
                    addon_data.internal_storage_slot_1.kind if
                    addon_data.internal_storage_slot_1.kind in
                    ['POINT', 'LINE', 'PLANE'] else
                    'POINT'
                ),
            },
            'SLOT2': {
                "item": addon_data.internal_storage_slot_2,
                "geom_mode": (
                    addon_data.internal_storage_slot_2.kind if
                    addon_data.internal_storage_slot_2.kind in
                    ['POINT', 'LINE', 'PLANE'] else
                    'POINT'
                ),
            },
            'CALCRESULT': {
                "item": addon_data.quick_calc_result_item,
                "geom_mode": (
                    addon_data.quick_calc_result_item.kind if
                    addon_data.quick_calc_result_item.kind in
                    ['POINT', 'LINE', 'PLANE'] else
                    'POINT'
                ),
            }
        }
        set_attribs = {
            "POINT": (
                "point",
                "pt_make_unit_vec",
                "pt_flip_direction",
                "pt_multiplier"
            ),
            "LINE": (
                "line_start",
                "line_end",
                "ln_make_unit_vec",
                "ln_flip_direction",
                "ln_multiplier"
            ),
            "PLANE": (
                "plane_pt_a",
                "plane_pt_b",
                "plane_pt_c"
            ),
        }

        source = string_to_target_mappings[self.source_dest_pair[0]]
        dest = string_to_target_mappings[self.source_dest_pair[1]]
        # If internal storage is the destination, the kind needs to be set
        # to the proper value
        if self.source_dest_pair[1] in ['INTERNALCLIPBOARD', 'SLOT1', 'SLOT2']:
            dest["item"].kind = source["geom_mode"]

        copy_source_attribs_to_dest(
            source["item"],
            dest["item"],
            set_attribs[source["geom_mode"]]
        )

        return {'FINISHED'}


class PasteIntoAdvToolsActive(CopyToOtherBase):
    bl_idname = "maplus.pasteintoadvtoolsactive"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'ADVTOOLSACTIVE')


class CopyFromAdvToolsActive(CopyToOtherBase):
    bl_idname = "maplus.copyfromadvtoolsactive"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('ADVTOOLSACTIVE', 'INTERNALCLIPBOARD')


class PasteIntoSlot1(CopyToOtherBase):
    bl_idname = "maplus.pasteintoslot1"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'SLOT1')


class CopyFromSlot1(CopyToOtherBase):
    bl_idname = "maplus.copyfromslot1"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('SLOT1', 'INTERNALCLIPBOARD')


class PasteIntoSlot2(CopyToOtherBase):
    bl_idname = "maplus.pasteintoslot2"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'SLOT2')


class CopyFromSlot2(CopyToOtherBase):
    bl_idname = "maplus.copyfromslot2"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('SLOT2', 'INTERNALCLIPBOARD')


class CopyFromCalcResult(CopyToOtherBase):
    bl_idname = "maplus.copyfromcalcresult"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('CALCRESULT', 'INTERNALCLIPBOARD')


class PasteIntoCalcResult(CopyToOtherBase):
    bl_idname = "maplus.pasteintocalcresult"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'CALCRESULT')


class PasteIntoAptSrc(CopyToOtherBase):
    bl_idname = "maplus.pasteintoaptsrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'APTSRC')


class CopyFromAptSrc(CopyToOtherBase):
    bl_idname = "maplus.copyfromaptsrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('APTSRC', 'INTERNALCLIPBOARD')


class PasteIntoAptDest(CopyToOtherBase):
    bl_idname = "maplus.pasteintoaptdest"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'APTDEST')


class CopyFromAptDest(CopyToOtherBase):
    bl_idname = "maplus.copyfromaptdest"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('APTDEST', 'INTERNALCLIPBOARD')


class PasteIntoAlnSrc(CopyToOtherBase):
    bl_idname = "maplus.pasteintoalnsrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'ALNSRC')


class CopyFromAlnSrc(CopyToOtherBase):
    bl_idname = "maplus.copyfromalnsrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('ALNSRC', 'INTERNALCLIPBOARD')


class PasteIntoAlnDest(CopyToOtherBase):
    bl_idname = "maplus.pasteintoalndest"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'ALNDEST')


class CopyFromAlnDest(CopyToOtherBase):
    bl_idname = "maplus.copyfromalndest"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('ALNDEST', 'INTERNALCLIPBOARD')


class PasteIntoAplSrc(CopyToOtherBase):
    bl_idname = "maplus.pasteintoaplsrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'APLSRC')


class CopyFromAplSrc(CopyToOtherBase):
    bl_idname = "maplus.copyfromaplsrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('APLSRC', 'INTERNALCLIPBOARD')


class PasteIntoAplDest(CopyToOtherBase):
    bl_idname = "maplus.pasteintoapldest"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'APLDEST')


class CopyFromAplDest(CopyToOtherBase):
    bl_idname = "maplus.copyfromapldest"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('APLDEST', 'INTERNALCLIPBOARD')


class PasteIntoAxrSrc(CopyToOtherBase):
    bl_idname = "maplus.pasteintoaxrsrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'AXRSRC')


class CopyFromAxrSrc(CopyToOtherBase):
    bl_idname = "maplus.copyfromaxrsrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('AXRSRC', 'INTERNALCLIPBOARD')


class PasteIntoDsSrc(CopyToOtherBase):
    bl_idname = "maplus.pasteintodssrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'DSSRC')


class CopyFromDsSrc(CopyToOtherBase):
    bl_idname = "maplus.copyfromdssrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('DSSRC', 'INTERNALCLIPBOARD')


class PasteIntoSmeSrc(CopyToOtherBase):
    bl_idname = "maplus.pasteintosmesrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'SMESRC')


class CopyFromSmeSrc(CopyToOtherBase):
    bl_idname = "maplus.copyfromsmesrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('SMESRC', 'INTERNALCLIPBOARD')


class PasteIntoSmeDest(CopyToOtherBase):
    bl_idname = "maplus.pasteintosmedest"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'SMEDEST')


class CopyFromSmeDest(CopyToOtherBase):
    bl_idname = "maplus.copyfromsmedest"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('SMEDEST', 'INTERNALCLIPBOARD')


class DuplicateItemBase(bpy.types.Operator):
    bl_idname = "maplus.duplicateitembase"
    bl_label = "Duplicate Item"
    bl_description = "Duplicates this item"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        self.new_kind = active_item.kind

        if active_item.kind not in {'POINT', 'LINE', 'PLANE'}:
            self.report(
                {'ERROR'},
                ('Wrong operand: "Duplicate Item" can only operate on'
                 ' geometry items')
            )
            return {'CANCELLED'}

        try:
            new_item = AddListItemBase.add_new_named(self)
        except UniqueNameError:
            self.report({'ERROR'}, 'Cannot add item, unique name error.')
            return {'CANCELLED'}

        new_item.kind = self.new_kind

        attrib_copy = {
            "POINT": (
                "point",
                "pt_make_unit_vec",
                "pt_flip_direction",
                "pt_multiplier"
            ),
            "LINE": (
                "line_start",
                "line_end",
                "ln_make_unit_vec",
                "ln_flip_direction",
                "ln_multiplier"
            ),
            "PLANE": (
                "plane_pt_a",
                "plane_pt_b",
                "plane_pt_c"
            ),
        }
        if active_item.kind in attrib_copy:
            for att in attrib_copy[active_item.kind]:
                setattr(new_item, att, getattr(active_item, att))

        return {'FINISHED'}


class RemoveListItem(bpy.types.Operator):
    bl_idname = "maplus.removelistitem"
    bl_label = "Remove an item"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        if len(prims) == 0:
            self.report({'WARNING'}, "Nothing to remove")
            return {'CANCELLED'}
        else:
            prims.remove(addon_data.active_list_item)
            if len(prims) == 0 or addon_data.active_list_item == 0:
                # ^ The extra or prevents act=0 from going to the else below
                addon_data.active_list_item = 0
            elif addon_data.active_list_item > (len(prims) - 1):
                addon_data.active_list_item = len(prims) - 1
            else:
                addon_data.active_list_item -= 1

        return {'FINISHED'}


class SpecialsAddFromActiveBase(bpy.types.Operator):
    bl_idname = "maplus.specialsaddfromactivebase"
    bl_label = "Specials Menu Item Base Class, Add Geometry Item From Active"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = None
    vert_attribs_to_set = None
    multiply_by_world_matrix = None
    message_geom_type = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        try:
            vert_data = return_selected_verts(
                bpy.context.active_object,
                len(self.vert_attribs_to_set),
                bpy.context.active_object.matrix_world
            )
        except InsufficientSelectionError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except NonMeshGrabError:
            self.report(
                {'ERROR'},
                'Cannot grab coords: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        target_data = dict(zip(self.vert_attribs_to_set, vert_data))
        try:
            new_item = AddListItemBase.add_new_named(self)
        except UniqueNameError:
            self.report({'ERROR'}, 'Cannot add item, unique name error.')
            return {'CANCELLED'}
        new_item.kind = self.new_kind

        for key, val in target_data.items():
            setattr(new_item, key, val)

        self.report(
            {'INFO'},
            '{0} \'{1}\' was added'.format(
                self.message_geom_type,
                new_item.name
            )
        )
        return {'FINISHED'}


class SpecialsAddPointFromActiveGlobal(SpecialsAddFromActiveBase):
    bl_idname = "maplus.specialsaddpointfromactiveglobal"
    bl_label = "Point From Active Global"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = 'POINT'
    message_geom_type = 'Point'
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True


class SpecialsAddLineFromActiveGlobal(SpecialsAddFromActiveBase):
    bl_idname = "maplus.specialsaddlinefromactiveglobal"
    bl_label = "Line From Active Global"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = 'LINE'
    message_geom_type = 'Line'
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True


class SpecialsAddPlaneFromActiveGlobal(SpecialsAddFromActiveBase):
    bl_idname = "maplus.specialsaddplanefromactiveglobal"
    bl_label = "Plane From Active Global"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = 'PLANE'
    message_geom_type = 'Plane'
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True


class NonMeshGrabError(Exception):
    pass


class InsufficientSelectionError(Exception):
    pass


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
                coords = global_matrix_multiplier * coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)

        for vert in (v for v in src_mesh.verts if v.select):
            if len(selection) == verts_to_grab:
                break
            coords = vert.co
            if global_matrix_multiplier:
                coords = global_matrix_multiplier * coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)

        if len(selection) == verts_to_grab:
            return selection
        else:
            raise InsufficientSelectionError()
    else:
        raise NonMeshGrabError(mesh_object)


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
            raise InsufficientSelectionError()
        if global_matrix_multiplier:
            face_normal_origin = (
                global_matrix_multiplier *
                face_elems[0].calc_center_median()
            )
            face_normal_endpoint = (
                global_matrix_multiplier *
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
        raise NonMeshGrabError(mesh_object)


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
        for vert in (v for v in src_mesh.verts if v.select):
            coords = vert.co
            if global_matrix_multiplier:
                coords = global_matrix_multiplier * coords
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
            raise NotEnoughVertsError()
    else:
        raise NonMeshGrabError(mesh_object)


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
                coords = global_matrix_multiplier * coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)
        for vert in (v for v in src_mesh.verts if v.select):
            if len(selection) == 3:
                break
            coords = vert.co
            if global_matrix_multiplier:
                coords = global_matrix_multiplier * coords
            if not (vert.index in vert_indices):
                vert_indices.append(vert.index)
                selection.append(coords)

        if len(selection) > 0:
            return selection
        else:
            raise InsufficientSelectionError()
    else:
        raise NonMeshGrabError(mesh_object)


def set_item_coords(item, coords_to_set, coords):
    target_data = collections.OrderedDict(
        zip(coords_to_set, coords)
    )
    for key, val in target_data.items():
        setattr(item, key, val)
    return True


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
            matrix_multiplier = bpy.context.active_object.matrix_world
        try:
            vert_data = return_selected_verts(
                bpy.context.active_object,
                len(self.vert_attribs_to_set),
                matrix_multiplier
            )
        except InsufficientSelectionError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except NonMeshGrabError:
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
            matrix_multiplier = bpy.context.active_object.matrix_world
        try:
            vert_data = return_selected_verts(
                bpy.context.active_object,
                len(self.vert_attribs_to_set),
                matrix_multiplier
            )
        except InsufficientSelectionError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except NonMeshGrabError:
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
            matrix_multiplier = bpy.context.active_object.matrix_world
        try:
            vert_data = return_at_least_one_selected_vert(
                bpy.context.active_object,
                matrix_multiplier
            )
        except InsufficientSelectionError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except NonMeshGrabError:
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
            matrix_multiplier = bpy.context.active_object.matrix_world
        try:
            vert_data = return_avg_vert_pos(
                bpy.context.active_object,
                matrix_multiplier
            )
        except NotEnoughVertsError:
            self.report({'ERROR'}, 'Not enough vertices selected.')
            return {'CANCELLED'}
        except NonMeshGrabError:
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
            matrix_multiplier = bpy.context.active_object.matrix_world
        try:
            vert_data = return_normal_coords(
                bpy.context.active_object,
                matrix_multiplier
            )
        except InsufficientSelectionError:
            self.report(
                {'ERROR'},
                'Select at least one face to grab a face normal.'
            )
            return {'CANCELLED'}
        except NonMeshGrabError:
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
        previous_mode = bpy.context.active_object.mode
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


class ScaleMatchEdgeBase(bpy.types.Operator):
    bl_idname = "maplus.scalematchedgebase"
    bl_label = "Scale Match Edge Base"
    bl_description = "Scale match edge base class"
    bl_options = {'REGISTER', 'UNDO'}
    target = None

    def execute(self, context):
        if not (bpy.context.active_object and bpy.context.active_object.select):
            self.report(
                {'ERROR'},
                'Cannot complete: need at least one active (and selected) object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = bpy.context.active_object.mode
        if hasattr(self, "quick_op_target"):
            active_item = addon_data.quick_scale_match_edge_transf
        else:
            active_item = prims[addon_data.active_list_item]

        if (bpy.context.active_object and
                type(bpy.context.active_object.data) == bpy.types.Mesh):

            if not hasattr(self, "quick_op_target"):
                if (prims[active_item.sme_edge_one].kind != 'LINE' or
                        prims[active_item.sme_edge_two].kind != 'LINE'):
                    self.report(
                        {'ERROR'},
                        ('Wrong operands: "Scale Match Edge" can only'
                         ' operate on two lines')
                    )
                    return {'CANCELLED'}

            if previous_mode != 'EDIT':
                bpy.ops.object.editmode_toggle()
            else:
                # else we could already be in edit mode with some stale
                # updates, exiting and reentering forces an update
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()

            # Get global coordinate data for each geometry item, with
            # applicable modifiers applied. Grab either (A) directly from
            # the scene data (for quick ops), (B) from the MAPlus primitives
            # CollectionProperty on the scene data (for advanced tools), or
            # (C) from the selected verts directly for numeric input mode
            if hasattr(self, "quick_op_target"):
                # Numeric mode is part of this op's quick tools
                if addon_data.quick_sme_numeric_mode:
                    if addon_data.quick_sme_numeric_auto:
                        vert_attribs_to_set = ('line_start', 'line_end')
                        try:
                            vert_data = return_selected_verts(
                                bpy.context.active_object,
                                len(vert_attribs_to_set),
                                bpy.context.active_object.matrix_world
                            )
                        except InsufficientSelectionError:
                            self.report({'ERROR'}, 'Not enough vertices selected.')
                            return {'CANCELLED'}
                        except NonMeshGrabError:
                            self.report(
                                {'ERROR'},
                                'Cannot grab coords: non-mesh or no active object.'
                            )
                            return {'CANCELLED'}

                        set_item_coords(
                            addon_data.quick_sme_numeric_src,
                            vert_attribs_to_set,
                            vert_data
                        )
                        set_item_coords(
                            addon_data.quick_sme_numeric_dest,
                            vert_attribs_to_set,
                            vert_data
                        )

                    addon_data.quick_sme_numeric_dest.ln_make_unit_vec = (
                        True
                    )
                    addon_data.quick_sme_numeric_dest.ln_multiplier = (
                        addon_data.quick_sme_numeric_length
                    )

                    src_global_data = get_modified_global_coords(
                        geometry=addon_data.quick_sme_numeric_src,
                        kind='LINE'
                    )
                    dest_global_data = get_modified_global_coords(
                        geometry=addon_data.quick_sme_numeric_dest,
                        kind='LINE'
                    )

                # Non-numeric (normal quick op) mode
                else:
                    if addon_data.quick_scale_match_edge_auto_grab_src:
                        vert_attribs_to_set = ('line_start', 'line_end')
                        try:
                            vert_data = return_selected_verts(
                                bpy.context.active_object,
                                len(vert_attribs_to_set),
                                bpy.context.active_object.matrix_world
                            )
                        except InsufficientSelectionError:
                            self.report({'ERROR'}, 'Not enough vertices selected.')
                            return {'CANCELLED'}
                        except NonMeshGrabError:
                            self.report(
                                {'ERROR'},
                                'Cannot grab coords: non-mesh or no active object.'
                            )
                            return {'CANCELLED'}

                        set_item_coords(
                            addon_data.quick_scale_match_edge_src,
                            vert_attribs_to_set,
                            vert_data
                        )

                    src_global_data = get_modified_global_coords(
                        geometry=addon_data.quick_scale_match_edge_src,
                        kind='LINE'
                    )
                    dest_global_data = get_modified_global_coords(
                        geometry=addon_data.quick_scale_match_edge_dest,
                        kind='LINE'
                    )

            # Else, operate on data from the advanced tools
            else:
                src_global_data = get_modified_global_coords(
                    geometry=prims[active_item.sme_edge_one],
                    kind='LINE'
                )
                dest_global_data = get_modified_global_coords(
                    geometry=prims[active_item.sme_edge_two],
                    kind='LINE'
                )

            # These global point coordinate vectors will be used to construct
            # geometry and transformations in both object (global) space
            # and mesh (local) space
            src_start = src_global_data[0]
            src_end = src_global_data[1]

            dest_start = dest_global_data[0]
            dest_end = dest_global_data[1]

            # create common vars needed for object and for mesh
            # level transforms
            active_obj_transf = bpy.context.active_object.matrix_world.copy()
            inverse_active = active_obj_transf.copy()
            inverse_active.invert()

            # Construct vectors for each edge from the global point coord data
            src_edge = src_end - src_start
            dest_edge = dest_end - dest_start

            if dest_edge.length == 0 or src_edge.length == 0:
                self.report(
                    {'ERROR'},
                    'Divide by zero error: zero length edge encountered'
                )
                return {'CANCELLED'}
            scale_factor = dest_edge.length/src_edge.length

            multi_edit_targets = [
                model for model in bpy.context.scene.objects if (
                    model.select and model.type == 'MESH'
                )
            ]
            if self.target == 'OBJECT':
                for item in multi_edit_targets:
                    # Get the object world matrix before we modify it here
                    item_matrix_unaltered = item.matrix_world.copy()
                    unaltered_inverse = item_matrix_unaltered.copy()
                    unaltered_inverse.invert()

                    # (Note that there are no transformation modifiers for this
                    # transformation type, so that section is omitted here)
                    item.scale = [
                        scale_factor * num
                        for num in item.scale
                    ]
                    bpy.context.scene.update()

                    # put the original line starting point (before the object
                    # was transformed) into the local object space
                    src_pivot_location_local = unaltered_inverse * src_start

                    # get final global position of pivot (source line
                    # start coords) after object rotation
                    new_global_src_pivot_coords = (
                        item.matrix_world *
                        src_pivot_location_local
                    )

                    # get translation, new to old (original) pivot location
                    new_to_old_pivot = (
                        src_start - new_global_src_pivot_coords
                    )

                    item.location = (
                       item.location + new_to_old_pivot
                    )
                    bpy.context.scene.update()

            else:
                for item in multi_edit_targets:
                    # (Note that there are no transformation modifiers for this
                    # transformation type, so that section is omitted here)
                    self.report(
                        {'WARNING'},
                        ('Warning/Experimental: mesh transforms'
                         ' on objects with non-uniform scaling'
                         ' are not currently supported.')
                    )

                    # Init source mesh
                    src_mesh = bmesh.new()
                    src_mesh.from_mesh(item.data)

                    item_matrix_unaltered_loc = item.matrix_world.copy()
                    unaltered_inverse_loc = item_matrix_unaltered_loc.copy()
                    unaltered_inverse_loc.invert()

                    # Stored geom data in local coords
                    src_start_loc = unaltered_inverse_loc * src_start
                    src_end_loc = unaltered_inverse_loc * src_end

                    dest_start_loc = unaltered_inverse_loc * dest_start
                    dest_end_loc = unaltered_inverse_loc * dest_end

                    # Construct vectors for each line in local space
                    loc_src_line = src_end_loc - src_start_loc
                    loc_dest_line = dest_end_loc - dest_start_loc

                    # Get the scale match matrix
                    scaling_match = mathutils.Matrix.Scale(
                        scale_factor,
                        4
                    )

                    # Get the new pivot location
                    new_pivot_location_loc = scaling_match * src_start_loc

                    # Get the translation, new to old pivot location
                    new_to_old_pivot_vec = (
                        src_start_loc - new_pivot_location_loc
                    )
                    new_to_old_pivot = mathutils.Matrix.Translation(
                        new_to_old_pivot_vec
                    )

                    # Get combined scale + move
                    match_transf = new_to_old_pivot * scaling_match

                    if self.target == 'MESHSELECTED':
                        src_mesh.transform(
                            match_transf,
                            filter={'SELECT'}
                        )
                    elif self.target == 'WHOLEMESH':
                        src_mesh.transform(match_transf)

                    # write and then release the mesh data
                    bpy.ops.object.mode_set(mode='OBJECT')
                    src_mesh.to_mesh(item.data)
                    src_mesh.free()

            # Go back to whatever mode we were in before doing this
            bpy.ops.object.mode_set(mode=previous_mode)

        else:
            self.report(
                {'ERROR'},
                'Cannot transform: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class ScaleMatchEdgeObject(ScaleMatchEdgeBase):
    bl_idname = "maplus.scalematchedgeobject"
    bl_label = "Scale Match Edge Object"
    bl_description = (
        "Scale source object so that source edge matches length of dest edge"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class QuickScaleMatchEdgeObject(ScaleMatchEdgeBase):
    bl_idname = "maplus.quickscalematchedgeobject"
    bl_label = "Scale Match Edge Object"
    bl_description = (
        "Scale source object so that source edge matches length of dest edge"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class ScaleMatchEdgeMeshSelected(ScaleMatchEdgeBase):
    bl_idname = "maplus.scalematchedgemeshselected"
    bl_label = "Scale Match Edge Mesh Selected"
    bl_description = (
        "Scale source mesh piece so that source edge matches length "
        "of dest edge"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickScaleMatchEdgeMeshSelected(ScaleMatchEdgeBase):
    bl_idname = "maplus.quickscalematchedgemeshselected"
    bl_label = "Scale Match Edge Whole Mesh"
    bl_description = (
        "Scale source (whole) mesh so that source edge matches length "
        "of dest edge"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class ScaleMatchEdgeWholeMesh(ScaleMatchEdgeBase):
    bl_idname = "maplus.scalematchedgewholemesh"
    bl_label = "Scale Match Edge Whole Mesh"
    bl_description = (
        "Scale source (whole) mesh so that source edge matches length "
        "of dest edge"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickScaleMatchEdgeWholeMesh(ScaleMatchEdgeBase):
    bl_idname = "maplus.quickscalematchedgewholemesh"
    bl_label = "Scale Match Edge Whole Mesh"
    bl_description = (
        "Scale source (whole) mesh so that source edge matches length "
        "of dest edge"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class AlignPointsBase(bpy.types.Operator):
    bl_idname = "maplus.alignpointsbase"
    bl_label = "Align Points Base"
    bl_description = "Align points base class"
    bl_options = {'REGISTER', 'UNDO'}
    target = None

    def execute(self, context):
        if not (bpy.context.active_object and bpy.context.active_object.select):
            self.report(
                {'ERROR'},
                'Cannot complete: need at least one active (and selected) object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = bpy.context.active_object.mode
        if not hasattr(self, "quick_op_target"):
            active_item = prims[addon_data.active_list_item]
        else:
            active_item = addon_data.quick_align_pts_transf

        if (bpy.context.active_object and
                type(bpy.context.active_object.data) == bpy.types.Mesh):

            # todo: use a bool check and put on all derived classes
            # instead of hasattr
            if not hasattr(self, 'quick_op_target'):
                if (prims[active_item.apt_pt_one].kind != 'POINT' or
                        prims[active_item.apt_pt_two].kind != 'POINT'):
                    self.report(
                        {'ERROR'},
                        ('Wrong operands: "Align Points" can only operate on '
                         'two points')
                    )
                    return {'CANCELLED'}

            # a bmesh can only be initialized in edit mode...todo/better way?
            if previous_mode != 'EDIT':
                bpy.ops.object.editmode_toggle()
            else:
                # else we could already be in edit mode with some stale
                # updates, exiting and reentering forces an update
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()

            # Get global coordinate data for each geometry item, with
            # modifiers applied. Grab either directly from the scene data
            # (for quick ops), or from the MAPlus primitives
            # CollectionProperty on the scene data (for advanced tools)
            if hasattr(self, 'quick_op_target'):
                if addon_data.quick_align_pts_auto_grab_src:
                    vert_attribs_to_set = ('point',)
                    try:
                        vert_data = return_selected_verts(
                            bpy.context.active_object,
                            len(vert_attribs_to_set),
                            bpy.context.active_object.matrix_world
                        )
                    except InsufficientSelectionError:
                        self.report({'ERROR'}, 'Not enough vertices selected.')
                        return {'CANCELLED'}
                    except NonMeshGrabError:
                        self.report(
                            {'ERROR'},
                            'Cannot grab coords: non-mesh or no active object.'
                        )
                        return {'CANCELLED'}

                    set_item_coords(
                        addon_data.quick_align_pts_src,
                        vert_attribs_to_set,
                        vert_data
                    )

                src_global_data = get_modified_global_coords(
                    geometry=addon_data.quick_align_pts_src,
                    kind='POINT'
                )
                dest_global_data = get_modified_global_coords(
                    geometry=addon_data.quick_align_pts_dest,
                    kind='POINT'
                )

            else:
                src_global_data = get_modified_global_coords(
                    geometry=prims[active_item.apt_pt_one],
                    kind='POINT'
                )
                dest_global_data = get_modified_global_coords(
                    geometry=prims[active_item.apt_pt_two],
                    kind='POINT'
                )

            # These global point coordinate vectors will be used to construct
            # geometry and transformations in both object (global) space
            # and mesh (local) space
            src_pt = src_global_data[0]
            dest_pt = dest_global_data[0]

            # create common vars needed for object and for mesh level transfs
            active_obj_transf = bpy.context.active_object.matrix_world.copy()
            inverse_active = active_obj_transf.copy()
            inverse_active.invert()

            multi_edit_targets = [
                model for model in bpy.context.scene.objects if (
                    model.select and model.type == 'MESH'
                )
            ]
            if self.target == 'OBJECT':
                for item in multi_edit_targets:
                    align_points = dest_pt - src_pt

                    # Take modifiers on the transformation item into account,
                    # in global (object) space
                    if active_item.apt_make_unit_vector:
                        align_points.normalize()
                    if active_item.apt_flip_direction:
                        align_points.negate()
                    align_points *= active_item.apt_multiplier

                    item.location += align_points

            else:
                for item in multi_edit_targets:
                    self.report(
                        {'WARNING'},
                        ('Warning/Experimental: mesh transforms'
                         ' on objects with non-uniform scaling'
                         ' are not currently supported.')
                    )
                    # Init source mesh
                    src_mesh = bmesh.new()
                    src_mesh.from_mesh(item.data)

                    # Stored geom data in local coords
                    src_pt_loc = inverse_active * src_pt
                    dest_pt_loc = inverse_active * dest_pt

                    # Get translation vector (in local space), src to dest
                    align_points_vec = dest_pt_loc - src_pt_loc

                    # Take modifiers on the transformation item into account,
                    # in local (mesh) space
                    if active_item.apt_make_unit_vector:
                        # There are special considerations for this modifier
                        # since we need to achieve a global length of
                        # one, but can only transform it in local space
                        # (NOTE: assumes only uniform scaling on the
                        # active object)
                        scaling_factor = 1.0 / item.scale[0]
                        align_points_vec.normalize()
                        align_points_vec *= scaling_factor
                    if active_item.apt_flip_direction:
                        align_points_vec.negate()
                    align_points_vec *= active_item.apt_multiplier

                    align_points_loc = mathutils.Matrix.Translation(
                        align_points_vec
                    )

                    if self.target == 'MESHSELECTED':
                        src_mesh.transform(
                            align_points_loc,
                            filter={'SELECT'}
                        )
                    elif self.target == 'WHOLEMESH':
                        src_mesh.transform(align_points_loc)

                    # write and then release the mesh data
                    bpy.ops.object.mode_set(mode='OBJECT')
                    src_mesh.to_mesh(item.data)
                    src_mesh.free()

            # Go back to whatever mode we were in before doing this
            bpy.ops.object.mode_set(mode=previous_mode)

        else:
            self.report(
                {'ERROR'},
                'Cannot transform: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class AlignPointsObject(AlignPointsBase):
    bl_idname = "maplus.alignpointsobject"
    bl_label = "Align Points Object"
    bl_description = (
        "Match the location of one vertex on a mesh object to another"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class QuickAlignPointsObject(AlignPointsBase):
    bl_idname = "maplus.quickalignpointsobject"
    bl_label = "Quick Align Points Object"
    bl_description = (
        "Match the location of one vertex on a mesh object to another"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class AlignPointsMeshSelected(AlignPointsBase):
    bl_idname = "maplus.alignpointsmeshselected"
    bl_label = "Align Points Mesh Selected"
    bl_description = (
        "Match the location of one vertex on a mesh piece "
        "(the selected verts) to another"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAlignPointsMeshSelected(AlignPointsBase):
    bl_idname = "maplus.quickalignpointsmeshselected"
    bl_label = "Quick Align Points Mesh Selected"
    bl_description = (
        "Match the location of one vertex on a mesh piece "
        "(the selected verts) to another"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class AlignPointsWholeMesh(AlignPointsBase):
    bl_idname = "maplus.alignpointswholemesh"
    bl_label = "Align Points Whole Mesh"
    bl_description = "Match the location of one vertex on a mesh to another"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAlignPointsWholeMesh(AlignPointsBase):
    bl_idname = "maplus.quickalignpointswholemesh"
    bl_label = "Quick Align Points Whole Mesh"
    bl_description = "Match the location of one vertex on a mesh to another"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class DirectionalSlideBase(bpy.types.Operator):
    bl_idname = "maplus.directionalslidebase"
    bl_label = "Directional Slide Base"
    bl_description = "Directional slide base class"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not (bpy.context.active_object and bpy.context.active_object.select):
            self.report(
                {'ERROR'},
                'Cannot complete: need at least one active (and selected) object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = bpy.context.active_object.mode
        if not hasattr(self, "quick_op_target"):
            active_item = prims[addon_data.active_list_item]
        else:
            active_item = addon_data.quick_directional_slide_transf

        if (bpy.context.active_object and
                type(bpy.context.active_object.data) == bpy.types.Mesh):

            if not hasattr(self, "quick_op_target"):
                if prims[active_item.ds_direction].kind != 'LINE':
                    self.report(
                        {'ERROR'},
                        'Wrong operand: "Directional Slide" can'
                        ' only operate on a line'
                    )
                    return {'CANCELLED'}

            # a bmesh can only be initialized in edit mode...
            if previous_mode != 'EDIT':
                bpy.ops.object.editmode_toggle()
            else:
                # else we could already be in edit mode with some stale
                # updates, exiting and reentering forces an update
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()

            # Get global coordinate data for each geometry item, with
            # modifiers applied. Grab either directly from the scene data
            # (for quick ops), or from the MAPlus primitives
            # CollectionProperty on the scene data (for advanced tools)
            if hasattr(self, 'quick_op_target'):
                if addon_data.quick_directional_slide_auto_grab_src:
                    vert_attribs_to_set = ('line_start', 'line_end')
                    try:
                        vert_data = return_selected_verts(
                            bpy.context.active_object,
                            len(vert_attribs_to_set),
                            bpy.context.active_object.matrix_world
                        )
                    except InsufficientSelectionError:
                        self.report({'ERROR'}, 'Not enough vertices selected.')
                        return {'CANCELLED'}
                    except NonMeshGrabError:
                        self.report(
                            {'ERROR'},
                            'Cannot grab coords: non-mesh or no active object.'
                        )
                        return {'CANCELLED'}

                    set_item_coords(
                        addon_data.quick_directional_slide_src,
                        vert_attribs_to_set,
                        vert_data
                    )

                src_global_data = get_modified_global_coords(
                    geometry=addon_data.quick_directional_slide_src,
                    kind='LINE'
                )

            else:
                src_global_data = get_modified_global_coords(
                    geometry=prims[active_item.ds_direction],
                    kind='LINE'
                )

            # These global point coordinate vectors will be used to construct
            # geometry and transformations in both object (global) space
            # and mesh (local) space
            dir_start = src_global_data[0]
            dir_end = src_global_data[1]

            # create common vars needed for object and for mesh level transfs
            active_obj_transf = bpy.context.active_object.matrix_world.copy()
            inverse_active = active_obj_transf.copy()
            inverse_active.invert()

            multi_edit_targets = [
                model for model in bpy.context.scene.objects if (
                    model.select and model.type == 'MESH'
                )
            ]
            if self.target == 'OBJECT':
                for item in multi_edit_targets:
                    # Make the vector specifying the direction and
                    # magnitude to slide in
                    direction = dir_end - dir_start

                    # Take modifiers on the transformation item into account,
                    # in global (object) space
                    if active_item.ds_make_unit_vec:
                        direction.normalize()
                    if active_item.ds_flip_direction:
                        direction.negate()
                    direction *= active_item.ds_multiplier

                    item.location += direction

            else:
                for item in multi_edit_targets:
                    self.report(
                        {'WARNING'},
                        ('Warning/Experimental: mesh transforms'
                         ' on objects with non-uniform scaling'
                         ' are not currently supported.')
                    )
                    # Init source mesh
                    src_mesh = bmesh.new()
                    src_mesh.from_mesh(item.data)

                    # Get the object world matrix
                    item_matrix_unaltered_loc = item.matrix_world.copy()
                    unaltered_inverse_loc = item_matrix_unaltered_loc.copy()
                    unaltered_inverse_loc.invert()

                    # Stored geom data in local coords
                    dir_start_loc = unaltered_inverse_loc * dir_start
                    dir_end_loc = unaltered_inverse_loc * dir_end

                    # Get translation vector in local space
                    direction_loc = dir_end_loc - dir_start_loc

                    # Take modifiers on the transformation item into account,
                    # in local (mesh) space
                    if active_item.ds_make_unit_vec:
                        # There are special considerations for this modifier
                        # since we need to achieve a global length of
                        # one, but can only transform it in local space
                        # (NOTE: assumes only uniform scaling on the
                        # active object)
                        scaling_factor = 1.0 / item.scale[0]
                        direction_loc.normalize()
                        direction_loc *= scaling_factor
                    if active_item.ds_flip_direction:
                        direction_loc.negate()
                    direction_loc *= active_item.ds_multiplier
                    dir_slide = mathutils.Matrix.Translation(direction_loc)

                    if self.target == 'MESHSELECTED':
                        src_mesh.transform(
                            dir_slide,
                            filter={'SELECT'}
                        )
                    elif self.target == 'WHOLEMESH':
                        src_mesh.transform(dir_slide)

                    # write and then release the mesh data
                    bpy.ops.object.mode_set(mode='OBJECT')
                    src_mesh.to_mesh(item.data)
                    src_mesh.free()

            # Go back to whatever mode we were in before doing this
            bpy.ops.object.mode_set(mode=previous_mode)

        else:
            self.report(
                {'ERROR'},
                'Cannot transform: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class DirectionalSlideObject(DirectionalSlideBase):
    bl_idname = "maplus.directionalslideobject"
    bl_label = "Directional Slide Object"
    bl_description = "Translates a target object (moves in a direction)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class QuickDirectionalSlideObject(DirectionalSlideBase):
    bl_idname = "maplus.quickdirectionalslideobject"
    bl_label = "Directional Slide Object"
    bl_description = "Translates a target object (moves in a direction)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class DirectionalSlideMeshSelected(DirectionalSlideBase):
    bl_idname = "maplus.directionalslidemeshselected"
    bl_label = "Directional Slide Mesh Piece"
    bl_description = (
        "Translates a target mesh piece (moves selected verts in a direction)"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class DirectionalSlideWholeMesh(DirectionalSlideBase):
    bl_idname = "maplus.directionalslidewholemesh"
    bl_label = "Directional Slide Mesh"
    bl_description = "Translates a target mesh (moves mesh in a direction)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickDirectionalSlideMeshSelected(DirectionalSlideBase):
    bl_idname = "maplus.quickdirectionalslidemeshselected"
    bl_label = "Directional Slide Mesh"
    bl_description = "Translates a target mesh (moves mesh in a direction)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickDirectionalSlideWholeMesh(DirectionalSlideBase):
    bl_idname = "maplus.quickdirectionalslidewholemesh"
    bl_label = "Directional Slide Mesh"
    bl_description = "Translates a target mesh (moves mesh in a direction)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


def scale_mat_from_vec(vec):
    return (
        mathutils.Matrix.Scale(
            vec[0],
            4,
            mathutils.Vector((1, 0.0, 0.0))
        ) *
        mathutils.Matrix.Scale(
            vec[1],
            4,
            mathutils.Vector((0.0, 1, 0.0))
        ) *
        mathutils.Matrix.Scale(
            vec[2],
            4,
            mathutils.Vector((0.0, 0.0, 1))
        )
    )


class AxisRotateBase(bpy.types.Operator):
    bl_idname = "maplus.axisrotatebase"
    bl_label = "Axis Rotate Base"
    bl_description = "Axis rotate base class"
    bl_options = {'REGISTER', 'UNDO'}
    target = None

    def execute(self, context):
        if not (bpy.context.active_object and bpy.context.active_object.select):
            self.report(
                {'ERROR'},
                'Cannot complete: need at least one active (and selected) object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = bpy.context.active_object.mode
        if not hasattr(self, "quick_op_target"):
            active_item = prims[addon_data.active_list_item]
        else:
            active_item = addon_data.quick_axis_rotate_transf

        if (bpy.context.active_object and
                type(bpy.context.active_object.data) == bpy.types.Mesh):

            if not hasattr(self, "quick_op_target"):
                if prims[active_item.axr_axis].kind != 'LINE':
                    self.report(
                        {'ERROR'},
                        ('Wrong operands: "Axis Rotate" can only operate on '
                         'a line')
                    )
                    return {'CANCELLED'}

            # a bmesh can only be initialized in edit mode...
            if previous_mode != 'EDIT':
                bpy.ops.object.editmode_toggle()
            else:
                # else we could already be in edit mode with some stale
                # updates, exiting and reentering forces an update
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()

            # Get global coordinate data for each geometry item, with
            # modifiers applied. Grab either directly from the scene data
            # (for quick ops), or from the MAPlus primitives
            # CollectionProperty on the scene data (for advanced tools)
            if hasattr(self, 'quick_op_target'):
                if addon_data.quick_axis_rotate_auto_grab_src:
                    vert_attribs_to_set = ('line_start', 'line_end')
                    try:
                        vert_data = return_selected_verts(
                            bpy.context.active_object,
                            len(vert_attribs_to_set),
                            bpy.context.active_object.matrix_world
                        )
                    except InsufficientSelectionError:
                        self.report({'ERROR'}, 'Not enough vertices selected.')
                        return {'CANCELLED'}
                    except NonMeshGrabError:
                        self.report(
                            {'ERROR'},
                            'Cannot grab coords: non-mesh or no active object.'
                        )
                        return {'CANCELLED'}

                    set_item_coords(
                        addon_data.quick_axis_rotate_src,
                        vert_attribs_to_set,
                        vert_data
                    )

                src_global_data = get_modified_global_coords(
                    geometry=addon_data.quick_axis_rotate_src,
                    kind='LINE'
                )

            else:
                src_global_data = get_modified_global_coords(
                    geometry=prims[active_item.axr_axis],
                    kind='LINE'
                )

            # These global point coordinate vectors will be used to construct
            # geometry and transformations in both object (global) space
            # and mesh (local) space
            axis_start = src_global_data[0]
            axis_end = src_global_data[1]

            # Get rotation in proper units (radians)
            if (bpy.context.scene.unit_settings.system_rotation == 'RADIANS'):
                converted_rot_amount = active_item.axr_amount
            else:
                converted_rot_amount = math.radians(active_item.axr_amount)

            # create common vars needed for object and for mesh
            # level transforms
            active_obj_transf = bpy.context.active_object.matrix_world.copy()
            inverse_active = active_obj_transf.copy()
            inverse_active.invert()

            multi_edit_targets = [
                model for model in bpy.context.scene.objects if (
                    model.select and model.type == 'MESH'
                )
            ]
            if self.target == 'OBJECT':
                for item in multi_edit_targets:
                    # (Note that there are no transformation modifiers for this
                    # transformation type, so that section is omitted here)

                    # Get the object world matrix before we modify it here
                    item_matrix_unaltered = item.matrix_world.copy()
                    unaltered_inverse = item_matrix_unaltered.copy()
                    unaltered_inverse.invert()

                    # Construct the axis vector and corresponding matrix
                    axis = axis_end - axis_start
                    axis_rot = mathutils.Matrix.Rotation(
                        converted_rot_amount,
                        4,
                        axis
                    )

                    # Perform the rotation (axis will be realigned later)
                    item.rotation_euler.rotate(axis_rot)
                    bpy.context.scene.update()

                    # put the original line starting point (before the object
                    # was rotated) into the local object space
                    src_pivot_location_local = unaltered_inverse * axis_start

                    # Calculate the new pivot location (after the
                    # first rotation), so that the axis can be moved
                    # back into place
                    new_pivot_loc_global = (
                        item.matrix_world *
                        src_pivot_location_local
                    )
                    pivot_to_dest = axis_start - new_pivot_loc_global

                    item.location += pivot_to_dest

            else:
                for item in multi_edit_targets:
                    self.report(
                        {'WARNING'},
                        ('Warning/Experimental: mesh transforms'
                         ' on objects with non-uniform scaling'
                         ' are not currently supported.')
                    )
                    # (Note that there are no transformation modifiers for this
                    # transformation type, so that section is omitted here)

                    # Init source mesh
                    src_mesh = bmesh.new()
                    src_mesh.from_mesh(item.data)

                    # Get the object world matrix
                    item_matrix_unaltered_loc = item.matrix_world.copy()
                    unaltered_inverse_loc = item_matrix_unaltered_loc.copy()
                    unaltered_inverse_loc.invert()

                    # Stored geom data in local coords
                    axis_start_loc = unaltered_inverse_loc * axis_start
                    axis_end_loc = unaltered_inverse_loc * axis_end

                    # Get axis vector in local space
                    axis_loc = axis_end_loc - axis_start_loc

                    # Get translation, pivot to local origin
                    axis_start_inv = axis_start_loc.copy()
                    axis_start_inv.negate()
                    src_pivot_to_loc_origin = mathutils.Matrix.Translation(
                        axis_start_inv
                    )
                    src_pivot_to_loc_origin.resize_4x4()

                    # Get local axis rotation
                    axis_rot_at_loc_origin = mathutils.Matrix.Rotation(
                        converted_rot_amount,
                        4,
                        axis_loc
                    )

                    # Get translation, pivot to dest
                    pivot_to_dest = mathutils.Matrix.Translation(
                        axis_start_loc
                    )
                    pivot_to_dest.resize_4x4()

                    axis_rotate_loc = (
                        pivot_to_dest *
                        axis_rot_at_loc_origin *
                        src_pivot_to_loc_origin
                    )

                    if self.target == 'MESHSELECTED':
                        src_mesh.transform(
                            axis_rotate_loc,
                            filter={'SELECT'}
                        )
                        bpy.ops.object.mode_set(mode='OBJECT')
                        src_mesh.to_mesh(item.data)
                    elif self.target == 'WHOLEMESH':
                        src_mesh.transform(axis_rotate_loc)
                        bpy.ops.object.mode_set(mode='OBJECT')
                        src_mesh.to_mesh(item.data)

                    src_mesh.free()

            # Go back to whatever mode we were in before doing this
            bpy.ops.object.mode_set(mode=previous_mode)

        else:
            self.report(
                {'ERROR'},
                'Cannot transform: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class AxisRotateObject(AxisRotateBase):
    bl_idname = "maplus.axisrotateobject"
    bl_label = "Axis Rotate"
    bl_description = "Rotates around an axis"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class QuickAxisRotateObject(AxisRotateBase):
    bl_idname = "maplus.quickaxisrotateobject"
    bl_label = "Axis Rotate"
    bl_description = "Rotates around an axis"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class AxisRotateMeshSelected(AxisRotateBase):
    bl_idname = "maplus.axisrotatemeshselected"
    bl_label = "Axis Rotate"
    bl_description = "Rotates around an axis"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class AxisRotateWholeMesh(AxisRotateBase):
    bl_idname = "maplus.axisrotatewholemesh"
    bl_label = "Axis Rotate"
    bl_description = "Rotates around an axis"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAxisRotateMeshSelected(AxisRotateBase):
    bl_idname = "maplus.quickaxisrotatemeshselected"
    bl_label = "Axis Rotate"
    bl_description = "Rotates around an axis"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAxisRotateWholeMesh(AxisRotateBase):
    bl_idname = "maplus.quickaxisrotatewholemesh"
    bl_label = "Axis Rotate"
    bl_description = "Rotates around an axis"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class AlignLinesBase(bpy.types.Operator):
    bl_idname = "maplus.alignlinesbase"
    bl_label = "Align Lines Base"
    bl_description = "Align lines base class"
    bl_options = {'REGISTER', 'UNDO'}
    target = None

    def execute(self, context):
        if not (bpy.context.active_object and bpy.context.active_object.select):
            self.report(
                {'ERROR'},
                'Cannot complete: need at least one active (and selected) object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = bpy.context.active_object.mode
        if hasattr(self, "quick_op_target"):
            active_item = addon_data.quick_align_lines_transf
        else:
            active_item = prims[addon_data.active_list_item]

        if (bpy.context.active_object and
                type(bpy.context.active_object.data) == bpy.types.Mesh):

            if not hasattr(self, "quick_op_target"):
                if (prims[active_item.aln_src_line].kind != 'LINE' or
                        prims[active_item.aln_dest_line].kind != 'LINE'):
                    self.report(
                        {'ERROR'},
                        ('Wrong operands: "Align Lines" can only operate on '
                         'two lines')
                    )
                    return {'CANCELLED'}

            # a bmesh can only be initialized in edit mode...
            if previous_mode != 'EDIT':
                bpy.ops.object.editmode_toggle()
            else:
                # else we could already be in edit mode with some stale
                # updates, exiting and reentering forces an update
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()

            # Get global coordinate data for each geometry item, with
            # modifiers applied. Grab either directly from the scene data
            # (for quick ops), or from the MAPlus primitives
            # CollectionProperty on the scene data (for advanced tools)
            if hasattr(self, 'quick_op_target'):
                if addon_data.quick_align_lines_auto_grab_src:
                    vert_attribs_to_set = ('line_start', 'line_end')
                    try:
                        vert_data = return_selected_verts(
                            bpy.context.active_object,
                            len(vert_attribs_to_set),
                            bpy.context.active_object.matrix_world
                        )
                    except InsufficientSelectionError:
                        self.report({'ERROR'}, 'Not enough vertices selected.')
                        return {'CANCELLED'}
                    except NonMeshGrabError:
                        self.report(
                            {'ERROR'},
                            'Cannot grab coords: non-mesh or no active object.'
                        )
                        return {'CANCELLED'}

                    set_item_coords(
                        addon_data.quick_align_lines_src,
                        vert_attribs_to_set,
                        vert_data
                    )

                src_global_data = get_modified_global_coords(
                    geometry=addon_data.quick_align_lines_src,
                    kind='LINE'
                )
                dest_global_data = get_modified_global_coords(
                    geometry=addon_data.quick_align_lines_dest,
                    kind='LINE'
                )

            else:
                src_global_data = get_modified_global_coords(
                    geometry=prims[active_item.aln_src_line],
                    kind='LINE'
                )
                dest_global_data = get_modified_global_coords(
                    geometry=prims[active_item.aln_dest_line],
                    kind='LINE'
                )

            # These global point coordinate vectors will be used to construct
            # geometry and transformations in both object (global) space
            # and mesh (local) space
            src_start = src_global_data[0]
            src_end = src_global_data[1]

            dest_start = dest_global_data[0]
            dest_end = dest_global_data[1]

            # create common vars needed for object and for mesh
            # level transforms
            active_obj_transf = bpy.context.active_object.matrix_world.copy()
            inverse_active = active_obj_transf.copy()
            inverse_active.invert()

            multi_edit_targets = [
                model for model in bpy.context.scene.objects if (
                    model.select and model.type == 'MESH'
                )
            ]
            if self.target == 'OBJECT':
                for item in multi_edit_targets:
                    # Get the object world matrix before we modify it here
                    item_matrix_unaltered = item.matrix_world.copy()
                    unaltered_inverse = item_matrix_unaltered.copy()
                    unaltered_inverse.invert()

                    # construct lines from the stored geometry
                    src_line = src_end - src_start
                    dest_line = dest_end - dest_start

                    # Take modifiers on the transformation item into account,
                    # in global (object) space
                    if active_item.aln_flip_direction:
                        src_line.negate()

                    # find rotational difference between source and dest lines
                    rotational_diff = src_line.rotation_difference(dest_line)
                    parallelize_lines = rotational_diff.to_matrix()
                    parallelize_lines.resize_4x4()

                    # rotate active object so line one is parallel linear,
                    # position will be corrected after this
                    item.rotation_euler.rotate(
                        rotational_diff
                    )
                    bpy.context.scene.update()

                    # put the original line starting point (before the object
                    # was rotated) into the local object space
                    src_pivot_location_local = unaltered_inverse * src_start

                    # get final global position of pivot (source line
                    # start coords) after object rotation
                    new_global_src_pivot_coords = (
                        item.matrix_world *
                        src_pivot_location_local
                    )
                    # get translation, pivot to dest
                    pivot_to_dest = (
                        dest_start - new_global_src_pivot_coords
                    )

                    item.location = (
                        item.location + pivot_to_dest
                    )
                    bpy.context.scene.update()

            else:
                for item in multi_edit_targets:
                    self.report(
                        {'WARNING'},
                        ('Warning/Experimental: mesh transforms'
                         ' on objects with non-uniform scaling'
                         ' are not currently supported.')
                    )
                    # Init source mesh
                    src_mesh = bmesh.new()
                    src_mesh.from_mesh(item.data)

                    # Get the object world matrix
                    item_matrix_unaltered_loc = item.matrix_world.copy()
                    unaltered_inverse_loc = item_matrix_unaltered_loc.copy()
                    unaltered_inverse_loc.invert()

                    # Stored geom data in local coords
                    src_start_loc = unaltered_inverse_loc * src_start
                    src_end_loc = unaltered_inverse_loc * src_end

                    dest_start_loc = unaltered_inverse_loc * dest_start
                    dest_end_loc = unaltered_inverse_loc * dest_end

                    # Construct vectors for each line in local space
                    loc_src_line = src_end_loc - src_start_loc
                    loc_dest_line = dest_end_loc - dest_start_loc

                    # Take modifiers on the transformation item into account,
                    # in local (mesh) space
                    if active_item.aln_flip_direction:
                        loc_src_line.negate()

                    # Get translation, move source pivot to local origin
                    src_start_inv = src_start_loc.copy()
                    src_start_inv.negate()
                    src_pivot_to_loc_origin = mathutils.Matrix.Translation(
                        src_start_inv
                    )

                    # Get edge alignment rotation (align src to dest)
                    loc_rdiff = loc_src_line.rotation_difference(
                        loc_dest_line
                    )
                    parallelize_lines_loc = loc_rdiff.to_matrix()
                    parallelize_lines_loc.resize_4x4()

                    # Get translation, move pivot to destination
                    pivot_to_dest_loc = mathutils.Matrix.Translation(
                        dest_start_loc
                    )

                    loc_make_collinear = (
                        pivot_to_dest_loc *
                        parallelize_lines_loc *
                        src_pivot_to_loc_origin
                    )

                    if self.target == 'MESHSELECTED':
                        src_mesh.transform(
                            loc_make_collinear,
                            filter={'SELECT'}
                        )
                    elif self.target == 'WHOLEMESH':
                        src_mesh.transform(loc_make_collinear)

                    bpy.ops.object.mode_set(mode='OBJECT')
                    src_mesh.to_mesh(item.data)
                    src_mesh.free()

            # Go back to whatever mode we were in before doing this
            bpy.ops.object.mode_set(mode=previous_mode)

        else:
            self.report(
                {'ERROR'},
                'Cannot transform: non-mesh or no active object.'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class AlignLinesObject(AlignLinesBase):
    bl_idname = "maplus.alignlinesobject"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class QuickAlignLinesObject(AlignLinesBase):
    bl_idname = "maplus.quickalignlinesobject"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class AlignLinesMeshSelected(AlignLinesBase):
    bl_idname = "maplus.alignlinesmeshselected"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class AlignLinesWholeMesh(AlignLinesBase):
    bl_idname = "maplus.alignlineswholemesh"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAlignLinesMeshSelected(AlignLinesBase):
    bl_idname = "maplus.quickalignlinesmeshselected"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAlignLinesWholeMesh(AlignLinesBase):
    bl_idname = "maplus.quickalignlineswholemesh"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class AlignPlanesBase(bpy.types.Operator):
    bl_idname = "maplus.alignplanesbase"
    bl_label = "Align Planes base"
    bl_description = "Align Planes base class"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not (bpy.context.active_object and bpy.context.active_object.select):
            self.report(
                {'ERROR'},
                'Cannot complete: need at least one active (and selected) object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = bpy.context.active_object.mode
        if not hasattr(self, "quick_op_target"):
            active_item = prims[addon_data.active_list_item]
        else:
            active_item = addon_data.quick_align_planes_transf

        if (bpy.context.active_object and
                type(bpy.context.active_object.data) == bpy.types.Mesh):

            if not hasattr(self, "quick_op_target"):
                if (prims[active_item.apl_src_plane].kind != 'PLANE' or
                        prims[active_item.apl_dest_plane].kind != 'PLANE'):
                    self.report(
                        {'ERROR'},
                        ('Wrong operands: "Align Planes" can only operate on '
                         'two planes')
                    )
                    return {'CANCELLED'}

            # a bmesh can only be initialized in edit mode...
            if previous_mode != 'EDIT':
                bpy.ops.object.editmode_toggle()
            else:
                # else we could already be in edit mode with some stale
                # updates, exiting and reentering forces an update
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()

            # Get global coordinate data for each geometry item, with
            # modifiers applied. Grab either directly from the scene data
            # (for quick ops), or from the MAPlus primitives
            # CollectionProperty on the scene data (for advanced tools)
            if hasattr(self, "quick_op_target"):
                if addon_data.quick_align_planes_auto_grab_src:
                    vert_attribs_to_set = (
                        'plane_pt_a',
                        'plane_pt_b',
                        'plane_pt_c'
                    )
                    try:
                        vert_data = return_selected_verts(
                            bpy.context.active_object,
                            len(vert_attribs_to_set),
                            bpy.context.active_object.matrix_world
                        )
                    except InsufficientSelectionError:
                        self.report({'ERROR'}, 'Not enough vertices selected.')
                        return {'CANCELLED'}
                    except NonMeshGrabError:
                        self.report(
                            {'ERROR'},
                            'Cannot grab coords: non-mesh or no active object.'
                        )
                        return {'CANCELLED'}

                    set_item_coords(
                        addon_data.quick_align_planes_src,
                        vert_attribs_to_set,
                        vert_data
                    )

                src_global_data = get_modified_global_coords(
                    geometry=addon_data.quick_align_planes_src,
                    kind='PLANE'
                )
                dest_global_data = get_modified_global_coords(
                    geometry=addon_data.quick_align_planes_dest,
                    kind='PLANE'
                )

            else:
                src_global_data = get_modified_global_coords(
                    geometry=prims[active_item.apl_src_plane],
                    kind='PLANE'
                )
                dest_global_data = get_modified_global_coords(
                    geometry=prims[active_item.apl_dest_plane],
                    kind='PLANE'
                )

            # These global point coordinate vectors will be used to construct
            # geometry and transformations in both object (global) space
            # and mesh (local) space
            src_pt_a = src_global_data[0]
            src_pt_b = src_global_data[1]
            src_pt_c = src_global_data[2]

            dest_pt_a = dest_global_data[0]
            dest_pt_b = dest_global_data[1]
            dest_pt_c = dest_global_data[2]

            # create common vars needed for object and for mesh level transfs
            active_obj_transf = bpy.context.active_object.matrix_world.copy()
            inverse_active = active_obj_transf.copy()
            inverse_active.invert()

            # We need global data for the object operation and for creation
            # of a custom transform orientation if the user enables it.
            # construct normal vector for first (source) plane
            src_pln_ln_BA = src_pt_a - src_pt_b
            src_pln_ln_BC = src_pt_c - src_pt_b
            src_normal = src_pln_ln_BA.cross(src_pln_ln_BC)

            # Take modifiers on the transformation item into account,
            # in global (object) space
            if active_item.apl_flip_normal:
                src_normal.negate()

            # construct normal vector for second (destination) plane
            dest_pln_ln_BA = dest_pt_a - dest_pt_b
            dest_pln_ln_BC = dest_pt_c - dest_pt_b
            dest_normal = dest_pln_ln_BA.cross(dest_pln_ln_BC)

            # find rotational difference between source and dest planes
            rotational_diff = src_normal.rotation_difference(dest_normal)

            # Set up edge alignment (BA plane1 to BA plane2)
            new_lead_edge_orientation = src_pln_ln_BA.copy()
            new_lead_edge_orientation.rotate(rotational_diff)
            parallelize_edges = new_lead_edge_orientation.rotation_difference(
                dest_pln_ln_BA
            )

            # Create custom transform orientation, for sliding the user's
            # target along the destination face after it has been aligned.
            # We do this by making a basis matrix out of the dest plane
            # leading edge vector, the dest normal vector, and the cross
            # of those two (each vector is normalized first)
            vdest = dest_pln_ln_BA.copy()
            vdest.normalize()
            vnorm = dest_normal.copy()
            vnorm.normalize()
            # vnorm.negate()
            vcross = vdest.cross(vnorm)
            vcross.normalize()
            vcross.negate()
            custom_orientation = mathutils.Matrix(
                [
                    [vcross[0], vnorm[0], vdest[0]],
                    [vcross[1], vnorm[1], vdest[1]],
                    [vcross[2], vnorm[2], vdest[2]]
                ]
            )
            bpy.ops.transform.create_orientation(
                name='MAPlus',
                use=active_item.apl_use_custom_orientation,
                overwrite=True
            )
            bpy.context.scene.orientations['MAPlus'].matrix = (
                custom_orientation
            )

            multi_edit_targets = [
                model for model in bpy.context.scene.objects if (
                    model.select and model.type == 'MESH'
                )
            ]
            if self.target == 'OBJECT':
                for item in multi_edit_targets:
                    # Get the object world matrix before we modify it here
                    item_matrix_unaltered = item.matrix_world.copy()
                    unaltered_inverse = item_matrix_unaltered.copy()
                    unaltered_inverse.invert()

                    # Try to rotate the object by the rotational_diff
                    item.rotation_euler.rotate(
                        rotational_diff
                    )
                    bpy.context.scene.update()

                    # Parallelize the leading edges
                    item.rotation_euler.rotate(
                        parallelize_edges
                    )
                    bpy.context.scene.update()

                    # get local coords using active object as basis, in
                    # other words, determine coords of the source pivot
                    # relative to the active object's origin by reversing
                    # the active object's transf from the pivot's coords
                    local_src_pivot_coords = (
                        unaltered_inverse * src_pt_b
                    )

                    # find the new global location of the pivot (we access
                    # the item's matrix_world directly here since we
                    # changed/updated it earlier)
                    new_global_src_pivot_coords = (
                        item.matrix_world * local_src_pivot_coords
                    )
                    # figure out how to translate the object (the translation
                    # vector) so that the source pivot sits on the destination
                    # pivot's location
                    # first vector is the global/absolute distance
                    # between the two pivots
                    pivot_to_dest = (
                        dest_pt_b -
                        new_global_src_pivot_coords
                    )
                    item.location = (
                        item.location +
                        pivot_to_dest
                    )
                    bpy.context.scene.update()

            else:
                for item in multi_edit_targets:
                    self.report(
                        {'WARNING'},
                        ('Warning/Experimental: mesh transforms'
                         ' on objects with non-uniform scaling'
                         ' are not currently supported.')
                    )
                    src_mesh = bmesh.new()
                    src_mesh.from_mesh(item.data)

                    item_matrix_unaltered_loc = item.matrix_world.copy()
                    unaltered_inverse_loc = item_matrix_unaltered_loc.copy()
                    unaltered_inverse_loc.invert()

                    # Stored geom data in local coords
                    src_a_loc = unaltered_inverse_loc * src_pt_a
                    src_b_loc = unaltered_inverse_loc * src_pt_b
                    src_c_loc = unaltered_inverse_loc * src_pt_c

                    dest_a_loc = unaltered_inverse_loc * dest_pt_a
                    dest_b_loc = unaltered_inverse_loc * dest_pt_b
                    dest_c_loc = unaltered_inverse_loc * dest_pt_c

                    src_ba_loc = src_a_loc - src_b_loc
                    src_bc_loc = src_c_loc - src_b_loc
                    src_normal_loc = src_ba_loc.cross(src_bc_loc)

                    # Take modifiers on the transformation item into account,
                    # in local (mesh) space
                    if active_item.apl_flip_normal:
                        src_normal_loc.negate()

                    dest_ba_loc = dest_a_loc - dest_b_loc
                    dest_bc_loc = dest_c_loc - dest_b_loc
                    dest_normal_loc = dest_ba_loc.cross(dest_bc_loc)

                    # Get translation, move source pivot to local origin
                    src_b_inv = src_b_loc.copy()
                    src_b_inv.negate()
                    src_pivot_to_loc_origin = mathutils.Matrix.Translation(
                        src_b_inv
                    )

                    # Get rotational diff between planes
                    loc_rot_diff = src_normal_loc.rotation_difference(
                        dest_normal_loc
                    )
                    parallelize_planes_loc = loc_rot_diff.to_matrix()
                    parallelize_planes_loc.resize_4x4()

                    # Get edge alignment rotation (align leading plane edges)
                    new_lead_edge_ornt_loc = (
                        parallelize_planes_loc * src_ba_loc
                    )
                    edge_align_loc = (
                        new_lead_edge_ornt_loc.rotation_difference(
                            dest_ba_loc
                        )
                    )
                    parallelize_edges_loc = edge_align_loc.to_matrix()
                    parallelize_edges_loc.resize_4x4()

                    # Get translation, move pivot to destination
                    pivot_to_dest_loc = mathutils.Matrix.Translation(
                        dest_b_loc
                    )

                    mesh_coplanar = (
                        pivot_to_dest_loc *
                        parallelize_edges_loc *
                        parallelize_planes_loc *
                        src_pivot_to_loc_origin
                    )

                    if self.target == 'MESHSELECTED':
                        src_mesh.transform(
                            mesh_coplanar,
                            filter={'SELECT'}
                        )
                    elif self.target == 'WHOLEMESH':
                        src_mesh.transform(mesh_coplanar)

                    bpy.ops.object.mode_set(mode='OBJECT')
                    src_mesh.to_mesh(item.data)

            # Go back to whatever mode we were in before doing this
            bpy.ops.object.mode_set(mode=previous_mode)

        else:
            self.report(
                {'ERROR'},
                "\nCannot transform: non-mesh or no active object."
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class AlignPlanesObject(AlignPlanesBase):
    bl_idname = "maplus.alignplanesobject"
    bl_label = "Align Planes"
    bl_description = "Makes planes coplanar (flat against each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class QuickAlignPlanesObject(AlignPlanesBase):
    bl_idname = "maplus.quickalignplanesobject"
    bl_label = "Align Planes"
    bl_description = "Makes planes coplanar (flat against each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class AlignPlanesMeshSelected(AlignPlanesBase):
    bl_idname = "maplus.alignplanesmeshselected"
    bl_label = "Align Planes"
    bl_description = "Makes planes coplanar (flat against each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class AlignPlanesWholeMesh(AlignPlanesBase):
    bl_idname = "maplus.alignplaneswholemesh"
    bl_label = "Align Planes"
    bl_description = "Makes planes coplanar (flat against each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAlignPlanesMeshSelected(AlignPlanesBase):
    bl_idname = "maplus.quickalignplanesmeshselected"
    bl_label = "Align Planes"
    bl_description = "Makes planes coplanar (flat against each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESHSELECTED'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAlignPlanesWholeMesh(AlignPlanesBase):
    bl_idname = "maplus.quickalignplaneswholemesh"
    bl_label = "Align Planes"
    bl_description = "Makes planes coplanar (flat against each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLEMESH'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class QuickAlignObjects(bpy.types.Operator):
    bl_idname = "maplus.quickalignobjects"
    bl_label = "Align Objects"
    bl_description = "Align Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.context.active_object:
            self.report(
                {'ERROR'},
                'Cannot complete: no active object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = bpy.context.active_object.mode

        # Get active (target) transformation matrix components
        active_mat = bpy.context.active_object.matrix_world
        active_trs = [
            mathutils.Matrix.Translation(active_mat.decompose()[0]),
            active_mat.decompose()[1].to_matrix(),
            mathutils.Matrix.Scale(active_mat.decompose()[2][0], 4),
        ]
        active_trs[1].resize_4x4()

        # Copy the transform components from the target to the current object
        selected = [item for item in bpy.context.scene.objects if item.select]
        for item in selected:
            current_mat = item.matrix_world
            current_trs = [
                mathutils.Matrix.Translation(current_mat.decompose()[0]),
                current_mat.decompose()[1].to_matrix(),
                mathutils.Matrix.Scale(current_mat.decompose()[2][0], 4),
            ]
            current_trs[1].resize_4x4()
            item.matrix_world = (
                active_trs[0] *
                active_trs[1] *
                current_trs[2]
            )

        return {'FINISHED'}


class CalcLineLengthBase(bpy.types.Operator):
    bl_idname = "maplus.calclinelengthbase"
    bl_label = "Calculate Line Length"
    bl_description = "Calculates the length of the targeted line item"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_attrib = 'quick_calc_result_numeric'
            calc_target_item = addon_data.internal_storage_slot_1
        else:
            active_calculation = prims[addon_data.active_list_item]
            result_attrib = 'single_calc_result'
            calc_target_item = prims[active_calculation.single_calc_target]

        if (not hasattr(self, 'quick_calc_target')) and calc_target_item.kind != 'LINE':
            self.report(
                {'ERROR'},
                ('Wrong operand: "Calculate Line Length" can only operate on'
                 ' a line')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_item.kind != 'LINE':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 (the target) is not'
                     ' explicitly using the correct type for this'
                     ' calculation (type should be set to "Line").')
                )

        src_global_data = get_modified_global_coords(
            geometry=calc_target_item,
            kind='LINE'
        )
        src_line = src_global_data[1] - src_global_data[0]
        result = src_line.length
        setattr(active_calculation, result_attrib, result)
        if addon_data.calc_result_to_clipboard:
            bpy.context.window_manager.clipboard = str(result)

        return {'FINISHED'}


class CalcLineLength(CalcLineLengthBase):
    bl_idname = "maplus.calclinelength"
    bl_label = "Calculate Line Length"
    bl_description = "Calculates the length of the targeted line item"
    bl_options = {'REGISTER', 'UNDO'}


class QuickCalcLineLength(CalcLineLengthBase):
    bl_idname = "maplus.quickcalclinelength"
    bl_label = "Calculate Line Length"
    bl_description = (
        "Calculates the length of the line item in Slot 1"
    )
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                addon_data.internal_storage_slot_1.kind != 'LINE'):
            return False
        return True


class CalcRotationalDiffBase(bpy.types.Operator):
    bl_idname = "maplus.calcrotationaldiffbase"
    bl_label = "Angle of Lines"
    bl_description = (
        "Calculates the rotational difference between line items"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_attrib = 'quick_calc_result_numeric'
            calc_target_one = addon_data.internal_storage_slot_1
            calc_target_two = addon_data.internal_storage_slot_2
        else:
            active_calculation = prims[addon_data.active_list_item]
            result_attrib = 'multi_calc_result'
            calc_target_one = prims[active_calculation.multi_calc_target_one]
            calc_target_two = prims[active_calculation.multi_calc_target_two]

        if (not hasattr(self, 'quick_calc_target')) and not (calc_target_one.kind == 'LINE' and
                calc_target_two.kind == 'LINE'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Calculate Rotational Difference" can'
                 ' only operate on two lines')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_one.kind != 'LINE' or calc_target_two.kind != 'LINE':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Line").')
                )


        src_global_data = get_modified_global_coords(
            geometry=calc_target_one,
            kind='LINE'
        )
        dest_global_data = get_modified_global_coords(
            geometry=calc_target_two,
            kind='LINE'
        )
        src_line = src_global_data[1] - src_global_data[0]
        dest_line = dest_global_data[1] - dest_global_data[0]

        axis, angle = (
            src_line.rotation_difference(dest_line).to_axis_angle()
        )
        # Get rotation in proper units (radians)
        if (bpy.context.scene.unit_settings.system_rotation == 'RADIANS'):
            result = angle
        else:
            result = math.degrees(angle)

        setattr(active_calculation, result_attrib, result)
        if addon_data.calc_result_to_clipboard:
            bpy.context.window_manager.clipboard = str(result)

        return {'FINISHED'}


class CalcRotationalDiff(CalcRotationalDiffBase):
    bl_idname = "maplus.calcrotationaldiff"
    bl_label = "Angle of Lines"
    bl_description = (
        "Calculates the rotational difference between line items"
    )
    bl_options = {'REGISTER', 'UNDO'}


class QuickCalcRotationalDiff(CalcRotationalDiffBase):
    bl_idname = "maplus.quickcalcrotationaldiff"
    bl_label = "Angle of Lines"
    bl_description = (
        "Calculates the rotational difference between line items"
    )
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                (addon_data.internal_storage_slot_1.kind != 'LINE' or
                 addon_data.internal_storage_slot_2.kind != 'LINE')):
            return False
        return True


class ComposeNewLineFromOriginBase(bpy.types.Operator):
    bl_idname = "maplus.composenewlinefromoriginbase"
    bl_label = "New Line from Origin"
    bl_description = "Composes a new line item starting at the world origin"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_item = active_calculation.quick_calc_result_item
            calc_target_item = addon_data.internal_storage_slot_1
        else:
            active_calculation = prims[addon_data.active_list_item]
            bpy.ops.maplus.addnewline()
            result_item = prims[-1]
            calc_target_item = prims[active_calculation.single_calc_target]

        if (not hasattr(self, 'quick_calc_target')) and calc_target_item.kind != 'LINE':
            self.report(
                {'ERROR'},
                ('Wrong operand: "Compose New Line from Origin" can'
                 ' only operate on a line')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_item.kind != 'LINE':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 (the target) is not'
                     ' explicitly using the correct type for this'
                     ' calculation (type should be set to "Line").')
                )

        start_loc = mathutils.Vector((0, 0, 0))
        src_global_data = get_modified_global_coords(
            geometry=calc_target_item,
            kind='LINE'
        )
        src_line = src_global_data[1] - src_global_data[0]

        result_item.kind = 'LINE'
        result_item.line_start = start_loc
        result_item.line_end = (
            start_loc + src_line
        )
        if addon_data.calc_result_to_clipboard:
            addon_data.internal_storage_clipboard.kind = 'LINE'
            copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class ComposeNewLineFromOrigin(ComposeNewLineFromOriginBase):
    bl_idname = "maplus.composenewlinefromorigin"
    bl_label = "New Line from Origin"
    bl_description = "Composes a new line item starting at the world origin"
    bl_options = {'REGISTER', 'UNDO'}


class QuickComposeNewLineFromOrigin(ComposeNewLineFromOriginBase):
    bl_idname = "maplus.quickcomposenewlinefromorigin"
    bl_label = "New Line from Origin"
    bl_description = "Composes a new line item starting at the world origin"
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                addon_data.internal_storage_slot_1.kind != 'LINE'):
            return False
        return True


class ComposeNormalFromPlaneBase(bpy.types.Operator):
    bl_idname = "maplus.composenormalfromplanebase"
    bl_label = "Get Plane Normal"
    bl_description = "Get the plane's normal as a new line item"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_item = active_calculation.quick_calc_result_item
            calc_target_item = addon_data.internal_storage_slot_1
        else:
            active_calculation = prims[addon_data.active_list_item]
            bpy.ops.maplus.addnewline()
            result_item = prims[-1]
            calc_target_item = prims[active_calculation.single_calc_target]

        if (not hasattr(self, 'quick_calc_target')) and not calc_target_item.kind == 'PLANE':
            self.report(
                {'ERROR'},
                ('Wrong operand: "Get Plane Normal" can only operate on'
                 ' a plane')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_item.kind != 'PLANE':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 (the target) is not'
                     ' explicitly using the correct type for this'
                     ' calculation (type should be set to "Plane").')
                )

        src_global_data = get_modified_global_coords(
            geometry=calc_target_item,
            kind='PLANE'
        )
        line_BA = (
            src_global_data[0] -
            src_global_data[1]
        )
        line_BC = (
            src_global_data[2] -
            src_global_data[1]
        )
        normal = line_BA.cross(line_BC)
        normal.normalize()
        start_loc = mathutils.Vector(
            calc_target_item.plane_pt_b[0:3]
        )

        result_item.kind = 'LINE'
        result_item.line_start = start_loc
        result_item.line_end = start_loc + normal
        if addon_data.calc_result_to_clipboard:
            addon_data.internal_storage_clipboard.kind = 'LINE'
            copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class ComposeNormalFromPlane(ComposeNormalFromPlaneBase):
    bl_idname = "maplus.composenormalfromplane"
    bl_label = "Get Plane Normal"
    bl_description = "Get the plane's normal as a new line item"
    bl_options = {'REGISTER', 'UNDO'}


class QuickComposeNormalFromPlane(ComposeNormalFromPlaneBase):
    bl_idname = "maplus.quickcomposenormalfromplane"
    bl_label = "Get Plane Normal"
    bl_description = "Get the plane's normal as a new line item"
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                addon_data.internal_storage_slot_1.kind != 'PLANE'):
            return False
        return True


class ComposeNewLineFromPointBase(bpy.types.Operator):
    bl_idname = "maplus.composenewlinefrompointbase"
    bl_label = "New Line from Point"
    bl_description = (
        "Composes a new line item from the supplied point,"
        " starting at the world origin"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_item = active_calculation.quick_calc_result_item
            calc_target_item = addon_data.internal_storage_slot_1
        else:
            active_calculation = prims[addon_data.active_list_item]
            bpy.ops.maplus.addnewline()
            result_item = prims[-1]
            calc_target_item = prims[active_calculation.single_calc_target]

        if (not hasattr(self, 'quick_calc_target')) and calc_target_item.kind != 'POINT':
            self.report(
                {'ERROR'},
                ('Wrong operand: "Compose New Line from Point" can'
                 ' only operate on a point')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_item.kind != 'POINT':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 (the target) is not'
                     ' explicitly using the correct type for this'
                     ' calculation (type should be set to "Point").')
                )

        start_loc = mathutils.Vector((0, 0, 0))

        src_global_data = get_modified_global_coords(
            geometry=calc_target_item,
            kind='POINT'
        )

        result_item.kind = 'LINE'
        result_item.line_start = start_loc
        result_item.line_end = src_global_data[0]
        if addon_data.calc_result_to_clipboard:
            addon_data.internal_storage_clipboard.kind = 'LINE'
            copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class ComposeNewLineFromPoint(bpy.types.Operator):
    bl_idname = "maplus.composenewlinefrompoint"
    bl_label = "New Line from Point"
    bl_description = (
        "Composes a new line item from the supplied point,"
        " starting at the world origin"
    )
    bl_options = {'REGISTER', 'UNDO'}


class QuickComposeNewLineFromPoint(bpy.types.Operator):
    bl_idname = "maplus.quickcomposenewlinefrompoint"
    bl_label = "New Line from Point"
    bl_description = (
        "Composes a new line item from the supplied point,"
        " starting at the world origin"
    )
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                addon_data.internal_storage_slot_1.kind != 'POINT'):
            return False
        return True


class ComposeNewLineAtPointLocationBase(bpy.types.Operator):
    bl_idname = "maplus.composenewlineatpointlocationbase"
    bl_label = "New Line at Point Location"
    bl_description = "Composes a new line item starting at the point location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_item = active_calculation.quick_calc_result_item
            calc_target_one = addon_data.internal_storage_slot_1
            calc_target_two = addon_data.internal_storage_slot_2
        else:
            active_calculation = prims[addon_data.active_list_item]
            bpy.ops.maplus.addnewline()
            result_item = prims[-1]
            calc_target_one = prims[active_calculation.multi_calc_target_one]
            calc_target_two = prims[active_calculation.multi_calc_target_two]
        targets_by_kind = {
            item.kind: item for item in [calc_target_one, calc_target_two]
        }

        if not ('POINT' in targets_by_kind and 'LINE' in targets_by_kind):
            self.report(
                {'ERROR'},
                ('Wrong operand(s): "Compose New Line at Point" can'
                 ' only operate with both a line and a point')
            )
            return {'CANCELLED'}

        pt_global_data = get_modified_global_coords(
            geometry=targets_by_kind['POINT'],
            kind='POINT'
        )
        line_global_data = get_modified_global_coords(
            geometry=targets_by_kind['LINE'],
            kind='LINE'
        )
        start_loc = pt_global_data[0]
        src_line = line_global_data[1] - line_global_data[0]

        result_item.kind = 'LINE'
        result_item.line_start = start_loc
        result_item.line_end = start_loc + src_line
        if addon_data.calc_result_to_clipboard:
            addon_data.internal_storage_clipboard.kind = 'LINE'
            copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class ComposeNewLineAtPointLocation(ComposeNewLineAtPointLocationBase):
    bl_idname = "maplus.composenewlineatpointlocation"
    bl_label = "New Line at Point Location"
    bl_description = "Composes a new line item starting at the point location"
    bl_options = {'REGISTER', 'UNDO'}


class QuickComposeNewLineAtPointLocation(ComposeNewLineAtPointLocationBase):
    bl_idname = "maplus.quickcomposenewlineatpointlocation"
    bl_label = "New Line at Point Location"
    bl_description = "Composes a new line item starting at the point location"
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        slot_kinds = set(
            [item.kind for item in [
                    addon_data.internal_storage_slot_1,
                    addon_data.internal_storage_slot_2
                ]
            ]
        )
        if (addon_data.quick_calc_check_types and
                ('POINT' not in slot_kinds or 'LINE' not in slot_kinds)):
            return False
        return True


class CalcDistanceBetweenPointsBase(bpy.types.Operator):
    bl_idname = "maplus.calcdistancebetweenpointsbase"
    bl_label = "Distance Between Points"
    bl_description = "Calculate the distance between provided point items"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_attrib = 'quick_calc_result_numeric'
            calc_target_one = addon_data.internal_storage_slot_1
            calc_target_two = addon_data.internal_storage_slot_2
        else:
            active_calculation = prims[addon_data.active_list_item]
            result_attrib = 'multi_calc_result'
            calc_target_one = prims[active_calculation.multi_calc_target_one]
            calc_target_two = prims[active_calculation.multi_calc_target_two]

        if (not hasattr(self, 'quick_calc_target')) and not (calc_target_one.kind == 'POINT' and
                calc_target_two.kind == 'POINT'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Calculate Distance Between Points" can'
                 ' only operate on two points')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_one.kind != 'POINT' or calc_target_two.kind != 'POINT':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Point").')
                )

        src_global_data = get_modified_global_coords(
            geometry=calc_target_one,
            kind='POINT'
        )
        dest_global_data = get_modified_global_coords(
            geometry=calc_target_two,
            kind='POINT'
        )
        src_pt = src_global_data[0]
        dest_pt = dest_global_data[0]

        result = (dest_pt - src_pt).length
        setattr(active_calculation, result_attrib, result)
        if addon_data.calc_result_to_clipboard:
            bpy.context.window_manager.clipboard = str(result)

        return {'FINISHED'}


class CalcDistanceBetweenPoints(CalcDistanceBetweenPointsBase):
    bl_idname = "maplus.calcdistancebetweenpoints"
    bl_label = "Distance Between Points"
    bl_description = "Calculate the distance between provided point items"
    bl_options = {'REGISTER', 'UNDO'}


class QuickCalcDistanceBetweenPoints(CalcDistanceBetweenPointsBase):
    bl_idname = "maplus.quickcalcdistancebetweenpoints"
    bl_label = "Distance Between Points"
    bl_description = "Calculate the distance between provided point items"
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                (addon_data.internal_storage_slot_1.kind != 'POINT' or
                 addon_data.internal_storage_slot_2.kind != 'POINT')):
            return False
        return True


class ComposeNewLineFromPointsBase(bpy.types.Operator):
    bl_idname = "maplus.composenewlinefrompointsbase"
    bl_label = "New Line from Points"
    bl_description = "Composes a new line item from provided point items"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_item = active_calculation.quick_calc_result_item
            calc_target_one = addon_data.internal_storage_slot_1
            calc_target_two = addon_data.internal_storage_slot_2
        else:
            active_calculation = prims[addon_data.active_list_item]
            bpy.ops.maplus.addnewline()
            result_item = prims[-1]
            calc_target_one = prims[active_calculation.multi_calc_target_one]
            calc_target_two = prims[active_calculation.multi_calc_target_two]

        if (not hasattr(self, 'quick_calc_target')) and not (calc_target_one.kind == 'POINT' and
                calc_target_two.kind == 'POINT'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Compose New Line from Points" can'
                 ' only operate on two points')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_one.kind != 'POINT' or calc_target_two.kind != 'POINT':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Point").')
                )

        src_global_data = get_modified_global_coords(
            geometry=calc_target_one,
            kind='POINT'
        )
        dest_global_data = get_modified_global_coords(
            geometry=calc_target_two,
            kind='POINT'
        )
        src_pt = src_global_data[0]
        dest_pt = dest_global_data[0]

        result_item.kind = 'LINE'
        result_item.line_start = src_pt
        result_item.line_end = dest_pt
        if addon_data.calc_result_to_clipboard:
            addon_data.internal_storage_clipboard.kind = 'LINE'
            copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class ComposeNewLineFromPoints(ComposeNewLineFromPointsBase):
    bl_idname = "maplus.composenewlinefrompoints"
    bl_label = "New Line from Points"
    bl_description = "Composes a new line item from provided point items"
    bl_options = {'REGISTER', 'UNDO'}


class QuickComposeNewLineFromPoints(ComposeNewLineFromPointsBase):
    bl_idname = "maplus.quickcomposenewlinefrompoints"
    bl_label = "New Line from Points"
    bl_description = "Composes a new line item from provided point items"
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                (addon_data.internal_storage_slot_1.kind != 'POINT' or
                 addon_data.internal_storage_slot_2.kind != 'POINT')):
            return False
        return True


class ComposeNewLineVectorAdditionBase(bpy.types.Operator):
    bl_idname = "maplus.composenewlinevectoradditionbase"
    bl_label = "Add Lines"
    bl_description = "Composes a new line item by vector-adding provided lines"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_item = active_calculation.quick_calc_result_item
            calc_target_one = addon_data.internal_storage_slot_1
            calc_target_two = addon_data.internal_storage_slot_2
        else:
            active_calculation = prims[addon_data.active_list_item]
            bpy.ops.maplus.addnewline()
            result_item = prims[-1]
            calc_target_one = prims[active_calculation.multi_calc_target_one]
            calc_target_two = prims[active_calculation.multi_calc_target_two]

        if (not hasattr(self, 'quick_calc_target')) and not (calc_target_one.kind == 'LINE' and
                calc_target_two.kind == 'LINE'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Add Lines" can only operate on'
                 ' two lines')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_one.kind != 'LINE' or calc_target_two.kind != 'LINE':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Line").')
                )

        start_loc = mathutils.Vector((0, 0, 0))

        src_global_data = get_modified_global_coords(
            geometry=calc_target_one,
            kind='LINE'
        )
        dest_global_data = get_modified_global_coords(
            geometry=calc_target_two,
            kind='LINE'
        )
        src_line = src_global_data[1] - src_global_data[0]
        dest_line = dest_global_data[1] - dest_global_data[0]

        result_item.kind = 'LINE'
        result_item.line_start = start_loc
        result_item.line_end = src_line + dest_line
        if addon_data.calc_result_to_clipboard:
            addon_data.internal_storage_clipboard.kind = 'LINE'
            copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class ComposeNewLineVectorAddition(ComposeNewLineVectorAdditionBase):
    bl_idname = "maplus.composenewlinevectoraddition"
    bl_label = "Add Lines"
    bl_description = "Composes a new line item by vector-adding provided lines"
    bl_options = {'REGISTER', 'UNDO'}


class QuickComposeNewLineVectorAddition(ComposeNewLineVectorAdditionBase):
    bl_idname = "maplus.quickcomposenewlinevectoraddition"
    bl_label = "Add Lines"
    bl_description = "Composes a new line item by vector-adding provided lines"
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                (addon_data.internal_storage_slot_1.kind != 'LINE' or
                 addon_data.internal_storage_slot_2.kind != 'LINE')):
            return False
        return True


class ComposeNewLineVectorSubtractionBase(bpy.types.Operator):
    bl_idname = "maplus.composenewlinevectorsubtractionbase"
    bl_label = "Subtract Lines"
    bl_description = (
        "Composes a new line item by performing vector-subtraction"
        " (first line minus second line)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_item = active_calculation.quick_calc_result_item
            calc_target_one = addon_data.internal_storage_slot_1
            calc_target_two = addon_data.internal_storage_slot_2
        else:
            active_calculation = prims[addon_data.active_list_item]
            bpy.ops.maplus.addnewline()
            result_item = prims[-1]
            calc_target_one = prims[active_calculation.multi_calc_target_one]
            calc_target_two = prims[active_calculation.multi_calc_target_two]

        if (not hasattr(self, 'quick_calc_target')) and not (calc_target_one.kind == 'LINE' and
                calc_target_two.kind == 'LINE'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Add Lines" can only operate on'
                 ' two lines')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if calc_target_one.kind != 'LINE' or calc_target_two.kind != 'LINE':
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Line").')
                )

        start_loc = mathutils.Vector((0, 0, 0))

        src_global_data = get_modified_global_coords(
            geometry=calc_target_one,
            kind='LINE'
        )
        dest_global_data = get_modified_global_coords(
            geometry=calc_target_two,
            kind='LINE'
        )
        src_line = src_global_data[1] - src_global_data[0]
        dest_line = dest_global_data[1] - dest_global_data[0]

        result_item.kind = 'LINE'
        result_item.line_start = start_loc
        result_item.line_end = src_line - dest_line
        if addon_data.calc_result_to_clipboard:
            addon_data.internal_storage_clipboard.kind = 'LINE'
            copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class ComposeNewLineVectorSubtraction(ComposeNewLineVectorSubtractionBase):
    bl_idname = "maplus.composenewlinevectorsubtraction"
    bl_label = "Subtract Lines"
    bl_description = (
        "Composes a new line item by performing vector-subtraction"
        " (first line minus second line)"
    )
    bl_options = {'REGISTER', 'UNDO'}


class QuickComposeNewLineVectorSubtraction(ComposeNewLineVectorSubtractionBase):
    bl_idname = "maplus.quickcomposenewlinevectorsubtraction"
    bl_label = "Subtract Lines"
    bl_description = (
        "Composes a new line item by performing vector-subtraction"
        " (first line minus second line)"
    )
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        if (addon_data.quick_calc_check_types and
                (addon_data.internal_storage_slot_1.kind != 'LINE' or
                 addon_data.internal_storage_slot_2.kind != 'LINE')):
            return False
        return True


class ComposePointIntersectingLinePlaneBase(bpy.types.Operator):
    bl_idname = "maplus.composepointintersectinglineplanebase"
    bl_label = "Intersect Line/Plane"
    bl_description = (
        "Composes a new point item by intersecting a line and a plane"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if hasattr(self, 'quick_calc_target'):
            active_calculation = addon_data
            result_item = active_calculation.quick_calc_result_item
            calc_target_one = addon_data.internal_storage_slot_1
            calc_target_two = addon_data.internal_storage_slot_2
        else:
            active_calculation = prims[addon_data.active_list_item]
            bpy.ops.maplus.addnewline()
            result_item = prims[-1]
            calc_target_one = prims[active_calculation.multi_calc_target_one]
            calc_target_two = prims[active_calculation.multi_calc_target_two]
        targets_by_kind = {
            item.kind: item for item in [calc_target_one, calc_target_two]
        }

        if not ('LINE' in targets_by_kind and 'PLANE' in targets_by_kind):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Intersect Line/Plane" can'
                 ' only operate on a line and a plane.')
            )
            return {'CANCELLED'}

        line_global_data = get_modified_global_coords(
            geometry=targets_by_kind['LINE'],
            kind='LINE'
        )
        plane_global_data = get_modified_global_coords(
            geometry=targets_by_kind['PLANE'],
            kind='PLANE'
        )

        plane_line_ba = plane_global_data[0] - plane_global_data[1]
        plane_line_bc = plane_global_data[2] - plane_global_data[1]
        plane_normal = plane_line_ba.cross(plane_line_bc)
        intersection = mathutils.geometry.intersect_line_plane(
            line_global_data[0],
            line_global_data[1],
            plane_global_data[1],
            plane_normal
        )

        if intersection:
            result_item.kind = 'POINT'
            result_item.point = intersection
            if addon_data.calc_result_to_clipboard:
                addon_data.internal_storage_clipboard.kind = 'POINT'
                copy_source_attribs_to_dest(
                    result_item,
                    addon_data.internal_storage_clipboard,
                    ("point",
                     "pt_make_unit_vec",
                     "pt_flip_direction",
                     "pt_multiplier")
                )
        else:
            self.report(
                {'ERROR'},
                'No intersection: Selected line/plane do not intersect'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class ComposePointIntersectingLinePlane(ComposePointIntersectingLinePlaneBase):
    bl_idname = "maplus.composepointintersectinglineplane"
    bl_label = "Intersect Line/Plane"
    bl_description = (
        "Composes a new point item by intersecting a line and a plane"
    )
    bl_options = {'REGISTER', 'UNDO'}


class QuickComposePointIntersectingLinePlane(ComposePointIntersectingLinePlaneBase):
    bl_idname = "maplus.quickcomposepointintersectinglineplane"
    bl_label = "Intersect Line/Plane"
    bl_description = (
        "Composes a new point item by intersecting a line and a plane"
    )
    bl_options = {'REGISTER', 'UNDO'}
    quick_calc_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data

        slot_kinds = set(
            [item.kind for item in [
                    addon_data.internal_storage_slot_1,
                    addon_data.internal_storage_slot_2
                ]
            ]
        )
        if (addon_data.quick_calc_check_types and
                ('LINE' not in slot_kinds or 'PLANE' not in slot_kinds)):
            return False
        return True


# Custom list, for displaying combined list of all primitives (Used at top
# of main panel and for item pointers in transformation primitives
class MAPlusList(bpy.types.UIList):

    def draw_item(self,
                  context,
                  layout,
                  data,
                  item,
                  icon,
                  active_data,
                  active_propname
                  ):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        # Check which type of primitive, separate draw code for each
        if item.kind == 'POINT':
            layout.label(item.name, icon="LAYER_ACTIVE")
        elif item.kind == 'LINE':
            layout.label(item.name, icon="MAN_TRANS")
        elif item.kind == 'PLANE':
            layout.label(item.name, icon="OUTLINER_OB_MESH")
        elif item.kind == 'CALCULATION':
            layout.label(item.name, icon="NODETREE")
        elif item.kind == 'TRANSFORMATION':
            layout.label(item.name, icon="MANIPUL")


def layout_coordvec(parent_layout,
                    coordvec_label,
                    op_id_cursor_grab,
                    op_id_avg_grab,
                    op_id_local_grab,
                    op_id_global_grab,
                    coord_container,
                    coord_attribute,
                    op_id_cursor_send,
                    op_id_text_tuple_swap_first=None,
                    op_id_text_tuple_swap_second=None):
    coordvec_container = parent_layout.column(align=True)
    coordvec_container.label(coordvec_label)
    type_or_grab_coords = coordvec_container.column()

    grab_buttons = type_or_grab_coords.row(align=True)
    grab_buttons.label("Grab:")
    grab_buttons.operator(
        op_id_cursor_grab,
        icon='CURSOR',
        text=""
    )
    grab_buttons.operator(
        op_id_avg_grab,
        icon='GROUP_VERTEX',
        text=""
    )
    grab_buttons.operator(
        op_id_local_grab,
        icon='VERTEXSEL',
        text=""
    )
    grab_buttons.operator(
        op_id_global_grab,
        icon='WORLD',
        text=""
    )

    type_or_grab_coords.prop(
        bpy.types.AnyType(coord_container),
        coord_attribute,
        ""
    )

    coordvec_lowers = type_or_grab_coords.row()

    if op_id_text_tuple_swap_first:
        coordvec_lowers.label("Swap:")
        if op_id_text_tuple_swap_second:
            aligned_swap_buttons = coordvec_lowers.row(align=True)
            aligned_swap_buttons.operator(
                op_id_text_tuple_swap_first[0],
                text=op_id_text_tuple_swap_first[1]
            )
            aligned_swap_buttons.operator(
                op_id_text_tuple_swap_second[0],
                text=op_id_text_tuple_swap_second[1]
            )
        else:
            coordvec_lowers.operator(
                op_id_text_tuple_swap_first[0],
                text=op_id_text_tuple_swap_first[1]
            )

    coordvec_lowers.label("Send:")
    coordvec_lowers.operator(
        op_id_cursor_send,
        icon='DRIVER',
        text=""
    )


# Advanced Tools panel
class MAPlusGui(bpy.types.Panel):
    bl_idname = "maplus_advanced_tools"
    bl_label = "Mesh Align Plus Advanced Tools"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        if len(prims) > 0:
            active_item = prims[addon_data.active_list_item]

        # We start with a row that holds the prim list and buttons
        # for adding/subtracting prims (the data management section
        # of the interface)
        maplus_data_mgmt_row = layout.row()
        maplus_items_list = maplus_data_mgmt_row.column()
        maplus_items_list.template_list(
            "MAPlusList",
            "",
            maplus_data_ptr,
            "prim_list",
            maplus_data_ptr,
            "active_list_item",
            type='DEFAULT'
        )
        add_remove_data_col = maplus_data_mgmt_row.column()
        add_new_items = add_remove_data_col.column(align=True)
        add_new_items.operator(
            "maplus.addnewpoint",
            icon='LAYER_ACTIVE',
            text=""
        )
        add_new_items.operator(
            "maplus.addnewline",
            icon='MAN_TRANS',
            text=""
        )
        add_new_items.operator(
            "maplus.addnewplane",
            icon='OUTLINER_OB_MESH',
            text=""
        )
        add_new_items.operator(
            "maplus.addnewcalculation",
            icon='NODETREE',
            text=""
        )
        add_new_items.operator(
            "maplus.addnewtransformation",
            icon='MANIPUL',
            text=""
        )
        add_remove_data_col.operator(
            "maplus.removelistitem",
            icon='X',
            text=""
        )

        # Items below data management section, this consists of either the
        # empty list message or the Primitive type selector (for when the
        # list is not empty, it allow users to choose the type of the
        # current primitive)
        if len(prims) == 0:
            layout.label("Add items above")
        else:
            basic_item_attribs_col = layout.column()
            basic_item_attribs_col.label("Item Name and Type:")
            item_name_and_types = basic_item_attribs_col.split(
                align=True,
                percentage=.8
            )
            item_name_and_types.prop(
                bpy.types.AnyType(active_item),
                'name',
                ""
            )
            item_name_and_types.prop(
                bpy.types.AnyType(active_item),
                'kind',
                ""
            )
            basic_item_attribs_col.separator()

            # Item-specific UI elements (primitive-specific data like coords
            # for plane points, transformation type etc.)
            item_info_col = layout.column()

            if active_item.kind == 'POINT':
                modifier_header = item_info_col.row()
                modifier_header.label("Point Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                apply_mods.operator(
                    "maplus.applygeommodifiers",
                    text="Apply Modifiers"
                )
                item_mods_box = item_info_col.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(active_item),
                    'pt_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(active_item),
                    'pt_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(active_item),
                    'pt_multiplier',
                    "Multiplier"
                )
                item_info_col.separator()

                item_info_col.label("Point Coordinates:")
                pt_grab_all = item_info_col.row(align=True)
                pt_grab_all.operator(
                    "maplus.grabpointfromcursor",
                    icon='CURSOR',
                    text="Grab Cursor"
                )
                pt_grab_all.operator(
                    "maplus.grabpointfromactivelocal",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                pt_grab_all.operator(
                    "maplus.grabpointfromactiveglobal",
                    icon='WORLD',
                    text="Grab All Global"
                )
                item_info_col.separator()
                special_grabs = item_info_col.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromadvtoolsactive",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintoadvtoolsactive",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )
                item_info_col.separator()

                layout_coordvec(
                    parent_layout=item_info_col,
                    coordvec_label="Point Coordinates:",
                    op_id_cursor_grab=(
                        "maplus.grabpointfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.pointgrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grabpointfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.grabpointfromactiveglobal"
                    ),
                    coord_container=active_item,
                    coord_attribute="point",
                    op_id_cursor_send=(
                        "maplus.sendpointtocursor"
                    )
                )

                item_info_col.separator()
                item_info_col.operator(
                    "maplus.duplicateitembase",
                    text="Duplicate Item"
                )

            elif active_item.kind == 'LINE':
                modifier_header = item_info_col.row()
                modifier_header.label("Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                apply_mods.operator(
                    "maplus.applygeommodifiers",
                    text="Apply Modifiers"
                )
                item_mods_box = item_info_col.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(active_item),
                    'ln_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(active_item),
                    'ln_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(active_item),
                    'ln_multiplier',
                    "Multiplier"
                )
                item_info_col.separator()

                item_info_col.label("Line Coordinates:")
                ln_grab_all = item_info_col.row(align=True)
                ln_grab_all.operator(
                    "maplus.graballvertslinelocal",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                ln_grab_all.operator(
                    "maplus.graballvertslineglobal",
                    icon='WORLD',
                    text="Grab All Global"
                )
                item_info_col.separator()
                special_grabs = item_info_col.row(align=True)
                special_grabs.operator(
                    "maplus.grabnormal",
                    icon='LAMP_HEMI',
                    text="Grab Normal"
                )
                item_info_col.separator()
                special_grabs_extra = item_info_col.row(align=True)
                special_grabs_extra.operator(
                    "maplus.copyfromadvtoolsactive",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs_extra.operator(
                    "maplus.pasteintoadvtoolsactive",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )
                item_info_col.separator()

                layout_coordvec(
                    parent_layout=item_info_col,
                    coordvec_label="Start:",
                    op_id_cursor_grab=(
                        "maplus.grablinestartfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.linestartgrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grablinestartfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.grablinestartfromactiveglobal"
                    ),
                    coord_container=active_item,
                    coord_attribute="line_start",
                    op_id_cursor_send=(
                        "maplus.sendlinestarttocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.swaplinepoints",
                        "End"
                    )
                )
                item_info_col.separator()

                layout_coordvec(
                    parent_layout=item_info_col,
                    coordvec_label="End:",
                    op_id_cursor_grab=(
                        "maplus.grablineendfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.lineendgrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grablineendfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.grablineendfromactiveglobal"
                    ),
                    coord_container=active_item,
                    coord_attribute="line_end",
                    op_id_cursor_send=(
                        "maplus.sendlineendtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.swaplinepoints",
                        "Start"
                    )
                )

                item_info_col.separator()
                item_info_col.operator(
                    "maplus.duplicateitembase",
                    text="Duplicate Item"
                )

            elif active_item.kind == 'PLANE':
                item_info_col.label("Plane Coordinates:")
                plane_grab_all = item_info_col.row(align=True)
                plane_grab_all.operator(
                    "maplus.graballvertsplanelocal",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                plane_grab_all.operator(
                    "maplus.graballvertsplaneglobal",
                    icon='WORLD',
                    text="Grab All Global"
                )
                item_info_col.separator()
                special_grabs = item_info_col.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromadvtoolsactive",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintoadvtoolsactive",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )
                item_info_col.separator()

                layout_coordvec(
                    parent_layout=item_info_col,
                    coordvec_label="Pt. A:",
                    op_id_cursor_grab=(
                        "maplus.grabplaneafromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.planeagrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grabplaneafromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.grabplaneafromactiveglobal"
                    ),
                    coord_container=active_item,
                    coord_attribute="plane_pt_a",
                    op_id_cursor_send=(
                        "maplus.sendplaneatocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.swapplaneaplaneb",
                        "B"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.swapplaneaplanec",
                        "C"
                    )
                )
                item_info_col.separator()

                layout_coordvec(
                    parent_layout=item_info_col,
                    coordvec_label="Pt. B:",
                    op_id_cursor_grab=(
                        "maplus.grabplanebfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.planebgrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grabplanebfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.grabplanebfromactiveglobal"
                    ),
                    coord_container=active_item,
                    coord_attribute="plane_pt_b",
                    op_id_cursor_send=(
                        "maplus.sendplanebtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.swapplaneaplaneb",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.swapplanebplanec",
                        "C"
                    )
                )
                item_info_col.separator()

                layout_coordvec(
                    parent_layout=item_info_col,
                    coordvec_label="Pt. C:",
                    op_id_cursor_grab=(
                        "maplus.grabplanecfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.planecgrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grabplanecfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.grabplanecfromactiveglobal"
                    ),
                    coord_container=active_item,
                    coord_attribute="plane_pt_c",
                    op_id_cursor_send=(
                        "maplus.sendplanectocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.swapplaneaplanec",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.swapplanebplanec",
                        "B"
                    )
                )

                item_info_col.separator()
                item_info_col.operator(
                    "maplus.duplicateitembase",
                    text="Duplicate Item"
                )

            elif active_item.kind == 'CALCULATION':
                item_info_col.label("Calculation Type:")
                calc_type_switcher = item_info_col.row()
                calc_type_switcher.operator(
                    "maplus.changecalctosingle",
                    # icon='ROTATECOLLECTION',
                    text="Single Item"
                )
                calc_type_switcher.operator(
                    "maplus.changecalctomulti",
                    # icon='ROTATECOLLECTION',
                    text="Multi-Item"
                )
                item_info_col.separator()
                if active_item.calc_type == 'SINGLEITEM':
                    item_info_col.label("Target:")
                    item_info_col.template_list(
                        "MAPlusList",
                        "single_calc_target_list",
                        maplus_data_ptr,
                        "prim_list",
                        active_item,
                        "single_calc_target",
                        type='DEFAULT'
                    )
                    item_info_col.separator()
                    calcs_and_results_header = item_info_col.row()
                    calcs_and_results_header.label(
                        "Available Calc.'s and Result:"
                    )
                    clipboard_row_right = calcs_and_results_header.row()
                    clipboard_row_right.alignment = 'RIGHT'
                    clipboard_row_right.prop(
                        bpy.types.AnyType(maplus_data_ptr),
                        'calc_result_to_clipboard',
                        "Copy to Clipboard"
                    )
                    item_info_col.prop(
                        bpy.types.AnyType(active_item),
                        'single_calc_result',
                        "Result"
                    )
                    # Check if the target pointer is valid, since we attempt
                    # to access that index in prims at the beginning here.
                    if active_item.single_calc_target < len(prims):
                        calc_target = prims[active_item.single_calc_target]
                        if calc_target.kind == 'POINT':
                            item_info_col.operator(
                                "maplus.composenewlinefrompoint",
                                icon='MAN_TRANS',
                                text="New Line from Point"
                            )
                        elif calc_target.kind == 'LINE':
                            item_info_col.operator(
                                "maplus.calclinelength",
                                text="Line Length"
                            )
                            item_info_col.operator(
                                "maplus.composenewlinefromorigin",
                                icon='MAN_TRANS',
                                text="New Line from Origin"
                            )
                        elif calc_target.kind == 'PLANE':
                            item_info_col.operator(
                                "maplus.composenormalfromplane",
                                icon='MAN_TRANS',
                                text="Get Plane Normal (Normalized)"
                            )
                elif active_item.calc_type == 'MULTIITEM':

                    item_info_col.label("Targets:")
                    calc_targets = item_info_col.row()
                    calc_targets.template_list(
                        "MAPlusList",
                        "multi_calc_target_one_list",
                        maplus_data_ptr,
                        "prim_list",
                        active_item,
                        "multi_calc_target_one",
                        type='DEFAULT'
                    )
                    calc_targets.template_list(
                        "MAPlusList",
                        "multi_calc_target_two_list",
                        maplus_data_ptr,
                        "prim_list",
                        active_item,
                        "multi_calc_target_two",
                        type='DEFAULT'
                    )
                    item_info_col.separator()
                    calcs_and_results_header = item_info_col.row()
                    calcs_and_results_header.label(
                        "Available Calc.'s and Result:"
                    )
                    clipboard_row_right = calcs_and_results_header.row()
                    clipboard_row_right.alignment = 'RIGHT'
                    clipboard_row_right.prop(
                        bpy.types.AnyType(maplus_data_ptr),
                        'calc_result_to_clipboard',
                        "Copy to Clipboard"
                    )
                    item_info_col.prop(
                        bpy.types.AnyType(active_item),
                        'multi_calc_result',
                        "Result"
                    )
                    # Check if the target pointers are valid, since we attempt
                    # to access those indices in prims at the beginning here.
                    if (active_item.multi_calc_target_one < len(prims) and
                            active_item.multi_calc_target_two < len(prims)):
                        calc_target_one = prims[
                            active_item.multi_calc_target_one
                        ]
                        calc_target_two = prims[
                            active_item.multi_calc_target_two
                        ]
                        type_combo = {
                            calc_target_one.kind,
                            calc_target_two.kind
                        }
                        if (calc_target_one.kind == 'POINT' and
                                calc_target_two.kind == 'POINT'):
                            item_info_col.operator(
                                "maplus.composenewlinefrompoints",
                                icon='MAN_TRANS',
                                text="New Line from Points"
                            )
                            item_info_col.operator(
                                "maplus.calcdistancebetweenpoints",
                                text="Distance Between Points"
                            )
                        elif (calc_target_one.kind == 'LINE' and
                                calc_target_two.kind == 'LINE'):
                            item_info_col.operator(
                                "maplus.calcrotationaldiff",
                                text="Angle of Lines"
                            )
                            item_info_col.operator(
                                "maplus.composenewlinevectoraddition",
                                icon='MAN_TRANS',
                                text="Add Lines"
                            )
                            item_info_col.operator(
                                "maplus.composenewlinevectorsubtraction",
                                icon='MAN_TRANS',
                                text="Subtract Lines"
                            )
                        elif 'POINT' in type_combo and 'LINE' in type_combo:
                            item_info_col.operator(
                                "maplus.composenewlineatpointlocation",
                                icon='MAN_TRANS',
                                text="New Line at Point"
                            )
                        elif 'LINE' in type_combo and 'PLANE' in type_combo:
                            item_info_col.operator(
                                "maplus.composepointintersectinglineplane",
                                icon='LAYER_ACTIVE',
                                text="Intersect Line/Plane"
                            )

            elif active_item.kind == 'TRANSFORMATION':
                item_info_col.label("Transformation Type Selectors:")
                transf_types = item_info_col.row(align=True)
                transf_types.operator(
                    "maplus.changetransftoalignpoints",
                    icon='ROTATECOLLECTION',
                    text="Align Points"
                )
                transf_types.operator(
                    "maplus.changetransftoalignlines",
                    icon='SNAP_EDGE',
                    text="Align Lines"
                )
                transf_types.operator(
                    "maplus.changetransftoalignplanes",
                    icon='MOD_ARRAY',
                    text="Align Planes"
                )
                transf_types.operator(
                    "maplus.changetransftodirectionalslide",
                    icon='CURVE_PATH',
                    text="Directional Slide"
                )
                transf_types.operator(
                    "maplus.changetransftoscalematchedge",
                    icon='FULLSCREEN_ENTER',
                    text="Scale Match Edge"
                )
                transf_types.operator(
                    "maplus.changetransftoaxisrotate",
                    icon='FORCE_MAGNETIC',
                    text="Axis Rotate"
                )
                item_info_col.separator()

                if active_item.transf_type == "UNDEFINED":
                    item_info_col.label("Select a transformation above")
                else:
                    apply_buttons_header = item_info_col.row()
                    if active_item.transf_type == 'ALIGNPOINTS':
                        apply_buttons_header.label('Apply Align Points to:')
                        apply_buttons = item_info_col.split(percentage=.33)
                        apply_buttons.operator(
                            "maplus.alignpointsobject",
                            icon='NONE',
                            text="Object"
                        )
                        mesh_appliers = apply_buttons.row(align=True)
                        mesh_appliers.operator(
                            "maplus.alignpointsmeshselected",
                            icon='NONE',
                            text="Mesh Piece"
                        )
                        mesh_appliers.operator(
                            "maplus.alignpointswholemesh",
                            icon='NONE',
                            text=" Whole Mesh"
                        )
                    elif active_item.transf_type == 'DIRECTIONALSLIDE':
                        apply_buttons_header.label(
                            'Apply Directional Slide to:'
                        )
                        apply_buttons = item_info_col.split(percentage=.33)
                        apply_buttons.operator(
                            "maplus.directionalslideobject",
                            icon='NONE',
                            text="Object"
                        )
                        mesh_appliers = apply_buttons.row(align=True)
                        mesh_appliers.operator(
                            "maplus.directionalslidemeshselected",
                            icon='NONE', text="Mesh Piece"
                        )
                        mesh_appliers.operator(
                            "maplus.directionalslidewholemesh",
                            icon='NONE',
                            text="Whole Mesh"
                        )
                    elif active_item.transf_type == 'SCALEMATCHEDGE':
                        apply_buttons_header.label(
                            'Apply Scale Match Edge to:'
                        )
                        apply_buttons = item_info_col.split(percentage=.33)
                        apply_buttons.operator(
                            "maplus.scalematchedgeobject",
                            icon='NONE',
                            text="Object"
                        )
                        mesh_appliers = apply_buttons.row(align=True)
                        mesh_appliers.operator(
                            "maplus.scalematchedgemeshselected",
                            icon='NONE', text="Mesh Piece"
                        )
                        mesh_appliers.operator(
                            "maplus.scalematchedgewholemesh",
                            icon='NONE',
                            text="Whole Mesh"
                        )
                    elif active_item.transf_type == 'AXISROTATE':
                        apply_buttons_header.label('Apply Axis Rotate to:')
                        apply_buttons = item_info_col.split(percentage=.33)
                        apply_buttons.operator(
                            "maplus.axisrotateobject",
                            icon='NONE',
                            text="Object"
                        )
                        mesh_appliers = apply_buttons.row(align=True)
                        mesh_appliers.operator(
                            "maplus.axisrotatemeshselected",
                            icon='NONE', text="Mesh Piece"
                        )
                        mesh_appliers.operator(
                            "maplus.axisrotatewholemesh",
                            icon='NONE',
                            text="Whole Mesh"
                        )
                    elif active_item.transf_type == 'ALIGNLINES':
                        apply_buttons_header.label('Apply Align Lines to:')
                        apply_buttons = item_info_col.split(percentage=.33)
                        apply_buttons.operator(
                            "maplus.alignlinesobject",
                            icon='NONE',
                            text="Object"
                        )
                        mesh_appliers = apply_buttons.row(align=True)
                        mesh_appliers.operator(
                            "maplus.alignlinesmeshselected",
                            icon='NONE',
                            text="Mesh Piece"
                        )
                        mesh_appliers.operator(
                            "maplus.alignlineswholemesh",
                            icon='NONE',
                            text="Whole Mesh"
                        )
                    elif active_item.transf_type == 'ALIGNPLANES':
                        apply_buttons_header.label('Apply Align Planes to:')
                        apply_buttons = item_info_col.split(percentage=.33)
                        apply_buttons.operator(
                            "maplus.alignplanesobject",
                            icon='NONE',
                            text="Object"
                        )
                        mesh_appliers = apply_buttons.row(align=True)
                        mesh_appliers.operator(
                            "maplus.alignplanesmeshselected",
                            icon='NONE',
                            text="Mesh Piece"
                        )
                        mesh_appliers.operator(
                            "maplus.alignplaneswholemesh",
                            icon='NONE',
                            text="Whole Mesh"
                        )
                    item_info_col.separator()
                    experiment_toggle = apply_buttons_header.column()
                    experiment_toggle.prop(
                            addon_data,
                            'use_experimental',
                            'Enable Experimental Mesh Ops.'
                    )

                    active_transf = bpy.types.AnyType(active_item)

                    if (active_item.transf_type != 'SCALEMATCHEDGE' and
                            active_item.transf_type != 'AXISROTATE'):
                        item_info_col.label('Transformation Modifiers:')
                        item_mods_box = item_info_col.box()
                        mods_row_1 = item_mods_box.row()
                        mods_row_2 = item_mods_box.row()
                    if active_item.transf_type == "ALIGNPOINTS":
                        mods_row_1.prop(
                            active_transf,
                            'apt_make_unit_vector',
                            'Set Length Equal to One'
                        )
                        mods_row_1.prop(
                            active_transf,
                            'apt_flip_direction',
                            'Flip Direction'
                        )
                        mods_row_2.prop(
                            active_transf,
                            'apt_multiplier',
                            'Multiplier'
                        )
                    if active_item.transf_type == "DIRECTIONALSLIDE":
                        item_info_col.label('Item Modifiers:')
                        mods_row_1.prop(
                            active_transf,
                            'ds_make_unit_vec',
                            "Set Length Equal to One"
                        )
                        mods_row_1.prop(
                            active_transf,
                            'ds_flip_direction',
                            "Flip Direction"
                        )
                        mods_row_2.prop(
                            active_transf,
                            'ds_multiplier',
                            "Multiplier"
                        )
                    if active_item.transf_type == "ALIGNLINES":
                        mods_row_1.prop(
                            active_transf,
                            'aln_flip_direction',
                            "Flip Direction"
                        )
                    if active_item.transf_type == "ALIGNPLANES":
                        mods_row_1.prop(
                            active_transf,
                            'apl_flip_normal',
                            "Flip Source Normal"
                        )
                        # Todo: determine how to handle this from Adv. Tools
                        # ('use' arg only valid from a 3d view editor/context)
                        # mods_row_1.prop(
                        #    active_transf,
                        #    'apl_use_custom_orientation',
                        #    "Use Transf. Orientation"
                        # )
                    item_info_col.separator()

                    # Designate operands for the transformation by pointing to
                    # other primitive items in the main list. The indices are
                    # stored on each primitive item
                    if active_item.transf_type == "ALIGNPOINTS":
                        item_info_col.label("Source Point")
                        item_info_col.template_list(
                            "MAPlusList",
                            "apt_pt_one_list",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "apt_pt_one",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.label("Destination Point")
                        item_info_col.template_list(
                            "MAPlusList",
                            "apt_pt_two_list",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "apt_pt_two",
                            type='DEFAULT'
                        )
                    if active_item.transf_type == "DIRECTIONALSLIDE":
                        item_info_col.label("Source Line")
                        item_info_col.template_list(
                            "MAPlusList",
                            "vs_targetLineList",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "ds_direction",
                            type='DEFAULT'
                        )
                    if active_item.transf_type == "SCALEMATCHEDGE":
                        item_info_col.label("Source Edge")
                        item_info_col.template_list(
                            "MAPlusList",
                            "sme_src_edgelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "sme_edge_one",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.label("Destination Edge")
                        item_info_col.template_list(
                            "MAPlusList",
                            "sme_dest_edgelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "sme_edge_two",
                            type='DEFAULT'
                        )
                    if active_item.transf_type == "AXISROTATE":
                        item_info_col.label("Axis")
                        item_info_col.template_list(
                            "MAPlusList",
                            "axr_src_axis",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "axr_axis",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.prop(
                            active_transf,
                            'axr_amount',
                            'Amount'
                        )
                    if active_item.transf_type == "ALIGNLINES":
                        item_info_col.label("Source Line")
                        item_info_col.template_list(
                            "MAPlusList",
                            "aln_src_linelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "aln_src_line",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.label("Destination Line")
                        item_info_col.template_list(
                            "MAPlusList",
                            "aln_dest_linelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "aln_dest_line",
                            type='DEFAULT'
                        )
                    if active_item.transf_type == "ALIGNPLANES":
                        item_info_col.label("Source Plane")
                        item_info_col.template_list(
                            "MAPlusList",
                            "apl_src_planelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "apl_src_plane",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.label("Destination Plane")
                        item_info_col.template_list(
                            "MAPlusList",
                            "apl_dest_planelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "apl_dest_plane",
                            type='DEFAULT'
                        )


class QuickAlignPointsGUI(bpy.types.Panel):
    bl_idname = "quick_align_points_gui"
    bl_label = "Quick Align Points"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        apg_top = layout.row()
        align_pts_gui = layout.box()
        apg_top.label(
            "Align Points",
            icon="ROTATECOLLECTION"
        )
        apt_grab_col = align_pts_gui.column()
        apt_grab_col.prop(
            addon_data,
            'quick_align_pts_auto_grab_src',
            'Auto Grab Source from Selected Vertices'
        )

        apt_src_geom_top = apt_grab_col.row(align=True)
        if not addon_data.quick_align_pts_auto_grab_src:
            if not addon_data.quick_apt_show_src_geom:
                apt_src_geom_top.operator(
                        "maplus.showhidequickaptsrcgeom",
                        icon='TRIA_RIGHT',
                        text="",
                        emboss=False
                )
                preserve_button_roundedge = apt_src_geom_top.row()
                preserve_button_roundedge.operator(
                        "maplus.quickalignpointsgrabsrc",
                        icon='LAYER_ACTIVE',
                        text="Grab Source"
                )
                preserve_button_roundedge.operator(
                        "maplus.quickaptgrabavgsrc",
                        icon='GROUP_VERTEX',
                        text=""
                )

            else:
                apt_src_geom_top.operator(
                        "maplus.showhidequickaptsrcgeom",
                        icon='TRIA_DOWN',
                        text="",
                        emboss=False
                )
                apt_src_geom_top.label("Source Coordinates", icon="LAYER_ACTIVE")

                apt_src_geom_editor = apt_grab_col.box()
                pt_grab_all = apt_src_geom_editor.row(align=True)
                pt_grab_all.operator(
                    "maplus.quickalignpointsgrabsrcloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                pt_grab_all.operator(
                    "maplus.quickalignpointsgrabsrc",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = apt_src_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromaptsrc",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintoaptsrc",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = apt_src_geom_editor.row()
                modifier_header.label("Point Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = apt_src_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_align_pts_src),
                    'pt_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_align_pts_src),
                    'pt_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_align_pts_src),
                    'pt_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=apt_src_geom_editor,
                    coordvec_label="Pt. Origin:",
                    op_id_cursor_grab=(
                        "maplus.quickaptsrcgrabpointfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickaptgrabavgsrc"
                    ),
                    op_id_local_grab=(
                        "maplus.quickalignpointsgrabsrcloc"
                    ),
                    op_id_global_grab=(
                        "maplus.quickalignpointsgrabsrc"
                    ),
                    coord_container=addon_data.quick_align_pts_src,
                    coord_attribute="point",
                    op_id_cursor_send=(
                        "maplus.quickaptsrcsendpointtocursor"
                    )
                )

        if addon_data.quick_apt_show_src_geom:
            apt_grab_col.separator()

        apt_dest_geom_top = apt_grab_col.row(align=True)
        if not addon_data.quick_apt_show_dest_geom:
            apt_dest_geom_top.operator(
                    "maplus.showhidequickaptdestgeom",
                    icon='TRIA_RIGHT',
                    text="",
                    emboss=False
            )
            preserve_button_roundedge = apt_dest_geom_top.row()
            preserve_button_roundedge.operator(
                    "maplus.quickalignpointsgrabdest",
                    icon='LAYER_ACTIVE',
                    text="Grab Destination"
            )
            preserve_button_roundedge.operator(
                    "maplus.quickaptgrabavgdest",
                    icon='GROUP_VERTEX',
                    text=""
            )

        else:
            apt_dest_geom_top.operator(
                    "maplus.showhidequickaptdestgeom",
                    icon='TRIA_DOWN',
                    text="",
                    emboss=False
            )
            apt_dest_geom_top.label("Destination Coordinates", icon="LAYER_ACTIVE")

            apt_dest_geom_editor = apt_grab_col.box()
            pt_grab_all = apt_dest_geom_editor.row(align=True)
            pt_grab_all.operator(
                "maplus.quickalignpointsgrabdestloc",
                icon='VERTEXSEL',
                text="Grab All Local"
            )
            pt_grab_all.operator(
                "maplus.quickalignpointsgrabdest",
                icon='WORLD',
                text="Grab All Global"
            )
            special_grabs = apt_dest_geom_editor.row(align=True)
            special_grabs.operator(
                "maplus.copyfromaptdest",
                icon='COPYDOWN',
                text="Copy (To Clipboard)"
            )
            special_grabs.operator(
                "maplus.pasteintoaptdest",
                icon='PASTEDOWN',
                text="Paste (From Clipboard)"
            )

            modifier_header = apt_dest_geom_editor.row()
            modifier_header.label("Point Modifiers:")
            apply_mods = modifier_header.row()
            apply_mods.alignment = 'RIGHT'

            item_mods_box = apt_dest_geom_editor.box()
            mods_row_1 = item_mods_box.row()
            mods_row_1.prop(
                bpy.types.AnyType(addon_data.quick_align_pts_dest),
                'pt_make_unit_vec',
                "Set Length Equal to One"
            )
            mods_row_1.prop(
                bpy.types.AnyType(addon_data.quick_align_pts_dest),
                'pt_flip_direction',
                "Flip Direction"
            )
            mods_row_2 = item_mods_box.row()
            mods_row_2.prop(
                bpy.types.AnyType(addon_data.quick_align_pts_dest),
                'pt_multiplier',
                "Multiplier"
            )

            layout_coordvec(
                parent_layout=apt_dest_geom_editor,
                coordvec_label="Pt. Origin:",
                op_id_cursor_grab=(
                    "maplus.quickaptdestgrabpointfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quickaptgrabavgdest"
                ),
                op_id_local_grab=(
                    "maplus.quickalignpointsgrabdestloc"
                ),
                op_id_global_grab=(
                    "maplus.quickalignpointsgrabdest"
                ),
                coord_container=addon_data.quick_align_pts_dest,
                coord_attribute="point",
                op_id_cursor_send=(
                    "maplus.quickaptdestsendpointtocursor"
                )
            )

        align_pts_gui.label("Operator settings:", icon="SCRIPTWIN")
        apt_mods = align_pts_gui.box()
        apt_box_row1 = apt_mods.row()
        apt_box_row1.prop(
            addon_data.quick_align_pts_transf,
            'apt_make_unit_vector',
            'Set Length to 1'
        )
        apt_box_row1.prop(
            addon_data.quick_align_pts_transf,
            'apt_flip_direction',
            'Flip Direction'
        )
        apt_box_row2 = apt_mods.row()
        apt_box_row2.prop(
            addon_data.quick_align_pts_transf,
            'apt_multiplier',
            'Multiplier'
        )
        apt_apply_header = align_pts_gui.row()
        apt_apply_header.label("Apply to:")
        apt_apply_header.prop(
            addon_data,
            'use_experimental',
            'Enable Experimental Mesh Ops.'
        )
        apt_apply_items = align_pts_gui.split(percentage=.33)
        apt_apply_items.operator(
            "maplus.quickalignpointsobject",
            text="Object"
        )
        apt_mesh_apply_items = apt_apply_items.row(align=True)
        apt_mesh_apply_items.operator(
            "maplus.quickalignpointsmeshselected",
            text="Mesh Piece"
        )
        apt_mesh_apply_items.operator(
            "maplus.quickalignpointswholemesh",
            text="Whole Mesh"
        )


class QuickAlignLinesGUI(bpy.types.Panel):
    bl_idname = "quick_align_lines_gui"
    bl_label = "Quick Align Lines"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        aln_top = layout.row()
        aln_gui = layout.box()
        aln_top.label(
            "Align Lines",
            icon="SNAP_EDGE"
        )
        aln_grab_col = aln_gui.column()
        aln_grab_col.prop(
            addon_data,
            'quick_align_lines_auto_grab_src',
            'Auto Grab Source from Selected Vertices'
        )

        aln_src_geom_top = aln_grab_col.row(align=True)
        if not addon_data.quick_align_lines_auto_grab_src:
            if not addon_data.quick_aln_show_src_geom:
                aln_src_geom_top.operator(
                        "maplus.showhidequickalnsrcgeom",
                        icon='TRIA_RIGHT',
                        text="",
                        emboss=False
                )
                preserve_button_roundedge = aln_src_geom_top.row()
                preserve_button_roundedge.operator(
                        "maplus.quickalignlinesgrabsrc",
                        icon='MAN_TRANS',
                        text="Grab Source"
                )
                preserve_button_roundedge.operator(
                    "maplus.quickalngrabnormalsrc",
                    icon='LAMP_HEMI',
                    text=""
                )
            else:
                aln_src_geom_top.operator(
                        "maplus.showhidequickalnsrcgeom",
                        icon='TRIA_DOWN',
                        text="",
                        emboss=False
                )
                aln_src_geom_top.label("Source Coordinates", icon="MAN_TRANS")

                aln_src_geom_editor = aln_grab_col.box()
                ln_grab_all = aln_src_geom_editor.row(align=True)
                ln_grab_all.operator(
                    "maplus.quickalignlinesgrabsrcloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                ln_grab_all.operator(
                    "maplus.quickalignlinesgrabsrc",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = aln_src_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.quickalngrabnormalsrc",
                    icon='LAMP_HEMI',
                    text="Grab Normal"
                )
                special_grabs_extra = aln_src_geom_editor.row(align=True)
                special_grabs_extra.operator(
                    "maplus.copyfromalnsrc",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs_extra.operator(
                    "maplus.pasteintoalnsrc",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = aln_src_geom_editor.row()
                modifier_header.label("Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = aln_src_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_align_lines_src),
                    'ln_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_align_lines_src),
                    'ln_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_align_lines_src),
                    'ln_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=aln_src_geom_editor,
                    coordvec_label="Start:",
                    op_id_cursor_grab=(
                        "maplus.quickalnsrcgrablinestartfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickalngrabavgsrclinestart"
                    ),
                    op_id_local_grab=(
                        "maplus.quickalnsrcgrablinestartfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickalnsrcgrablinestartfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_align_lines_src,
                    coord_attribute="line_start",
                    op_id_cursor_send=(
                        "maplus.quickalnsrcsendlinestarttocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickalnsrcswaplinepoints",
                        "End"
                    )
                )

                layout_coordvec(
                    parent_layout=aln_src_geom_editor,
                    coordvec_label="End:",
                    op_id_cursor_grab=(
                        "maplus.quickalnsrcgrablineendfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickalngrabavgsrclineend"
                    ),
                    op_id_local_grab=(
                        "maplus.quickalnsrcgrablineendfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickalnsrcgrablineendfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_align_lines_src,
                    coord_attribute="line_end",
                    op_id_cursor_send=(
                        "maplus.quickalnsrcsendlineendtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickalnsrcswaplinepoints",
                        "Start"
                    )
                )

        if addon_data.quick_aln_show_src_geom:
            aln_grab_col.separator()

        aln_dest_geom_top = aln_grab_col.row(align=True)
        if not addon_data.quick_aln_show_dest_geom:
            aln_dest_geom_top.operator(
                    "maplus.showhidequickalndestgeom",
                    icon='TRIA_RIGHT',
                    text="",
                    emboss=False
            )
            preserve_button_roundedge = aln_dest_geom_top.row()
            preserve_button_roundedge.operator(
                    "maplus.quickalignlinesgrabdest",
                    icon='MAN_TRANS',
                    text="Grab Destination"
            )
            preserve_button_roundedge.operator(
                "maplus.quickalngrabnormaldest",
                icon='LAMP_HEMI',
                text=""
            )
        else:
            aln_dest_geom_top.operator(
                    "maplus.showhidequickalndestgeom",
                    icon='TRIA_DOWN',
                    text="",
                    emboss=False
            )
            aln_dest_geom_top.label("Destination Coordinates", icon="MAN_TRANS")

            aln_dest_geom_editor = aln_grab_col.box()
            ln_grab_all = aln_dest_geom_editor.row(align=True)
            ln_grab_all.operator(
                "maplus.quickalignlinesgrabdestloc",
                icon='VERTEXSEL',
                text="Grab All Local"
            )
            ln_grab_all.operator(
                "maplus.quickalignlinesgrabdest",
                icon='WORLD',
                text="Grab All Global"
            )
            special_grabs = aln_dest_geom_editor.row(align=True)
            special_grabs.operator(
                "maplus.quickalngrabnormaldest",
                icon='LAMP_HEMI',
                text="Grab Normal"
            )
            special_grabs_extra = aln_dest_geom_editor.row(align=True)
            special_grabs_extra.operator(
                "maplus.copyfromalndest",
                icon='COPYDOWN',
                text="Copy (To Clipboard)"
            )
            special_grabs_extra.operator(
                "maplus.pasteintoalndest",
                icon='PASTEDOWN',
                text="Paste (From Clipboard)"
            )

            modifier_header = aln_dest_geom_editor.row()
            modifier_header.label("Line Modifiers:")
            apply_mods = modifier_header.row()
            apply_mods.alignment = 'RIGHT'

            item_mods_box = aln_dest_geom_editor.box()
            mods_row_1 = item_mods_box.row()
            mods_row_1.prop(
                bpy.types.AnyType(addon_data.quick_align_lines_dest),
                'ln_make_unit_vec',
                "Set Length Equal to One"
            )
            mods_row_1.prop(
                bpy.types.AnyType(addon_data.quick_align_lines_dest),
                'ln_flip_direction',
                "Flip Direction"
            )
            mods_row_2 = item_mods_box.row()
            mods_row_2.prop(
                bpy.types.AnyType(addon_data.quick_align_lines_dest),
                'ln_multiplier',
                "Multiplier"
            )

            layout_coordvec(
                parent_layout=aln_dest_geom_editor,
                coordvec_label="Start:",
                op_id_cursor_grab=(
                    "maplus.quickalndestgrablinestartfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quickalngrabavgdestlinestart"
                ),
                op_id_local_grab=(
                    "maplus.quickalndestgrablinestartfromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quickalndestgrablinestartfromactiveglobal"
                ),
                coord_container=addon_data.quick_align_lines_dest,
                coord_attribute="line_start",
                op_id_cursor_send=(
                    "maplus.quickalndestsendlinestarttocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quickalndestswaplinepoints",
                    "End"
                )
            )

            layout_coordvec(
                parent_layout=aln_dest_geom_editor,
                coordvec_label="End:",
                op_id_cursor_grab=(
                    "maplus.quickalndestgrablineendfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quickalngrabavgdestlineend"
                ),
                op_id_local_grab=(
                    "maplus.quickalndestgrablineendfromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quickalndestgrablineendfromactiveglobal"
                ),
                coord_container=addon_data.quick_align_lines_dest,
                coord_attribute="line_end",
                op_id_cursor_send=(
                    "maplus.quickalndestsendlineendtocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quickalndestswaplinepoints",
                    "Start"
                )
            )

        aln_gui.label("Operator settings:", icon="SCRIPTWIN")
        aln_mods = aln_gui.box()
        aln_mods_row1 = aln_mods.row()
        aln_mods_row1.prop(
            addon_data.quick_align_lines_transf,
            'aln_flip_direction',
            'Flip Direction'
        )
        aln_apply_header = aln_gui.row()
        aln_apply_header.label("Apply to:")
        aln_apply_header.prop(
            addon_data,
            'use_experimental',
            'Enable Experimental Mesh Ops.'
        )
        aln_apply_items = aln_gui.split(percentage=.33)
        aln_apply_items.operator(
            "maplus.quickalignlinesobject",
            text="Object"
        )
        aln_mesh_apply_items = aln_apply_items.row(align=True)
        aln_mesh_apply_items.operator(
            "maplus.quickalignlinesmeshselected",
            text="Mesh Piece"
        )
        aln_mesh_apply_items.operator(
            "maplus.quickalignlineswholemesh",
            text="Whole Mesh"
        )


class QuickAlignPlanesGUI(bpy.types.Panel):
    bl_idname = "quick_align_planes_gui"
    bl_label = "Quick Align Planes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        apl_top = layout.row()
        apl_gui = layout.box()
        apl_top.label(
            "Align Planes",
            icon="MOD_ARRAY"
        )
        apl_grab_col = apl_gui.column()
        apl_grab_col.prop(
            addon_data,
            'quick_align_planes_auto_grab_src',
            'Auto Grab Source from Selected Vertices'
        )

        apl_src_geom_top = apl_grab_col.row(align=True)
        if not addon_data.quick_align_planes_auto_grab_src:
            if not addon_data.quick_apl_show_src_geom:
                apl_src_geom_top.operator(
                    "maplus.showhidequickaplsrcgeom",
                    icon='TRIA_RIGHT',
                    text="",
                    emboss=False
                )
                preserve_button_roundedge = apl_src_geom_top.row()
                preserve_button_roundedge.operator(
                    "maplus.quickalignplanesgrabsrc",
                    icon='OUTLINER_OB_MESH',
                    text="Grab Source"
                )
            else:
                apl_src_geom_top.operator(
                    "maplus.showhidequickaplsrcgeom",
                    icon='TRIA_DOWN',
                    text="",
                    emboss=False
                )
                apl_src_geom_top.label("Source Coordinates", icon="OUTLINER_OB_MESH")

                apl_src_geom_editor = apl_grab_col.box()
                plane_grab_all = apl_src_geom_editor.row(align=True)
                plane_grab_all.operator(
                    "maplus.quickalignplanesgrabsrcloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                plane_grab_all.operator(
                    "maplus.quickalignplanesgrabsrc",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = apl_src_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromaplsrc",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintoaplsrc",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                layout_coordvec(
                    parent_layout=apl_src_geom_editor,
                    coordvec_label="Pt. A:",
                    op_id_cursor_grab=(
                        "maplus.quickaplsrcgrabplaneafromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickaplgrabavgsrcplanea"
                    ),
                    op_id_local_grab=(
                        "maplus.quickaplsrcgrabplaneafromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickaplsrcgrabplaneafromactiveglobal"
                    ),
                    coord_container=addon_data.quick_align_planes_src,
                    coord_attribute="plane_pt_a",
                    op_id_cursor_send=(
                        "maplus.quickaplsrcsendplaneatocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickaplsrcswapplaneaplaneb",
                        "B"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.quickaplsrcswapplaneaplanec",
                        "C"
                    )
                )

                layout_coordvec(
                    parent_layout=apl_src_geom_editor,
                    coordvec_label="Pt. B (Pivot):",
                    op_id_cursor_grab=(
                        "maplus.quickaplsrcgrabplanebfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickaplgrabavgsrcplaneb"
                    ),
                    op_id_local_grab=(
                        "maplus.quickaplsrcgrabplanebfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickaplsrcgrabplanebfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_align_planes_src,
                    coord_attribute="plane_pt_b",
                    op_id_cursor_send=(
                        "maplus.quickaplsrcsendplanebtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickaplsrcswapplaneaplaneb",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.quickaplsrcswapplanebplanec",
                        "C"
                    )
                )

                layout_coordvec(
                    parent_layout=apl_src_geom_editor,
                    coordvec_label="Pt. C:",
                    op_id_cursor_grab=(
                        "maplus.quickaplsrcgrabplanecfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickaplgrabavgsrcplanec"
                    ),
                    op_id_local_grab=(
                        "maplus.quickaplsrcgrabplanecfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickaplsrcgrabplanecfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_align_planes_src,
                    coord_attribute="plane_pt_c",
                    op_id_cursor_send=(
                        "maplus.quickaplsrcsendplanectocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickaplsrcswapplaneaplanec",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.quickaplsrcswapplanebplanec",
                        "B"
                    )
                )

        if addon_data.quick_apl_show_src_geom:
            apl_grab_col.separator()

        apl_dest_geom_top = apl_grab_col.row(align=True)
        if not addon_data.quick_apl_show_dest_geom:
            apl_dest_geom_top.operator(
                    "maplus.showhidequickapldestgeom",
                    icon='TRIA_RIGHT',
                    text="",
                    emboss=False
            )
            preserve_button_roundedge = apl_dest_geom_top.row()
            preserve_button_roundedge.operator(
                    "maplus.quickalignplanesgrabdest",
                    icon='OUTLINER_OB_MESH',
                    text="Grab Destination"
            )
        else:
            apl_dest_geom_top.operator(
                    "maplus.showhidequickapldestgeom",
                    icon='TRIA_DOWN',
                    text="",
                    emboss=False
            )
            apl_dest_geom_top.label("Destination Coordinates", icon="OUTLINER_OB_MESH")

            apl_dest_geom_editor = apl_grab_col.box()
            plane_grab_all = apl_dest_geom_editor.row(align=True)
            plane_grab_all.operator(
                "maplus.quickalignplanesgrabdestloc",
                icon='VERTEXSEL',
                text="Grab All Local"
            )
            plane_grab_all.operator(
                "maplus.quickalignplanesgrabdest",
                icon='WORLD',
                text="Grab All Global"
            )
            special_grabs = apl_dest_geom_editor.row(align=True)
            special_grabs.operator(
                "maplus.copyfromapldest",
                icon='COPYDOWN',
                text="Copy (To Clipboard)"
            )
            special_grabs.operator(
                "maplus.pasteintoapldest",
                icon='PASTEDOWN',
                text="Paste (From Clipboard)"
            )

            layout_coordvec(
                parent_layout=apl_dest_geom_editor,
                coordvec_label="Pt. A:",
                op_id_cursor_grab=(
                    "maplus.quickapldestgrabplaneafromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quickaplgrabavgdestplanea"
                ),
                op_id_local_grab=(
                    "maplus.quickapldestgrabplaneafromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quickapldestgrabplaneafromactiveglobal"
                ),
                coord_container=addon_data.quick_align_planes_dest,
                coord_attribute="plane_pt_a",
                op_id_cursor_send=(
                    "maplus.quickapldestsendplaneatocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quickapldestswapplaneaplaneb",
                    "B"
                ),
                op_id_text_tuple_swap_second=(
                    "maplus.quickapldestswapplaneaplanec",
                    "C"
                )
            )

            layout_coordvec(
                parent_layout=apl_dest_geom_editor,
                coordvec_label="Pt. B (Pivot):",
                op_id_cursor_grab=(
                    "maplus.quickapldestgrabplanebfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quickaplgrabavgdestplaneb"
                ),
                op_id_local_grab=(
                    "maplus.quickapldestgrabplanebfromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quickapldestgrabplanebfromactiveglobal"
                ),
                coord_container=addon_data.quick_align_planes_dest,
                coord_attribute="plane_pt_b",
                op_id_cursor_send=(
                    "maplus.quickapldestsendplanebtocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quickapldestswapplaneaplaneb",
                    "A"
                ),
                op_id_text_tuple_swap_second=(
                    "maplus.quickapldestswapplanebplanec",
                    "C"
                )
            )

            layout_coordvec(
                parent_layout=apl_dest_geom_editor,
                coordvec_label="Pt. C:",
                op_id_cursor_grab=(
                    "maplus.quickapldestgrabplanecfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quickaplgrabavgdestplanec"
                ),
                op_id_local_grab=(
                    "maplus.quickapldestgrabplanecfromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quickapldestgrabplanecfromactiveglobal"
                ),
                coord_container=addon_data.quick_align_planes_dest,
                coord_attribute="plane_pt_c",
                op_id_cursor_send=(
                    "maplus.quickapldestsendplanectocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quickapldestswapplaneaplanec",
                    "A"
                ),
                op_id_text_tuple_swap_second=(
                    "maplus.quickapldestswapplanebplanec",
                    "B"
                )
            )

        apl_gui.label("Operator settings:", icon="SCRIPTWIN")
        apl_mods = apl_gui.box()
        apl_mods_row1 = apl_mods.row()
        apl_mods_row1.prop(
            addon_data.quick_align_planes_transf,
            'apl_flip_normal',
            'Flip Normal'
        )
        apl_mods_row1.prop(
            addon_data.quick_align_planes_transf,
            'apl_use_custom_orientation',
            'Use Transf. Orientation'
        )
        apl_apply_header = apl_gui.row()
        apl_apply_header.label("Apply to:")
        apl_apply_header.prop(
            addon_data,
            'use_experimental',
            'Enable Experimental Mesh Ops.'
        )
        apl_apply_items = apl_gui.split(percentage=.33)
        apl_apply_items.operator(
            "maplus.quickalignplanesobject",
            text="Object"
        )
        apl_mesh_apply_items = apl_apply_items.row(align=True)
        apl_mesh_apply_items.operator(
            "maplus.quickalignplanesmeshselected",
            text="Mesh Piece"
        )
        apl_mesh_apply_items.operator(
            "maplus.quickalignplaneswholemesh",
            text="Whole Mesh"
        )


class QuickAxisRotateGUI(bpy.types.Panel):
    bl_idname = "quick_axis_rotate_gui"
    bl_label = "Quick Axis Rotate"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        axr_top = layout.row()
        axr_gui = layout.box()
        axr_top.label(
            "Axis Rotate",
            icon="FORCE_MAGNETIC"
        )
        axr_grab_col = axr_gui.column()
        axr_grab_col.prop(
            addon_data,
            'quick_axis_rotate_auto_grab_src',
            'Auto Grab Axis from Selected Vertices'
        )

        axr_src_geom_top = axr_grab_col.row(align=True)
        if not addon_data.quick_axis_rotate_auto_grab_src:
            if not addon_data.quick_axr_show_src_geom:
                axr_src_geom_top.operator(
                        "maplus.showhidequickaxrsrcgeom",
                        icon='TRIA_RIGHT',
                        text="",
                        emboss=False
                )
                preserve_button_roundedge = axr_src_geom_top.row()
                preserve_button_roundedge.operator(
                        "maplus.quickaxisrotategrabsrc",
                        icon='MAN_TRANS',
                        text="Grab Axis"
                )
                preserve_button_roundedge.operator(
                    "maplus.quickaxrgrabnormalsrc",
                    icon='LAMP_HEMI',
                    text=""
                )
            else:
                axr_src_geom_top.operator(
                        "maplus.showhidequickaxrsrcgeom",
                        icon='TRIA_DOWN',
                        text="",
                        emboss=False
                )
                axr_src_geom_top.label("Source Coordinates", icon="MAN_TRANS")

                axr_src_geom_editor = axr_grab_col.box()
                ln_grab_all = axr_src_geom_editor.row(align=True)
                ln_grab_all.operator(
                    "maplus.quickaxisrotategrabsrcloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                ln_grab_all.operator(
                    "maplus.quickaxisrotategrabsrc",
                    icon='WORLD',
                    text="Grab All Global"
                )

                special_grabs = axr_src_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.quickaxrgrabnormalsrc",
                    icon='LAMP_HEMI',
                    text="Grab Normal"
                )
                special_grabs_extra = axr_src_geom_editor.row(align=True)
                special_grabs_extra.operator(
                    "maplus.copyfromaxrsrc",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs_extra.operator(
                    "maplus.pasteintoaxrsrc",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = axr_src_geom_editor.row()
                modifier_header.label("Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = axr_src_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_axis_rotate_src),
                    'ln_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_axis_rotate_src),
                    'ln_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_axis_rotate_src),
                    'ln_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=axr_src_geom_editor,
                    coordvec_label="Start:",
                    op_id_cursor_grab=(
                        "maplus.quickaxrsrcgrablinestartfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickaxrgrabavgsrclinestart"
                    ),
                    op_id_local_grab=(
                        "maplus.quickaxrsrcgrablinestartfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickaxrsrcgrablinestartfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_axis_rotate_src,
                    coord_attribute="line_start",
                    op_id_cursor_send=(
                        "maplus.quickaxrsrcsendlinestarttocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickaxrsrcswaplinepoints",
                        "End"
                    )
                )

                layout_coordvec(
                    parent_layout=axr_src_geom_editor,
                    coordvec_label="End:",
                    op_id_cursor_grab=(
                        "maplus.quickaxrsrcgrablineendfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickaxrgrabavgsrclineend"
                    ),
                    op_id_local_grab=(
                        "maplus.quickaxrsrcgrablineendfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickaxrsrcgrablineendfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_axis_rotate_src,
                    coord_attribute="line_end",
                    op_id_cursor_send=(
                        "maplus.quickaxrsrcsendlineendtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickaxrsrcswaplinepoints",
                        "Start"
                    )
                )

        if addon_data.quick_axr_show_src_geom:
            axr_grab_col.separator()

        axr_gui.label("Operator settings:", icon="SCRIPTWIN")
        axr_mods = axr_gui.box()
        axr_mods_row1 = axr_mods.row()
        axr_mods_row1.prop(
            addon_data.quick_axis_rotate_transf,
            'axr_amount',
            'Amount'
        )
        axr_apply_header = axr_gui.row()
        axr_apply_header.label("Apply to:")
        axr_apply_header.prop(
            addon_data,
            'use_experimental',
            'Enable Experimental Mesh Ops.'
        )
        axr_apply_items = axr_gui.split(percentage=.33)
        axr_apply_items.operator(
            "maplus.quickaxisrotateobject",
            text="Object"
        )
        axr_mesh_apply_items = axr_apply_items.row(align=True)
        axr_mesh_apply_items.operator(
            "maplus.quickaxisrotatemeshselected",
            text="Mesh Piece"
        )
        axr_mesh_apply_items.operator(
            "maplus.quickaxisrotatewholemesh",
            text="Whole Mesh"
        )


class QuickDirectionalSlideGUI(bpy.types.Panel):
    bl_idname = "quick_directional_slide_gui"
    bl_label = "Quick Directional Slide"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        ds_top = layout.row()
        ds_gui = layout.box()
        ds_top.label(
            "Directional Slide",
            icon="CURVE_PATH"
        )
        ds_grab_col = ds_gui.column()
        ds_grab_col.prop(
            addon_data,
            'quick_directional_slide_auto_grab_src',
            'Auto Grab Source from Selected Vertices'
        )

        ds_src_geom_top = ds_grab_col.row(align=True)
        if not addon_data.quick_directional_slide_auto_grab_src:
            if not addon_data.quick_ds_show_src_geom:
                ds_src_geom_top.operator(
                        "maplus.showhidequickdssrcgeom",
                        icon='TRIA_RIGHT',
                        text="",
                        emboss=False
                )
                preserve_button_roundedge = ds_src_geom_top.row()
                preserve_button_roundedge.operator(
                        "maplus.quickdirectionalslidegrabsrc",
                        icon='MAN_TRANS',
                        text="Grab Source"
                )
                preserve_button_roundedge.operator(
                    "maplus.quickdsgrabnormalsrc",
                    icon='LAMP_HEMI',
                    text=""
                )

            else:
                ds_src_geom_top.operator(
                        "maplus.showhidequickdssrcgeom",
                        icon='TRIA_DOWN',
                        text="",
                        emboss=False
                )
                ds_src_geom_top.label("Source Coordinates", icon="MAN_TRANS")

                ds_src_geom_editor = ds_grab_col.box()
                ln_grab_all = ds_src_geom_editor.row(align=True)
                ln_grab_all.operator(
                    "maplus.quickdirectionalslidegrabsrcloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                ln_grab_all.operator(
                    "maplus.quickdirectionalslidegrabsrc",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = ds_src_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.quickdsgrabnormalsrc",
                    icon='LAMP_HEMI',
                    text="Grab Normal"
                )
                special_grabs_extra = ds_src_geom_editor.row(align=True)
                special_grabs_extra.operator(
                    "maplus.copyfromdssrc",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs_extra.operator(
                    "maplus.pasteintodssrc",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = ds_src_geom_editor.row()
                modifier_header.label("Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = ds_src_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_directional_slide_src),
                    'ln_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_directional_slide_src),
                    'ln_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_directional_slide_src),
                    'ln_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=ds_src_geom_editor,
                    coordvec_label="Start:",
                    op_id_cursor_grab=(
                        "maplus.quickdssrcgrablinestartfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickdsgrabavgsrclinestart"
                    ),
                    op_id_local_grab=(
                        "maplus.quickdssrcgrablinestartfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickdssrcgrablinestartfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_directional_slide_src,
                    coord_attribute="line_start",
                    op_id_cursor_send=(
                        "maplus.quickdssrcsendlinestarttocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickdssrcswaplinepoints",
                        "End"
                    )
                )

                layout_coordvec(
                    parent_layout=ds_src_geom_editor,
                    coordvec_label="End:",
                    op_id_cursor_grab=(
                        "maplus.quickdssrcgrablineendfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quickdsgrabavgsrclineend"
                    ),
                    op_id_local_grab=(
                        "maplus.quickdssrcgrablineendfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quickdssrcgrablineendfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_directional_slide_src,
                    coord_attribute="line_end",
                    op_id_cursor_send=(
                        "maplus.quickdssrcsendlineendtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quickdssrcswaplinepoints",
                        "Start"
                    )
                )

        if addon_data.quick_ds_show_src_geom:
            ds_grab_col.separator()

        ds_gui.label("Operator settings:", icon="SCRIPTWIN")
        ds_mods = ds_gui.box()
        ds_box_row1 = ds_mods.row()
        ds_box_row1.prop(
            addon_data.quick_directional_slide_transf,
            'ds_make_unit_vec',
            'Set Length to 1'
        )
        ds_box_row1.prop(
            addon_data.quick_directional_slide_transf,
            'ds_flip_direction',
            'Flip Direction'
        )
        ds_box_row2 = ds_mods.row()
        ds_box_row2.prop(
            addon_data.quick_directional_slide_transf,
            'ds_multiplier',
            'Multiplier'
        )
        ds_apply_header = ds_gui.row()
        ds_apply_header.label("Apply to:")
        ds_apply_header.prop(
            addon_data,
            'use_experimental',
            'Enable Experimental Mesh Ops.'
        )
        ds_apply_items = ds_gui.split(percentage=.33)
        ds_apply_items.operator(
            "maplus.quickdirectionalslideobject",
            text="Object"
        )
        ds_mesh_apply_items = ds_apply_items.row(align=True)
        ds_mesh_apply_items.operator(
            "maplus.quickdirectionalslidemeshselected",
            text="Mesh Piece"
        )
        ds_mesh_apply_items.operator(
            "maplus.quickdirectionalslidewholemesh",
            text="Whole Mesh"
        )


class QuickSMEGUI(bpy.types.Panel):
    bl_idname = "quick_sme_gui"
    bl_label = "Quick Scale Match Edge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        sme_top = layout.row()
        sme_gui = layout.box()
        sme_top.label(
            "Match Edge Scale",
            icon="FULLSCREEN_ENTER"
        )
        sme_grab_col = sme_gui.column()
        sme_grab_col.prop(
            addon_data,
            'quick_scale_match_edge_auto_grab_src',
            'Auto Grab Source from Selected Vertices'
        )

        sme_src_geom_top = sme_grab_col.row(align=True)
        if not addon_data.quick_scale_match_edge_auto_grab_src:
            if not addon_data.quick_sme_show_src_geom:
                sme_src_geom_top.operator(
                        "maplus.showhidequicksmesrcgeom",
                        icon='TRIA_RIGHT',
                        text="",
                        emboss=False
                )
                preserve_button_roundedge = sme_src_geom_top.row()
                preserve_button_roundedge.operator(
                        "maplus.quickscalematchedgegrabsrc",
                        icon='MAN_TRANS',
                        text="Grab Source"
                )
            else:
                sme_src_geom_top.operator(
                        "maplus.showhidequicksmesrcgeom",
                        icon='TRIA_DOWN',
                        text="",
                        emboss=False
                )
                sme_src_geom_top.label("Source Coordinates", icon="MAN_TRANS")

                sme_src_geom_editor = sme_grab_col.box()
                ln_grab_all = sme_src_geom_editor.row(align=True)
                ln_grab_all.operator(
                    "maplus.quickscalematchedgegrabsrcloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                ln_grab_all.operator(
                    "maplus.quickscalematchedgegrabsrc",
                    icon='WORLD',
                    text="Grab All Global"
                )

                special_grabs = sme_src_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.quicksmegrabnormalsrc",
                    icon='LAMP_HEMI',
                    text="Grab Normal"
                )
                special_grabs_extra = sme_src_geom_editor.row(align=True)
                special_grabs_extra.operator(
                    "maplus.copyfromsmesrc",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs_extra.operator(
                    "maplus.pasteintosmesrc",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = sme_src_geom_editor.row()
                modifier_header.label("Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = sme_src_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_scale_match_edge_src),
                    'ln_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_scale_match_edge_src),
                    'ln_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_scale_match_edge_src),
                    'ln_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=sme_src_geom_editor,
                    coordvec_label="Start:",
                    op_id_cursor_grab=(
                        "maplus.quicksmesrcgrablinestartfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quicksmegrabavgsrclinestart"
                    ),
                    op_id_local_grab=(
                        "maplus.quicksmesrcgrablinestartfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quicksmesrcgrablinestartfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_scale_match_edge_src,
                    coord_attribute="line_start",
                    op_id_cursor_send=(
                        "maplus.quicksmesrcsendlinestarttocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quicksmesrcswaplinepoints",
                        "End"
                    )
                )

                layout_coordvec(
                    parent_layout=sme_src_geom_editor,
                    coordvec_label="End:",
                    op_id_cursor_grab=(
                        "maplus.quicksmesrcgrablineendfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.quicksmegrabavgsrclineend"
                    ),
                    op_id_local_grab=(
                        "maplus.quicksmesrcgrablineendfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.quicksmesrcgrablineendfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_scale_match_edge_src,
                    coord_attribute="line_end",
                    op_id_cursor_send=(
                        "maplus.quicksmesrcsendlineendtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.quicksmesrcswaplinepoints",
                        "Start"
                    )
                )

        if addon_data.quick_sme_show_src_geom:
            sme_grab_col.separator()

        sme_dest_geom_top = sme_grab_col.row(align=True)
        if not addon_data.quick_sme_show_dest_geom:
            sme_dest_geom_top.operator(
                    "maplus.showhidequicksmedestgeom",
                    icon='TRIA_RIGHT',
                    text="",
                    emboss=False
            )
            preserve_button_roundedge = sme_dest_geom_top.row()
            preserve_button_roundedge.operator(
                    "maplus.quickscalematchedgegrabdest",
                    icon='MAN_TRANS',
                    text="Grab Destination"
            )
        else:
            sme_dest_geom_top.operator(
                    "maplus.showhidequicksmedestgeom",
                    icon='TRIA_DOWN',
                    text="",
                    emboss=False
            )
            sme_dest_geom_top.label("Destination Coordinates", icon="MAN_TRANS")

            sme_dest_geom_editor = sme_grab_col.box()
            ln_grab_all = sme_dest_geom_editor.row(align=True)
            ln_grab_all.operator(
                "maplus.quickscalematchedgegrabdestloc",
                icon='VERTEXSEL',
                text="Grab All Local"
            )
            ln_grab_all.operator(
                "maplus.quickscalematchedgegrabdest",
                icon='WORLD',
                text="Grab All Global"
            )
            special_grabs = sme_dest_geom_editor.row(align=True)
            special_grabs.operator(
                "maplus.quicksmegrabnormaldest",
                icon='LAMP_HEMI',
                text="Grab Normal"
            )
            special_grabs_extra = sme_dest_geom_editor.row(align=True)
            special_grabs_extra.operator(
                "maplus.copyfromsmedest",
                icon='COPYDOWN',
                text="Copy (To Clipboard)"
            )
            special_grabs_extra.operator(
                "maplus.pasteintosmedest",
                icon='PASTEDOWN',
                text="Paste (From Clipboard)"
            )

            modifier_header = sme_dest_geom_editor.row()
            modifier_header.label("Line Modifiers:")
            apply_mods = modifier_header.row()
            apply_mods.alignment = 'RIGHT'

            item_mods_box = sme_dest_geom_editor.box()
            mods_row_1 = item_mods_box.row()
            mods_row_1.prop(
                bpy.types.AnyType(addon_data.quick_scale_match_edge_dest),
                'ln_make_unit_vec',
                "Set Length Equal to One"
            )
            mods_row_1.prop(
                bpy.types.AnyType(addon_data.quick_scale_match_edge_dest),
                'ln_flip_direction',
                "Flip Direction"
            )
            mods_row_2 = item_mods_box.row()
            mods_row_2.prop(
                bpy.types.AnyType(addon_data.quick_scale_match_edge_dest),
                'ln_multiplier',
                "Multiplier"
            )

            layout_coordvec(
                parent_layout=sme_dest_geom_editor,
                coordvec_label="Start:",
                op_id_cursor_grab=(
                    "maplus.quicksmedestgrablinestartfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quicksmegrabavgdestlinestart"
                ),
                op_id_local_grab=(
                    "maplus.quicksmedestgrablinestartfromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quicksmedestgrablinestartfromactiveglobal"
                ),
                coord_container=addon_data.quick_scale_match_edge_dest,
                coord_attribute="line_start",
                op_id_cursor_send=(
                    "maplus.quicksmedestsendlinestarttocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quicksmedestswaplinepoints",
                    "End"
                )
            )

            layout_coordvec(
                parent_layout=sme_dest_geom_editor,
                coordvec_label="End:",
                op_id_cursor_grab=(
                    "maplus.quicksmedestgrablineendfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quicksmegrabavgdestlineend"
                ),
                op_id_local_grab=(
                    "maplus.quicksmedestgrablineendfromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quicksmedestgrablineendfromactiveglobal"
                ),
                coord_container=addon_data.quick_scale_match_edge_dest,
                coord_attribute="line_end",
                op_id_cursor_send=(
                    "maplus.quicksmedestsendlineendtocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quicksmedestswaplinepoints",
                    "Start"
                )
            )

        numeric_gui = sme_gui.column()
        numeric_gui.prop(
            addon_data,
            'quick_sme_numeric_mode',
            'Numeric Input Mode'
        )
        numeric_settings = numeric_gui.box()
        numeric_grabs = numeric_settings.row()
        numeric_grabs.prop(
            addon_data,
            'quick_sme_numeric_auto',
            'Auto Grab Target'
        )
        if not addon_data.quick_sme_numeric_auto:
            numeric_grabs.operator(
                "maplus.grabsmenumeric"
            )
        numeric_settings.prop(
            addon_data,
            'quick_sme_numeric_length',
            'Target Length'
        )

        # Disable relevant items depending on whether numeric mode
        # is enabled or not
        if addon_data.quick_sme_numeric_mode:
            sme_grab_col.enabled = False
        else:
            numeric_settings.enabled = False

        sme_apply_header = sme_gui.row()
        sme_apply_header.label("Apply to:")
        sme_apply_header.prop(
            addon_data,
            'use_experimental',
            'Enable Experimental Mesh Ops.'
        )
        sme_apply_items = sme_gui.split(percentage=.33)
        sme_apply_items.operator(
            "maplus.quickscalematchedgeobject",
            text="Object"
        )
        sme_mesh_apply_items = sme_apply_items.row(align=True)
        sme_mesh_apply_items.operator(
            "maplus.quickscalematchedgemeshselected",
            text="Mesh Piece"
        )
        sme_mesh_apply_items.operator(
            "maplus.quickscalematchedgewholemesh",
            text="Whole Mesh"
        )


class QuickAlignObjectsGUI(bpy.types.Panel):
    bl_idname = "quick_align_objects_gui"
    bl_label = "Quick Align Objects"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
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


class CalculateAndComposeGUI(bpy.types.Panel):
    bl_idname = "calculate_and_compose_gui"
    bl_label = "Calculate and Compose"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data

        calc_gui = layout.column()

        slot1_geom_top = calc_gui.row(align=True)
        if not addon_data.quick_calc_show_slot1_geom:
            slot1_geom_top.operator(
                "maplus.showhidequickcalcslot1geom",
                icon='TRIA_RIGHT',
                text="",
                emboss=False
            )
            preserve_button_roundedge = slot1_geom_top.row()
            preserve_button_roundedge.operator(
                "maplus.graballslot1",
                icon='SOLO_ON',
                text="S. Grab Slot 1"
            )

        else:
            slot1_geom_top.operator(
                "maplus.showhidequickcalcslot1geom",
                icon='TRIA_DOWN',
                text="",
                emboss=False
            )
            slot1_geom_top.label("Slot 1 Coordinates")
            slot1_geom_editor = calc_gui.box()
            types_row = slot1_geom_editor.row()
            types_row.label("Item type:")
            types_row.prop(
                bpy.types.AnyType(addon_data.internal_storage_slot_1),
                'kind',
                ""
            )

            if addon_data.internal_storage_slot_1.kind == 'POINT':
                pt_grab_all = slot1_geom_editor.row(align=True)
                pt_grab_all.operator(
                    "maplus.grabpointslot1loc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                pt_grab_all.operator(
                    "maplus.grabpointslot1",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = slot1_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromslot1",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintoslot1",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = slot1_geom_editor.row()
                modifier_header.label("Point Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = slot1_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'pt_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'pt_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'pt_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=slot1_geom_editor,
                    coordvec_label="Pt. Origin:",
                    op_id_cursor_grab=(
                        "maplus.slot1grabpointfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot1pointgrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grabpointslot1loc"
                    ),
                    op_id_global_grab=(
                        "maplus.grabpointslot1"
                    ),
                    coord_container=addon_data.internal_storage_slot_1,
                    coord_attribute="point",
                    op_id_cursor_send=(
                        "maplus.slot1sendpointtocursor"
                    )
                )

            elif addon_data.internal_storage_slot_1.kind == 'LINE':
                ln_grab_all = slot1_geom_editor.row(align=True)
                ln_grab_all.operator(
                    "maplus.grablineslot1loc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                ln_grab_all.operator(
                    "maplus.grablineslot1",
                    icon='WORLD',
                    text="Grab All Global"
                )

                special_grabs = slot1_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.slot1grabnormal",
                    icon='LAMP_HEMI',
                    text="Grab Normal"
                )
                special_grabs_extra = slot1_geom_editor.row(align=True)
                special_grabs_extra.operator(
                    "maplus.copyfromslot1",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs_extra.operator(
                    "maplus.pasteintoslot1",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = slot1_geom_editor.row()
                modifier_header.label("Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = slot1_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'ln_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'ln_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'ln_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=slot1_geom_editor,
                    coordvec_label="Start:",
                    op_id_cursor_grab=(
                        "maplus.slot1grablinestartfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot1grabavglinestart"
                    ),
                    op_id_local_grab=(
                        "maplus.slot1grablinestartfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot1grablinestartfromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_1,
                    coord_attribute="line_start",
                    op_id_cursor_send=(
                        "maplus.slot1sendlinestarttocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot1swaplinepoints",
                        "End"
                    )
                )

                layout_coordvec(
                    parent_layout=slot1_geom_editor,
                    coordvec_label="End:",
                    op_id_cursor_grab=(
                        "maplus.slot1grablineendfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot1grabavglineend"
                    ),
                    op_id_local_grab=(
                        "maplus.slot1grablineendfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot1grablineendfromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_1,
                    coord_attribute="line_end",
                    op_id_cursor_send=(
                        "maplus.slot1sendlineendtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot1swaplinepoints",
                        "Start"
                    )
                )

            elif addon_data.internal_storage_slot_1.kind == 'PLANE':
                plane_grab_all = slot1_geom_editor.row(align=True)
                plane_grab_all.operator(
                    "maplus.grabplaneslot1loc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                plane_grab_all.operator(
                    "maplus.grabplaneslot1",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = slot1_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromslot1",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintoslot1",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                layout_coordvec(
                    parent_layout=slot1_geom_editor,
                    coordvec_label="Pt. A:",
                    op_id_cursor_grab=(
                        "maplus.slot1grabplaneafromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot1grabavgplanea"
                    ),
                    op_id_local_grab=(
                        "maplus.slot1grabplaneafromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot1grabplaneafromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_1,
                    coord_attribute="plane_pt_a",
                    op_id_cursor_send=(
                        "maplus.slot1sendplaneatocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot1swapplaneaplaneb",
                        "B"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.slot1swapplaneaplanec",
                        "C"
                    )
                )

                layout_coordvec(
                    parent_layout=slot1_geom_editor,
                    coordvec_label="Pt. B (Pivot):",
                    op_id_cursor_grab=(
                        "maplus.slot1grabplanebfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot1grabavgplaneb"
                    ),
                    op_id_local_grab=(
                        "maplus.slot1grabplanebfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot1grabplanebfromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_1,
                    coord_attribute="plane_pt_b",
                    op_id_cursor_send=(
                        "maplus.slot1sendplanebtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot1swapplaneaplaneb",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.slot1swapplanebplanec",
                        "C"
                    )
                )

                layout_coordvec(
                    parent_layout=slot1_geom_editor,
                    coordvec_label="Pt. C:",
                    op_id_cursor_grab=(
                        "maplus.slot1grabplanecfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot1grabavgplanec"
                    ),
                    op_id_local_grab=(
                        "maplus.slot1grabplanecfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot1grabplanecfromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_1,
                    coord_attribute="plane_pt_c",
                    op_id_cursor_send=(
                        "maplus.slot1sendplanectocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot1swapplaneaplanec",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.slot1swapplanebplanec",
                        "B"
                    )
                )

        if addon_data.quick_calc_show_slot1_geom:
                calc_gui.separator()

        slot2_geom_top = calc_gui.row(align=True)
        if not addon_data.quick_calc_show_slot2_geom:
            slot2_geom_top.operator(
                "maplus.showhidequickcalcslot2geom",
                icon='TRIA_RIGHT',
                text="",
                emboss=False
            )
            preserve_button_roundedge = slot2_geom_top.row()
            preserve_button_roundedge.operator(
                "maplus.graballslot2",
                icon='SOLO_ON',
                text="S. Grab Slot 2"
            )

        else:
            slot2_geom_top.operator(
                "maplus.showhidequickcalcslot2geom",
                icon='TRIA_DOWN',
                text="",
                emboss=False
            )
            slot2_geom_top.label("Slot 2 Coordinates")
            slot2_geom_editor = calc_gui.box()
            types_row = slot2_geom_editor.row()
            types_row.label("Item type:")
            types_row.prop(
                bpy.types.AnyType(addon_data.internal_storage_slot_2),
                'kind',
                ""
            )

            if addon_data.internal_storage_slot_2.kind == 'POINT':
                pt_grab_all = slot2_geom_editor.row(align=True)
                pt_grab_all.operator(
                    "maplus.grabpointslot2loc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                pt_grab_all.operator(
                    "maplus.grabpointslot2",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = slot2_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromslot2",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintoslot2",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = slot2_geom_editor.row()
                modifier_header.label("Point Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                item_mods_box = slot2_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'pt_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'pt_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'pt_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=slot2_geom_editor,
                    coordvec_label="Pt. Origin:",
                    op_id_cursor_grab=(
                        "maplus.slot2grabpointfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot2pointgrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grabpointslot2loc"
                    ),
                    op_id_global_grab=(
                        "maplus.grabpointslot2"
                    ),
                    coord_container=addon_data.internal_storage_slot_2,
                    coord_attribute="point",
                    op_id_cursor_send=(
                        "maplus.slot2sendpointtocursor"
                    )
                )

            elif addon_data.internal_storage_slot_2.kind == 'LINE':
                ln_grab_all = slot2_geom_editor.row(align=True)
                ln_grab_all.operator(
                    "maplus.grablineslot2loc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                ln_grab_all.operator(
                    "maplus.grablineslot2",
                    icon='WORLD',
                    text="Grab All Global"
                )

                special_grabs = slot2_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.slot2grabnormal",
                    icon='LAMP_HEMI',
                    text="Grab Normal"
                )
                special_grabs_extra = slot2_geom_editor.row(align=True)
                special_grabs_extra.operator(
                    "maplus.copyfromslot2",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs_extra.operator(
                    "maplus.pasteintoslot2",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = slot2_geom_editor.row()
                modifier_header.label("Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                item_mods_box = slot2_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'ln_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'ln_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'ln_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=slot2_geom_editor,
                    coordvec_label="Start:",
                    op_id_cursor_grab=(
                        "maplus.slot2grablinestartfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot2grabavglinestart"
                    ),
                    op_id_local_grab=(
                        "maplus.slot2grablinestartfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot2grablinestartfromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_2,
                    coord_attribute="line_start",
                    op_id_cursor_send=(
                        "maplus.slot2sendlinestarttocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot2swaplinepoints",
                        "End"
                    )
                )

                layout_coordvec(
                    parent_layout=slot2_geom_editor,
                    coordvec_label="End:",
                    op_id_cursor_grab=(
                        "maplus.slot2grablineendfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot2grabavglineend"
                    ),
                    op_id_local_grab=(
                        "maplus.slot2grablineendfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot2grablineendfromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_2,
                    coord_attribute="line_end",
                    op_id_cursor_send=(
                        "maplus.slot2sendlineendtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot2swaplinepoints",
                        "Start"
                    )
                )

            elif addon_data.internal_storage_slot_2.kind == 'PLANE':
                plane_grab_all = slot2_geom_editor.row(align=True)
                plane_grab_all.operator(
                    "maplus.grabplaneslot2loc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                plane_grab_all.operator(
                    "maplus.grabplaneslot2",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = slot2_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromslot2",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintoslot2",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                layout_coordvec(
                    parent_layout=slot2_geom_editor,
                    coordvec_label="Pt. A:",
                    op_id_cursor_grab=(
                        "maplus.slot2grabplaneafromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot2grabavgplanea"
                    ),
                    op_id_local_grab=(
                        "maplus.slot2grabplaneafromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot2grabplaneafromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_2,
                    coord_attribute="plane_pt_a",
                    op_id_cursor_send=(
                        "maplus.slot2sendplaneatocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot2swapplaneaplaneb",
                        "B"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.slot2swapplaneaplanec",
                        "C"
                    )
                )

                layout_coordvec(
                    parent_layout=slot2_geom_editor,
                    coordvec_label="Pt. B (Pivot):",
                    op_id_cursor_grab=(
                        "maplus.slot2grabplanebfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot2grabavgplaneb"
                    ),
                    op_id_local_grab=(
                        "maplus.slot2grabplanebfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot2grabplanebfromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_2,
                    coord_attribute="plane_pt_b",
                    op_id_cursor_send=(
                        "maplus.slot2sendplanebtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot2swapplaneaplaneb",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.slot2swapplanebplanec",
                        "C"
                    )
                )

                layout_coordvec(
                    parent_layout=slot2_geom_editor,
                    coordvec_label="Pt. C:",
                    op_id_cursor_grab=(
                        "maplus.slot2grabplanecfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.slot2grabavgplanec"
                    ),
                    op_id_local_grab=(
                        "maplus.slot2grabplanecfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.slot2grabplanecfromactiveglobal"
                    ),
                    coord_container=addon_data.internal_storage_slot_2,
                    coord_attribute="plane_pt_c",
                    op_id_cursor_send=(
                        "maplus.slot2sendplanectocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.slot2swapplaneaplanec",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.slot2swapplanebplanec",
                        "B"
                    )
                )

        if addon_data.quick_calc_show_slot2_geom:
                calc_gui.separator()

        calcs_and_results_header = calc_gui.row()
        calcs_and_results_header.label(
            "Result:"
        )
        clipboard_row_right = calcs_and_results_header.row()
        clipboard_row_right.alignment = 'RIGHT'
        clipboard_row_right.prop(
            bpy.types.AnyType(maplus_data_ptr),
            'calc_result_to_clipboard',
            "Copy to Clipboard"
        )
        calc_gui.prop(
            bpy.types.AnyType(bpy.types.AnyType(addon_data)),
            'quick_calc_result_numeric',
            ""
        )

        result_geom_top = calc_gui.row(align=True)
        if not addon_data.quick_calc_show_result_geom:
            result_geom_top.operator(
                "maplus.showhidequickcalcresultgeom",
                icon='TRIA_RIGHT',
                text="",
                emboss=False
            )
            preserve_button_roundedge = result_geom_top.row()
            preserve_button_roundedge.operator(
                "maplus.graballcalcresult",
                icon='SOLO_ON',
                text="S. Grab Result"
            )

        else:
            result_geom_top.operator(
                "maplus.showhidequickcalcresultgeom",
                icon='TRIA_DOWN',
                text="",
                emboss=False
            )
            result_geom_top.label("Calc. Result Coordinates")
            calcresult_geom_editor = calc_gui.box()
            types_row = calcresult_geom_editor.row()
            types_row.label("Item type:")
            types_row.prop(
                bpy.types.AnyType(addon_data.quick_calc_result_item),
                'kind',
                ""
            )

            if addon_data.quick_calc_result_item.kind == 'POINT':
                pt_grab_all = calcresult_geom_editor.row(align=True)
                pt_grab_all.operator(
                    "maplus.grabpointcalcresultloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                pt_grab_all.operator(
                    "maplus.grabpointcalcresult",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = calcresult_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromcalcresult",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintocalcresult",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = calcresult_geom_editor.row()
                modifier_header.label("Point Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                item_mods_box = calcresult_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'pt_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'pt_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'pt_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=calcresult_geom_editor,
                    coordvec_label="Pt. Origin:",
                    op_id_cursor_grab=(
                        "maplus.calcresultgrabpointfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.calcresultpointgrabavg"
                    ),
                    op_id_local_grab=(
                        "maplus.grabpointcalcresultloc"
                    ),
                    op_id_global_grab=(
                        "maplus.grabpointcalcresult"
                    ),
                    coord_container=addon_data.quick_calc_result_item,
                    coord_attribute="point",
                    op_id_cursor_send=(
                        "maplus.calcresultsendpointtocursor"
                    )
                )

            elif addon_data.quick_calc_result_item.kind == 'LINE':
                ln_grab_all = calcresult_geom_editor.row(align=True)
                ln_grab_all.operator(
                    "maplus.grablinecalcresultloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                ln_grab_all.operator(
                    "maplus.grablinecalcresult",
                    icon='WORLD',
                    text="Grab All Global"
                )

                special_grabs = calcresult_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.calcresultgrabnormal",
                    icon='LAMP_HEMI',
                    text="Grab Normal"
                )
                special_grabs_extra = calcresult_geom_editor.row(align=True)
                special_grabs_extra.operator(
                    "maplus.copyfromcalcresult",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs_extra.operator(
                    "maplus.pasteintocalcresult",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                modifier_header = calcresult_geom_editor.row()
                modifier_header.label("Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                item_mods_box = calcresult_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'ln_make_unit_vec',
                    "Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'ln_flip_direction',
                    "Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'ln_multiplier',
                    "Multiplier"
                )

                layout_coordvec(
                    parent_layout=calcresult_geom_editor,
                    coordvec_label="Start:",
                    op_id_cursor_grab=(
                        "maplus.calcresultgrablinestartfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.calcresultgrabavglinestart"
                    ),
                    op_id_local_grab=(
                        "maplus.calcresultgrablinestartfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.calcresultgrablinestartfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_calc_result_item,
                    coord_attribute="line_start",
                    op_id_cursor_send=(
                        "maplus.calcresultsendlinestarttocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.calcresultswaplinepoints",
                        "End"
                    )
                )

                layout_coordvec(
                    parent_layout=calcresult_geom_editor,
                    coordvec_label="End:",
                    op_id_cursor_grab=(
                        "maplus.calcresultgrablineendfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.calcresultgrabavglineend"
                    ),
                    op_id_local_grab=(
                        "maplus.calcresultgrablineendfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.calcresultgrablineendfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_calc_result_item,
                    coord_attribute="line_end",
                    op_id_cursor_send=(
                        "maplus.calcresultsendlineendtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.calcresultswaplinepoints",
                        "Start"
                    )
                )

            elif addon_data.quick_calc_result_item.kind == 'PLANE':
                plane_grab_all = calcresult_geom_editor.row(align=True)
                plane_grab_all.operator(
                    "maplus.grabplanecalcresultloc",
                    icon='VERTEXSEL',
                    text="Grab All Local"
                )
                plane_grab_all.operator(
                    "maplus.grabplanecalcresult",
                    icon='WORLD',
                    text="Grab All Global"
                )
                special_grabs = calcresult_geom_editor.row(align=True)
                special_grabs.operator(
                    "maplus.copyfromcalcresult",
                    icon='COPYDOWN',
                    text="Copy (To Clipboard)"
                )
                special_grabs.operator(
                    "maplus.pasteintocalcresult",
                    icon='PASTEDOWN',
                    text="Paste (From Clipboard)"
                )

                layout_coordvec(
                    parent_layout=calcresult_geom_editor,
                    coordvec_label="Pt. A:",
                    op_id_cursor_grab=(
                        "maplus.calcresultgrabplaneafromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.calcresultgrabavgplanea"
                    ),
                    op_id_local_grab=(
                        "maplus.calcresultgrabplaneafromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.calcresultgrabplaneafromactiveglobal"
                    ),
                    coord_container=addon_data.quick_calc_result_item,
                    coord_attribute="plane_pt_a",
                    op_id_cursor_send=(
                        "maplus.calcresultsendplaneatocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.calcresultswapplaneaplaneb",
                        "B"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.calcresultswapplaneaplanec",
                        "C"
                    )
                )

                layout_coordvec(
                    parent_layout=calcresult_geom_editor,
                    coordvec_label="Pt. B (Pivot):",
                    op_id_cursor_grab=(
                        "maplus.calcresultgrabplanebfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.calcresultgrabavgplaneb"
                    ),
                    op_id_local_grab=(
                        "maplus.calcresultgrabplanebfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.calcresultgrabplanebfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_calc_result_item,
                    coord_attribute="plane_pt_b",
                    op_id_cursor_send=(
                        "maplus.calcresultsendplanebtocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.calcresultswapplaneaplaneb",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.calcresultswapplanebplanec",
                        "C"
                    )
                )

                layout_coordvec(
                    parent_layout=calcresult_geom_editor,
                    coordvec_label="Pt. C:",
                    op_id_cursor_grab=(
                        "maplus.calcresultgrabplanecfromcursor"
                    ),
                    op_id_avg_grab=(
                        "maplus.calcresultgrabavgplanec"
                    ),
                    op_id_local_grab=(
                        "maplus.calcresultgrabplanecfromactivelocal"
                    ),
                    op_id_global_grab=(
                        "maplus.calcresultgrabplanecfromactiveglobal"
                    ),
                    coord_container=addon_data.quick_calc_result_item,
                    coord_attribute="plane_pt_c",
                    op_id_cursor_send=(
                        "maplus.calcresultsendplanectocursor"
                    ),
                    op_id_text_tuple_swap_first=(
                        "maplus.calcresultswapplaneaplanec",
                        "A"
                    ),
                    op_id_text_tuple_swap_second=(
                        "maplus.calcresultswapplanebplanec",
                        "B"
                    )
                )

        calc_gui.separator()

        ops_header = calc_gui.row()
        ops_header.label("Available Calc.'s:")
        ops_header.prop(
            bpy.types.AnyType(addon_data),
            'quick_calc_check_types',
            "Check/Verify Types"
        )
        calc_gui.operator(
            "maplus.quickcalclinelength",
            text="Line Length"
        )
        calc_gui.operator(
            "maplus.quickcalcrotationaldiff",
            text="Angle of Lines"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinefromorigin",
            icon='MAN_TRANS',
            text="New Line from Origin"
        )
        calc_gui.operator(
            "maplus.quickcomposenormalfromplane",
            icon='MAN_TRANS',
            text="Get Plane Normal (Normalized)"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinefrompoint",
            icon='MAN_TRANS',
            text="New Line from Point"
        )
        calc_gui.operator(
            "maplus.quickcalcdistancebetweenpoints",
            text="Distance Between Points"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlineatpointlocation",
            icon='MAN_TRANS',
            text="New Line at Point"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinefrompoints",
            icon='MAN_TRANS',
            text="New Line from Points"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinevectoraddition",
            icon='MAN_TRANS',
            text="Add Lines"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinevectorsubtraction",
            icon='MAN_TRANS',
            text="Subtract Lines"
        )
        calc_gui.operator(
            "maplus.quickcomposepointintersectinglineplane",
            icon='LAYER_ACTIVE',
            text="Intersect Line/Plane"
        )


def specials_menu_items(self, context):
    self.layout.separator()
    self.layout.label('Add Mesh Align Plus items')
    self.layout.operator('maplus.specialsaddpointfromactiveglobal')
    self.layout.operator('maplus.specialsaddlinefromactiveglobal')
    self.layout.operator('maplus.specialsaddplanefromactiveglobal')
    self.layout.separator()


def register():
    # Make custom classes available inside blender via bpy.types
    bpy.utils.register_module(__name__)

    # Extend the scene class here to include the addon data
    bpy.types.Scene.maplus_data = bpy.props.PointerProperty(type=MAPlusData)

    bpy.types.VIEW3D_MT_object_specials.append(specials_menu_items)
    bpy.types.VIEW3D_MT_edit_mesh_specials.append(specials_menu_items)


def unregister():
    del bpy.types.Scene.maplus_data
    bpy.types.VIEW3D_MT_object_specials.remove(specials_menu_items)
    bpy.types.VIEW3D_MT_edit_mesh_specials.remove(specials_menu_items)

    # Remove custom classes from blender's bpy.types
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
