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
# <pep8-80 compliant>


# Blender requires addons to provide this information.
bl_info = {
    "name": "Mesh Align Plus",
    "description": (
        "Precisely move mesh parts and objects around "
        "based on geometry and measurements from your scene."
    ),
    "author": "Eric Gentry",
    "version": (0, 3, 0),
    "blender": (2, 69, 0),
    "location": (
        "3D View > Tools, and Properties -> Scene -> Mesh Align Plus"
    ),
    "warning": (
        "Operations on objects with non-uniform scaling are "
        "not currently supported."
    ),
    "wiki_url": (
        "https://wiki.blender.org/index.php/Extensions:2.6/Py/"
        "Scripts/Modeling/Mesh_Align_Plus"
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

    quick_align_lines_show = bpy.props.BoolProperty(
        description=(
            "Expand/collapse the align lines operator"
            " in the quick tools panel."
        ),
        default=True
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
            "Copy numeric calculations to clipboard"
        ),
        default=True
    )


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
        except NotEnoughVertsError:
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


class NotEnoughVertsError(Exception):
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
            raise NotEnoughVertsError()
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

        matrix_multiplier = None
        if self.multiply_by_world_matrix:
            matrix_multiplier = bpy.context.active_object.matrix_world
        try:
            vert_data = return_selected_verts(
                bpy.context.active_object,
                len(self.vert_attribs_to_set),
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
        active_item = prims[addon_data.active_list_item]

        bpy.context.scene.cursor_location = getattr(
            active_item,
            self.source_coord_attrib
        )
        return {'FINISHED'}


class GrabPointFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grabpointfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'point'


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


class SendPointToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendpointtocursor"
    bl_label = "Sends Point to Cursor"
    bl_description = "Sends Point Coordinates to the 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'point'


class GrabLineStartFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grablinestartfromcursor"
    bl_label = "Grab Line Start From Cursor"
    bl_description = "Grabs line start coordinates from the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_start'


class GrabLineStartFromActiveLocal(GrabFromGeometryBase):
    bl_idname = "maplus.grablinestartfromactivelocal"
    bl_label = "Grab Local Coordinate for Line Start From Active Point"
    bl_description = (
        "Grabs local coordinates for line start from selected vertex"
        "in edit mode"
    )
    bl_options = {'REGISTER', 'UNDO'}
    target_point_attribute = 'line_start'
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


class SendLineStartToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendlinestarttocursor"
    bl_label = "Sends Line Start to Cursor"
    bl_description = "Sends Line Start Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_start'


class GrabLineEndFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grablineendfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'line_end'


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


class SendLineEndToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendlineendtocursor"
    bl_label = "Sends Line End to Cursor"
    bl_description = "Sends Line End Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'line_end'


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


class GrabPlaneAFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grabplaneafromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_a'


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


class SendPlaneAToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendplaneatocursor"
    bl_label = "Sends Plane Point A to Cursor"
    bl_description = "Sends Plane Point A Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_a'


class GrabPlaneBFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grabplanebfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_b'


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


class SendPlaneBToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendplanebtocursor"
    bl_label = "Sends Plane Point B to Cursor"
    bl_description = "Sends Plane Point B Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_b'


class GrabPlaneCFromCursor(GrabFromCursorBase):
    bl_idname = "maplus.grabplanecfromcursor"
    bl_label = "Grab From Cursor"
    bl_description = "Grabs coordinates from 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    vert_attrib_to_set = 'plane_pt_c'


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


class SendPlaneCToCursor(SendCoordToCursorBase):
    bl_idname = "maplus.sendplanectocursor"
    bl_label = "Sends Plane Point C to Cursor"
    bl_description = "Sends Plane Point C Coordinates to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    source_coord_attrib = 'plane_pt_c'


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
            # modifiers applied. Grab either directly from the scene data
            # (for quick ops), or from the MAPlus primitives
            # CollectionProperty on the scene data (for advanced tools)
            if hasattr(self, "quick_op_target"):
                if addon_data.quick_scale_match_edge_auto_grab_src:
                    vert_attribs_to_set = ('line_start', 'line_end')
                    try:
                        vert_data = return_selected_verts(
                            bpy.context.active_object,
                            len(vert_attribs_to_set),
                            bpy.context.active_object.matrix_world
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
                    except NotEnoughVertsError:
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
                    except NotEnoughVertsError:
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
                    except NotEnoughVertsError:
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
                    except NotEnoughVertsError:
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
                    except NotEnoughVertsError:
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


class CalcLineLength(bpy.types.Operator):
    bl_idname = "maplus.calclinelength"
    bl_label = "Calculate Line Length"
    bl_description = "Calculates the length of the targeted line item"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_item = prims[active_item.single_calc_target]

        if calc_target_item.kind != 'LINE':
            self.report(
                {'ERROR'},
                ('Wrong operand: "Calculate Line Length" can only operate on'
                 ' a line')
            )
            return {'CANCELLED'}

        src_global_data = get_modified_global_coords(
            geometry=calc_target_item,
            kind='LINE'
        )
        src_line = src_global_data[1] - src_global_data[0]
        result = src_line.length
        active_item.single_calc_result = result
        if addon_data.calc_result_to_clipboard:
            bpy.context.window_manager.clipboard = str(result)

        return {'FINISHED'}


class CalcRotationalDiff(bpy.types.Operator):
    bl_idname = "maplus.calcrotationaldiff"
    bl_label = "Angle of Lines"
    bl_description = (
        "Calculates the rotational difference between line items"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_one = prims[active_item.multi_calc_target_one]
        calc_target_two = prims[active_item.multi_calc_target_two]

        if not (calc_target_one.kind == 'LINE' and
                calc_target_two.kind == 'LINE'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Calculate Rotational Difference" can'
                 ' only operate on two lines')
            )
            return {'CANCELLED'}

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
        active_item.multi_calc_result = result
        if addon_data.calc_result_to_clipboard:
            bpy.context.window_manager.clipboard = str(result)

        return {'FINISHED'}


class ComposeNewLineFromOrigin(bpy.types.Operator):
    bl_idname = "maplus.composenewlinefromorigin"
    bl_label = "New Line from Origin"
    bl_description = "Composes a new line item starting at the world origin"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_item = prims[active_item.single_calc_target]

        if calc_target_item.kind != 'LINE':
            self.report(
                {'ERROR'},
                ('Wrong operand: "Compose New Line from Origin" can'
                 ' only operate on a line')
            )
            return {'CANCELLED'}

        start_loc = mathutils.Vector((0, 0, 0))

        src_global_data = get_modified_global_coords(
            geometry=calc_target_item,
            kind='LINE'
        )
        src_line = src_global_data[1] - src_global_data[0]

        bpy.ops.maplus.addnewline()
        new_line = prims[-1]
        new_line.line_start = start_loc
        new_line.line_end = (
            start_loc + src_line
        )

        return {'FINISHED'}


class ComposeNormalFromPlane(bpy.types.Operator):
    bl_idname = "maplus.composenormalfromplane"
    bl_label = "Get Plane Normal"
    bl_description = "Get the plane's normal as a new line item"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_item = prims[active_item.single_calc_target]

        if not calc_target_item.kind == 'PLANE':
            self.report(
                {'ERROR'},
                ('Wrong operand: "Get Plane Normal" can only operate on'
                 ' a plane')
            )
            return {'CANCELLED'}

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

        bpy.ops.maplus.addnewline()
        new_line = prims[-1]
        new_line.line_start = start_loc
        new_line.line_end = start_loc + normal

        return {'FINISHED'}


class ComposeNewLineFromPoint(bpy.types.Operator):
    bl_idname = "maplus.composenewlinefrompoint"
    bl_label = "New Line from Point"
    bl_description = (
        "Composes a new line item from the supplied point,"
        " starting at the world origin"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_item = prims[active_item.single_calc_target]

        if calc_target_item.kind != 'POINT':
            self.report(
                {'ERROR'},
                ('Wrong operand: "Compose New Line from Point" can'
                 ' only operate on a point')
            )
            return {'CANCELLED'}

        start_loc = mathutils.Vector((0, 0, 0))

        src_global_data = get_modified_global_coords(
            geometry=calc_target_item,
            kind='POINT'
        )

        bpy.ops.maplus.addnewline()
        new_line = prims[-1]
        new_line.line_start = start_loc
        new_line.line_end = src_global_data[0]

        return {'FINISHED'}


class ComposeNewLineAtPointLocation(bpy.types.Operator):
    bl_idname = "maplus.composenewlineatpointlocation"
    bl_label = "New Line at Point Location"
    bl_description = "Composes a new line item starting at the point location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_one = prims[active_item.multi_calc_target_one]
        calc_target_two = prims[active_item.multi_calc_target_two]
        targets_by_kind = {
            item.kind: item for item in [calc_target_one, calc_target_two]
        }

        if not ('POINT' in targets_by_kind and 'LINE' in targets_by_kind):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Compose New Line at Point" can'
                 ' only operate on a line')
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

        bpy.ops.maplus.addnewline()
        new_line = prims[-1]
        new_line.line_start = start_loc
        new_line.line_end = start_loc + src_line

        return {'FINISHED'}


class CalcDistanceBetweenPoints(bpy.types.Operator):
    bl_idname = "maplus.calcdistancebetweenpoints"
    bl_label = "Distance Between Points"
    bl_description = "Calculate the distance between provided point items"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_one = prims[active_item.multi_calc_target_one]
        calc_target_two = prims[active_item.multi_calc_target_two]

        if not (calc_target_one.kind == 'POINT' and
                calc_target_two.kind == 'POINT'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Calculate Distance Between Points" can'
                 ' only operate on two points')
            )
            return {'CANCELLED'}

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
        active_item.multi_calc_result = result
        if addon_data.calc_result_to_clipboard:
            bpy.context.window_manager.clipboard = str(result)

        return {'FINISHED'}


class ComposeNewLineFromPoints(bpy.types.Operator):
    bl_idname = "maplus.composenewlinefrompoints"
    bl_label = "New Line from Points"
    bl_description = "Composes a new line item from provided point items"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_one = prims[active_item.multi_calc_target_one]
        calc_target_two = prims[active_item.multi_calc_target_two]

        if not (calc_target_one.kind == 'POINT' and
                calc_target_two.kind == 'POINT'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Compose New Line from Points" can'
                 ' only operate on two points')
            )
            return {'CANCELLED'}

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

        bpy.ops.maplus.addnewline()
        new_line = prims[-1]
        new_line.line_start = src_pt
        new_line.line_end = dest_pt

        return {'FINISHED'}


class ComposeNewLineVectorAddition(bpy.types.Operator):
    bl_idname = "maplus.composenewlinevectoraddition"
    bl_label = "Add Lines"
    bl_description = "Composes a new line item by vector-adding provided lines"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_one = prims[active_item.multi_calc_target_one]
        calc_target_two = prims[active_item.multi_calc_target_two]

        if not (calc_target_one.kind == 'LINE' and
                calc_target_two.kind == 'LINE'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Add Lines" can only operate on'
                 ' two lines')
            )
            return {'CANCELLED'}

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

        bpy.ops.maplus.addnewline()
        new_line = prims[-1]
        new_line.line_start = start_loc
        new_line.line_end = src_line + dest_line

        return {'FINISHED'}


class ComposeNewLineVectorSubtraction(bpy.types.Operator):
    bl_idname = "maplus.composenewlinevectorsubtraction"
    bl_label = "Subtract Lines"
    bl_description = (
        "Composes a new line item by performing vector-subtraction"
        " (first line minus second line)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_one = prims[active_item.multi_calc_target_one]
        calc_target_two = prims[active_item.multi_calc_target_two]

        if not (calc_target_one.kind == 'LINE' and
                calc_target_two.kind == 'LINE'):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Add Lines" can only operate on'
                 ' two lines')
            )
            return {'CANCELLED'}

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

        bpy.ops.maplus.addnewline()
        new_line = prims[-1]
        new_line.line_start = start_loc
        new_line.line_end = src_line - dest_line

        return {'FINISHED'}


class ComposePointIntersectingLinePlane(bpy.types.Operator):
    bl_idname = "maplus.composepointintersectinglineplane"
    bl_label = "Intersect Line/Plane"
    bl_description = (
        "Composes a new point item by intersecting a line and a plane"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        active_item = prims[addon_data.active_list_item]
        calc_target_one = prims[active_item.multi_calc_target_one]
        calc_target_two = prims[active_item.multi_calc_target_two]
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
            bpy.ops.maplus.addnewpoint()
            new_point = prims[-1]
            new_point.point = intersection
        else:
            self.report(
                {'ERROR'},
                'No intersection: Selected line/plane do not intersect'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


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

                item_info_col.label('Pt. Origin:')
                pt_coord_items = item_info_col.split(percentage=.75)
                typein_and_grab = pt_coord_items.column()
                pt_coord_uppers = typein_and_grab.row()

                pt_coord_uppers_leftside = pt_coord_uppers.row(align=True)
                pt_coord_uppers_leftside.alignment = 'LEFT'
                pt_coord_uppers_leftside.label("Send:")
                pt_coord_uppers_leftside.operator(
                    "maplus.sendpointtocursor",
                    icon='CURSOR',
                    text=""
                )

                pt_coord_uppers_rightside = pt_coord_uppers.row(align=True)
                pt_coord_uppers_rightside.alignment = 'RIGHT'
                pt_coord_uppers_rightside.label("Grab:")
                pt_coord_uppers_rightside.operator(
                    "maplus.grabpointfromcursor",
                    icon='CURSOR',
                    text=""
                )
                pt_coord_uppers_rightside.operator(
                    "maplus.grabpointfromactivelocal",
                    icon='VERTEXSEL',
                    text=""
                )
                pt_coord_uppers_rightside.operator(
                    "maplus.grabpointfromactiveglobal",
                    icon='WORLD',
                    text=""
                )
                typein_and_grab.prop(
                    bpy.types.AnyType(active_item),
                    'point',
                    ""
                )

                component_changers = pt_coord_items.row()
                zero_components = component_changers.column(align=True)
                zero_components.label("Set Zeroes:")
                zero_components.operator(
                    "maplus.zerootherpointx",
                    text="X00"
                )
                zero_components.operator(
                    "maplus.zerootherpointy",
                    text="0Y0"
                )
                zero_components.operator(
                    "maplus.zerootherpointz",
                    text="00Z"
                )
                one_components = component_changers.column(align=True)
                one_components.label("Set Ones:")
                one_components.operator(
                    "maplus.oneotherpointx",
                    text="X11"
                )
                one_components.operator(
                    "maplus.oneotherpointy",
                    text="1Y1"
                )
                one_components.operator(
                    "maplus.oneotherpointz",
                    text="11Z"
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

                item_info_col.label("Start:")
                ln_start_items = item_info_col.split(percentage=.75)
                typein_and_grab_start = ln_start_items.column()
                ln_start_uppers = typein_and_grab_start.split(percentage=.33)
                ln_start_swap = ln_start_uppers.row(align=True)
                ln_start_swap.label("Swap:")
                ln_start_swap.operator(
                    "maplus.swaplinepoints",
                    text="End"
                )

                ln_start_uppers_rightside = ln_start_uppers.row(align=True)
                ln_start_uppers_rightside.alignment = 'RIGHT'

                ln_start_uppers_rightside.label("Send:")
                ln_start_uppers_rightside.operator(
                    "maplus.sendlinestarttocursor",
                    icon='CURSOR',
                    text=""
                )

                ln_start_uppers_rightside.label("Grab:")
                ln_start_uppers_rightside.operator(
                    "maplus.grablinestartfromcursor",
                    icon='CURSOR',
                    text=""
                )
                ln_start_uppers_rightside.operator(
                    "maplus.grablinestartfromactivelocal",
                    icon='VERTEXSEL',
                    text=""
                )
                ln_start_uppers_rightside.operator(
                    "maplus.grablinestartfromactiveglobal",
                    icon='WORLD',
                    text=""
                )
                typein_and_grab_start.prop(
                    bpy.types.AnyType(active_item),
                    'line_start',
                    ""
                )
                item_info_col.separator()

                component_changers_start = ln_start_items.row()
                zero_components = component_changers_start.column(align=True)
                zero_components.label("Set Zeroes:")
                zero_components.operator(
                    "maplus.zerootherlinestartx",
                    text="X00"
                )
                zero_components.operator(
                    "maplus.zerootherlinestarty",
                    text="0Y0"
                )
                zero_components.operator(
                    "maplus.zerootherlinestartz",
                    text="00Z"
                )
                one_components = component_changers_start.column(align=True)
                one_components.label("Set Ones:")
                one_components.operator(
                    "maplus.oneotherlinestartx",
                    text="X11"
                )
                one_components.operator(
                    "maplus.oneotherlinestarty",
                    text="1Y1"
                )
                one_components.operator(
                    "maplus.oneotherlinestartz",
                    text="11Z"
                )

                item_info_col.label("End:")
                ln_end_items = item_info_col.split(percentage=.75)
                typein_and_grab_end = ln_end_items.column()
                ln_end_uppers = typein_and_grab_end.split(percentage=.33)
                ln_end_swap = ln_end_uppers.row(align=True)
                ln_end_swap.label("Swap:")
                ln_end_swap.operator(
                    "maplus.swaplinepoints",
                    text="Start"
                )

                ln_end_uppers_rightside = ln_end_uppers.row(align=True)
                ln_end_uppers_rightside.alignment = 'RIGHT'
                ln_end_uppers_rightside.label("Send:")
                ln_end_uppers_rightside.operator(
                    "maplus.sendlineendtocursor",
                    icon='CURSOR',
                    text=""
                )

                ln_end_uppers_rightside.label("Grab:")
                ln_end_uppers_rightside.operator(
                    "maplus.grablineendfromcursor",
                    icon='CURSOR',
                    text=""
                )
                ln_end_uppers_rightside.operator(
                    "maplus.grablineendfromactivelocal",
                    icon='VERTEXSEL',
                    text=""
                )
                ln_end_uppers_rightside.operator(
                    "maplus.grablineendfromactiveglobal",
                    icon='WORLD',
                    text=""
                )
                typein_and_grab_end.prop(
                    bpy.types.AnyType(active_item),
                    'line_end',
                    ""
                )

                component_changers_end = ln_end_items.row()
                zero_components = component_changers_end.column(align=True)
                zero_components.label("Set Zeroes:")
                zero_components.operator(
                    "maplus.zerootherlineendx",
                    text="X00"
                )
                zero_components.operator(
                    "maplus.zerootherlineendy",
                    text="0Y0"
                )
                zero_components.operator(
                    "maplus.zerootherlineendz",
                    text="00Z"
                )
                one_components = component_changers_end.column(align=True)
                one_components.label("Set Ones:")
                one_components.operator(
                    "maplus.oneotherlineendx",
                    text="X11"
                )
                one_components.operator(
                    "maplus.oneotherlineendy",
                    text="1Y1"
                )
                one_components.operator(
                    "maplus.oneotherlineendz",
                    text="11Z"
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

                item_info_col.label("Pt. A:")
                plane_a_items = item_info_col.split(percentage=.75)
                typein_and_grab_plna = plane_a_items.column()
                plane_a_uppers = typein_and_grab_plna.split(percentage=.33)

                plane_a_swap = plane_a_uppers.row(align=True)
                plane_a_swap.label("Swap With:")
                plane_a_swap.operator(
                    "maplus.swapplaneaplaneb",
                    text="B"
                )
                plane_a_swap.operator(
                    "maplus.swapplaneaplanec",
                    text="C"
                )

                plane_a_uppers_rightside = plane_a_uppers.row(align=True)
                plane_a_uppers_rightside.alignment = 'RIGHT'
                plane_a_uppers_rightside.label("Send:")
                plane_a_uppers_rightside.operator(
                    "maplus.sendplaneatocursor",
                    icon='CURSOR',
                    text=""
                )

                plane_a_uppers_rightside.label("Grab:")
                plane_a_uppers_rightside.operator(
                    "maplus.grabplaneafromcursor",
                    icon='CURSOR',
                    text=""
                )
                plane_a_uppers_rightside.operator(
                    "maplus.grabplaneafromactivelocal",
                    icon='VERTEXSEL',
                    text=""
                )
                plane_a_uppers_rightside.operator(
                    "maplus.grabplaneafromactiveglobal",
                    icon='WORLD',
                    text=""
                )
                typein_and_grab_plna.prop(
                    bpy.types.AnyType(active_item),
                    'plane_pt_a',
                    ""
                )
                item_info_col.separator()

                component_changers_plna = plane_a_items.row()
                zero_components_plna = component_changers_plna.column(
                    align=True
                )
                zero_components_plna.label("Set Zeroes:")
                zero_components_plna.operator(
                    "maplus.zerootherplanepointax",
                    text="X00"
                )
                zero_components_plna.operator(
                    "maplus.zerootherplanepointay",
                    text="0Y0"
                )
                zero_components_plna.operator(
                    "maplus.zerootherplanepointaz",
                    text="00Z"
                )
                one_components_plna = component_changers_plna.column(
                    align=True
                )
                one_components_plna.label("Set Ones:")
                one_components_plna.operator(
                    "maplus.oneotherplanepointax",
                    text="X11"
                )
                one_components_plna.operator(
                    "maplus.oneotherplanepointay",
                    text="1Y1"
                )
                one_components_plna.operator(
                    "maplus.oneotherplanepointaz",
                    text="11Z"
                )

                item_info_col.label("Pt. B (Pivot):")
                plane_b_items = item_info_col.split(percentage=.75)
                typein_and_grab_plnb = plane_b_items.column()
                plane_b_uppers = typein_and_grab_plnb.split(percentage=.33)
                plane_b_swap = plane_b_uppers.row(align=True)
                plane_b_swap.label("Swap With:")
                plane_b_swap.operator(
                    "maplus.swapplaneaplaneb",
                    text="A"
                )
                plane_b_swap.operator(
                    "maplus.swapplanebplanec",
                    text="C"
                )

                plane_b_uppers_rightside = plane_b_uppers.row(align=True)
                plane_b_uppers_rightside.alignment = 'RIGHT'
                plane_b_uppers_rightside.label("Send:")
                plane_b_uppers_rightside.operator(
                    "maplus.sendplanebtocursor",
                    icon='CURSOR',
                    text=""
                )

                plane_b_uppers_rightside.label("Grab:")
                plane_b_uppers_rightside.operator(
                    "maplus.grabplanebfromcursor",
                    icon='CURSOR',
                    text=""
                )
                plane_b_uppers_rightside.operator(
                    "maplus.grabplanebfromactivelocal",
                    icon='VERTEXSEL',
                    text=""
                )
                plane_b_uppers_rightside.operator(
                    "maplus.grabplanebfromactiveglobal",
                    icon='WORLD',
                    text=""
                )
                typein_and_grab_plnb.prop(
                    bpy.types.AnyType(active_item),
                    'plane_pt_b',
                    ""
                )
                item_info_col.separator()

                component_changers_plnb = plane_b_items.row()
                zero_components_plnb = component_changers_plnb.column(
                    align=True
                )
                zero_components_plnb.label("Set Zeroes:")
                zero_components_plnb.operator(
                    "maplus.zerootherplanepointbx",
                    text="X00"
                )
                zero_components_plnb.operator(
                    "maplus.zerootherplanepointby",
                    text="0Y0"
                )
                zero_components_plnb.operator(
                    "maplus.zerootherplanepointbz",
                    text="00Z"
                )
                one_components_plnb = component_changers_plnb.column(
                    align=True
                )
                one_components_plnb.label("Set Ones:")
                one_components_plnb.operator(
                    "maplus.oneotherplanepointbx",
                    text="X11"
                )
                one_components_plnb.operator(
                    "maplus.oneotherplanepointby",
                    text="1Y1"
                )
                one_components_plnb.operator(
                    "maplus.oneotherplanepointbz",
                    text="11Z"
                )

                item_info_col.label("Pt. C:")
                plane_c_items = item_info_col.split(percentage=.75)
                typein_and_grab_plnc = plane_c_items.column()
                plane_c_uppers = typein_and_grab_plnc.split(percentage=.33)
                plane_c_swap = plane_c_uppers.row(align=True)
                plane_c_swap.label("Swap With:")
                plane_c_swap.operator(
                    "maplus.swapplaneaplanec",
                    text="A"
                )
                plane_c_swap.operator(
                    "maplus.swapplanebplanec",
                    text="B"
                )

                plane_c_uppers_rightside = plane_c_uppers.row(align=True)
                plane_c_uppers_rightside.alignment = 'RIGHT'
                plane_c_uppers_rightside.label("Send:")
                plane_c_uppers_rightside.operator(
                    "maplus.sendplanectocursor",
                    icon='CURSOR',
                    text=""
                )

                plane_c_uppers_rightside.label("Grab:")
                plane_c_uppers_rightside.operator(
                    "maplus.grabplanecfromcursor",
                    icon='CURSOR',
                    text=""
                )
                plane_c_uppers_rightside.operator(
                    "maplus.grabplanecfromactivelocal",
                    icon='VERTEXSEL',
                    text=""
                )
                plane_c_uppers_rightside.operator(
                    "maplus.grabplanecfromactiveglobal",
                    icon='WORLD',
                    text=""
                )
                typein_and_grab_plnc.prop(
                    bpy.types.AnyType(active_item),
                    'plane_pt_c',
                    ""
                )

                component_changers_plnc = plane_c_items.row()
                zero_components_plnc = component_changers_plnc.column(
                    align=True
                )
                zero_components_plnc.label("Set Zeroes:")
                zero_components_plnc.operator(
                    "maplus.zerootherplanepointcx",
                    text="X00"
                )
                zero_components_plnc.operator(
                    "maplus.zerootherplanepointcy",
                    text="0Y0"
                )
                zero_components_plnc.operator(
                    "maplus.zerootherplanepointcz",
                    text="00Z"
                )
                one_components_plnc = component_changers_plnc.column(
                    align=True
                )
                one_components_plnc.label("Set Ones:")
                one_components_plnc.operator(
                    "maplus.oneotherplanepointcx",
                    text="X11"
                )
                one_components_plnc.operator(
                    "maplus.oneotherplanepointcy",
                    text="1Y1"
                )
                one_components_plnc.operator(
                    "maplus.oneotherplanepointcz",
                    text="11Z"
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
        if not addon_data.quick_align_pts_auto_grab_src:
            apt_grab_col.operator(
                "maplus.quickalignpointsgrabsrc",
                icon='WORLD',
                text="Grab Source"
            )
        apt_grab_col.operator(
            "maplus.quickalignpointsgrabdest",
            icon='WORLD',
            text="Grab Destination"
        )
        align_pts_gui.label("Operator settings:")
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
        if not addon_data.quick_align_lines_auto_grab_src:
            aln_grab_col.operator(
                    "maplus.quickalignlinesgrabsrc",
                    icon='WORLD',
                    text="Grab Source"
            )
        aln_grab_col.operator(
                "maplus.quickalignlinesgrabdest",
                icon='WORLD',
                text="Grab Destination"
        )
        aln_gui.label("Operator settings:")
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
        if not addon_data.quick_align_planes_auto_grab_src:
            apl_grab_col.operator(
                    "maplus.quickalignplanesgrabsrc",
                    icon='WORLD',
                    text="Grab Source"
            )
        apl_grab_col.operator(
                "maplus.quickalignplanesgrabdest",
                icon='WORLD',
                text="Grab Destination"
        )
        apl_gui.label("Operator settings:")
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
        if not addon_data.quick_axis_rotate_auto_grab_src:
            axr_grab_col.operator(
                    "maplus.quickaxisrotategrabsrc",
                    icon='WORLD',
                    text="Grab Axis"
            )
        axr_gui.label("Operator settings:")
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
        if not addon_data.quick_directional_slide_auto_grab_src:
            ds_grab_col.operator(
                    "maplus.quickdirectionalslidegrabsrc",
                    icon='WORLD',
                    text="Grab Source"
            )
        ds_gui.label("Operator settings:")
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
        if not addon_data.quick_scale_match_edge_auto_grab_src:
            sme_grab_col.operator(
                    "maplus.quickscalematchedgegrabsrc",
                    icon='WORLD',
                    text="Grab Source"
            )
        sme_grab_col.operator(
                "maplus.quickscalematchedgegrabdest",
                icon='WORLD',
                text="Grab Destination"
        )
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
