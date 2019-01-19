"""Data structures & tools for storing, modifying, and moving addon data."""


import bpy


# This is the basic data structure for the addon. The item can be a point,
# line, plane, calc, or transf (only one at a time), chosen by the user
# (defaults to point). A MAPlusPrimitive always has data slots for each of
# these types, regardless of which 'kind' the item is currently
class MAPlusPrimitive(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Item name",
        description="The name of this item",
        default="Name"
    )
    kind: bpy.props.EnumProperty(
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
    point: bpy.props.FloatVectorProperty(
        description="Point primitive coordinates",
        precision=6
    )
    pt_make_unit_vec: bpy.props.BoolProperty(
        description="Treat the point like a vector of length 1"
    )
    pt_flip_direction: bpy.props.BoolProperty(
        description=(
            "Treat the point like a vector pointing in"
            " the opposite direction"
        )
    )
    pt_multiplier: bpy.props.FloatProperty(
        description=(
            "Treat the point like a vector and multiply"
            " its length by this value"
        ),
        default=1.0,
        precision=6
    )

    # Line primitive data/settings
    # DuplicateItemBase depends on a complete list of these attribs
    line_start: bpy.props.FloatVectorProperty(
        description="Line primitive, starting point coordinates",
        precision=6
    )
    line_end: bpy.props.FloatVectorProperty(
        description="Line primitive, ending point coordinates",
        precision=6
    )
    ln_make_unit_vec: bpy.props.BoolProperty(
        description="Make the line's length 1"
    )
    ln_flip_direction: bpy.props.BoolProperty(
        description="Point the line in the opposite direction"
    )
    ln_multiplier: bpy.props.FloatProperty(
        description="Multiply the line's length by this amount",
        default=1.0,
        precision=6
    )

    # Plane primitive data
    # DuplicateItemBase depends on a complete list of these attribs
    plane_pt_a: bpy.props.FloatVectorProperty(
        description="Plane primitive, point A coordinates",
        precision=6
    )
    plane_pt_b: bpy.props.FloatVectorProperty(
        description="Plane primitive, point B coordinates",
        precision=6
    )
    plane_pt_c: bpy.props.FloatVectorProperty(
        description="Plane primitive, point C coordinates",
        precision=6
    )

    # Calculation primitive data/settings
    calc_type: bpy.props.EnumProperty(
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
    single_calc_target: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the item that"
            " the calculation will be based on."
        ),
        default=0
    )
    # active item indices for the multi item calc lists
    multi_calc_target_one: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the first item that"
            " the calculation will be based on."
        ),
        default=0
    )
    multi_calc_target_two: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the second item that"
            " the calculation will be based on."
        ),
        default=0
    )

    single_calc_result: bpy.props.FloatProperty(
        description="Single Item Calc. Result",
        default=0,
        precision=6
    )
    multi_calc_result: bpy.props.FloatProperty(
        description="Multi Item Calc. Result",
        default=0,
        precision=6
    )

    # Transformation primitive data/settings (several blocks)
    transf_type: bpy.props.EnumProperty(
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
    apt_pt_one: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the source point"
            " (this point will be 'moved' to match the destination)."
        ),
        default=0
    )
    apt_pt_two: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the destination point"
            " (this is a fixed reference location, where"
            " the source point will be 'moved' to)."
        ),
        default=0
    )
    apt_make_unit_vector: bpy.props.BoolProperty(
        description="Set the move distance equal to one",
        default=False
    )
    apt_flip_direction: bpy.props.BoolProperty(
        description="Flip the move direction",
        default=False
    )
    apt_multiplier: bpy.props.FloatProperty(
        description="Multiply the move by this amount",
        default=1.0,
        precision=6
    )

    # "Align Planes" (transformation) data/settings
    apl_src_plane: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the source plane"
            " (this plane will be 'moved' to match the destination)."
        ),
        default=0
    )
    apl_dest_plane: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the destination plane"
            " (this is a fixed reference location, where"
            " the source plane will be 'moved' to)."
        ),
        default=0
    )
    apl_flip_normal: bpy.props.BoolProperty(
        description="Flips the normal of the source plane",
        default=False
    )
    apl_use_custom_orientation: bpy.props.BoolProperty(
        description=(
            "Switches to custom transform orientation upon applying"
            " the operator (oriented to the destination plane)."
        ),
        default=False
    )
    apl_alternate_pivot: bpy.props.BoolProperty(
        description=(
            "Make the first point (A) the pivot (The first point selected on"
            " each plane will be aligned to each other). Turn this off for"
            " 'classic'/'old-style' behavior, where point B is the pivot."
        ),
        default=True
    )

    # "Align Lines" (transformation) data/settings
    aln_src_line: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the source line"
            " (this line will be 'moved' to match the destination)."
        ),
        default=0
    )
    aln_dest_line: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the destination line"
            " (this is a fixed reference location, where"
            " the source line will be 'moved' to)."
        ),
        default=0
    )
    aln_flip_direction: bpy.props.BoolProperty(
        description="Flip the source line direction",
        default=False
    )

    # "Axis rotate" (transformation) data/settings
    axr_axis: bpy.props.IntProperty(
        description="The axis to rotate around",
        default=0
    )
    axr_amount: bpy.props.FloatProperty(
        description=(
            "How much to rotate around the specified axis"
            " (units are set to radians or degrees"
            " depending on Blender user settings)"
        ),
        default=0,
        precision=6
    )

    # "Directional slide" (transformation) data/settings
    ds_direction: bpy.props.IntProperty(
        description="The direction to move",
        default=0
    )  # This is a list item pointer
    ds_make_unit_vec: bpy.props.BoolProperty(
        description="Make the line's length 1",
        default=False
    )
    ds_flip_direction: bpy.props.BoolProperty(
        description="Flip source line direction",
        default=False
    )
    ds_multiplier: bpy.props.FloatProperty(
        description="Multiply the source line's length by this amount",
        default=1.0,
        precision=6
    )

    # "Scale Match Edge" (transformation) data/settings
    sme_edge_one: bpy.props.IntProperty(
        description=(
            "Pointer to an item in the list, the source edge"
            " (this edge will be scaled to match"
            " the destination edge's length)."
        ),
        default=0
    )
    sme_edge_two: bpy.props.IntProperty(
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
    prim_list: bpy.props.CollectionProperty(type=MAPlusPrimitive)
    # stores index of active primitive in my UIList
    active_list_item: bpy.props.IntProperty()
    use_experimental: bpy.props.BoolProperty(
        description=(
            'Use experimental:'
            ' Mesh transformations are not currently'
            ' supported on objects with non-uniform'
            ' scaling. These are designated experimental'
            ' until non-uniform scaling is supported.'
        )
    )

    # Items for the quick operators
    quick_align_pts_show: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the align points operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_apt_show_src_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_apt_show_dest_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the destination geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_align_pts_auto_grab_src: bpy.props.BoolProperty(
        description=(
            "Automatically grab source point from selected geometry"
        ),
        default=True
    )
    quick_align_pts_src: bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_pts_dest: bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_pts_transf: bpy.props.PointerProperty(type=MAPlusPrimitive)

    quick_directional_slide_show: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the directional slide operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_ds_show_src_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_directional_slide_auto_grab_src: bpy.props.BoolProperty(
        description=(
            "Automatically grab source line from selected geometry"
        ),
        default=True
    )
    quick_directional_slide_src: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_directional_slide_dest: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_directional_slide_transf: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )

    quick_scale_match_edge_show: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the scale match edge operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_sme_show_src_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_sme_show_dest_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the destination geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_scale_match_edge_auto_grab_src: bpy.props.BoolProperty(
        description=(
            "Automatically grab source line from selected geometry"
        ),
        default=True
    )
    quick_scale_match_edge_src: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_scale_match_edge_dest: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_scale_match_edge_transf: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    # Scale Match Edge numeric mode items
    quick_sme_numeric_mode: bpy.props.BoolProperty(
        description=(
            'Use alternate "Numeric Input" mode to type a target edge'
            ' length in directly.'
        ),
        default=False
    )
    quick_sme_numeric_auto: bpy.props.BoolProperty(
        description=(
            "Automatically grab target line from selected geometry"
        ),
        default=True
    )
    quick_sme_numeric_length: bpy.props.FloatProperty(
        description="Desired length for the target edge",
        default=1,
        precision=6
    )
    quick_sme_numeric_src: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )
    quick_sme_numeric_dest: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )

    quick_align_lines_show: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the align lines operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_aln_show_src_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_aln_show_dest_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the destination geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_align_lines_auto_grab_src: bpy.props.BoolProperty(
        description=(
            "Automatically grab source line from selected geometry"
        ),
        default=True
    )
    quick_align_lines_src: bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_lines_dest: bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_lines_transf: bpy.props.PointerProperty(type=MAPlusPrimitive)

    quick_axis_rotate_show: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the axis rotate operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_axr_show_src_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_axis_rotate_auto_grab_src: bpy.props.BoolProperty(
        description=(
            "Automatically grab source axis from selected geometry"
        ),
        default=True
    )
    quick_axis_rotate_src: bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_axis_rotate_transf: bpy.props.PointerProperty(type=MAPlusPrimitive)

    quick_align_planes_show: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the align planes operator"
            " in the quick tools panel."
        ),
        default=True
    )
    quick_apl_show_src_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the source geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_apl_show_dest_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the destination geometry editor"
            " in the quick tools panel."
        ),
        default=False
    )
    quick_align_planes_auto_grab_src: bpy.props.BoolProperty(
        description=(
            "Automatically grab source plane from selected geometry"
        ),
        default=True
    )
    quick_align_planes_src: bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_planes_dest: bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_align_planes_transf: bpy.props.PointerProperty(
        type=MAPlusPrimitive
    )

    # Calculation global settings
    calc_result_to_clipboard: bpy.props.BoolProperty(
        description=(
            "Copy  calculation results (new reference locations or"
            " numeric calculations) to the addon clipboard or the"
            " system clipboard, respectively."
        ),
        default=True
    )

    # Quick Calculation items
    quick_calc_check_types: bpy.props.BoolProperty(
        description=(
            "Check/verify slot types and disable operations that do not"
            " match the type(s) of the current geometry item slots."
            " Uncheck to silently allow calculations on slot data that is"
            " not currently displayed in the interface."
        ),
        default=True
    )
    quick_calc_show_slot1_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the slot 1 geometry editor"
            " in the calculate/compose panel."
        ),
        default=False
    )
    quick_calc_show_slot2_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the slot 2 geometry editor"
            " in the calculate/compose panel."
        ),
        default=False
    )
    quick_calc_show_result_geom: bpy.props.BoolProperty(
        description=(
            "Expand/collapse the calculation result geometry editor"
            " in the calculate/compose panel."
        ),
        default=False
    )
    quick_calc_result_item: bpy.props.PointerProperty(type=MAPlusPrimitive)
    quick_calc_result_numeric: bpy.props.FloatProperty(
        description="Quick Calculation numeric result",
        default=0,
        precision=6
    )
    internal_storage_slot_1: bpy.props.PointerProperty(type=MAPlusPrimitive)
    internal_storage_slot_2: bpy.props.PointerProperty(type=MAPlusPrimitive)
    internal_storage_clipboard: bpy.props.PointerProperty(type=MAPlusPrimitive)


def copy_source_attribs_to_dest(source, dest, set_attribs=None):
    if set_attribs:
        for att in set_attribs:
            setattr(dest, att, getattr(source, att))


class MAPLUS_OT_CopyToOtherBase(bpy.types.Operator):
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



class MAPLUS_OT_PasteIntoAdvToolsActive(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoadvtoolsactive"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'ADVTOOLSACTIVE')


class MAPLUS_OT_CopyFromAdvToolsActive(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromadvtoolsactive"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('ADVTOOLSACTIVE', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoSlot1(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoslot1"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'SLOT1')


class MAPLUS_OT_CopyFromSlot1(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromslot1"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('SLOT1', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoSlot2(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoslot2"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'SLOT2')


class MAPLUS_OT_CopyFromSlot2(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromslot2"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('SLOT2', 'INTERNALCLIPBOARD')


class MAPLUS_OT_CopyFromCalcResult(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromcalcresult"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('CALCRESULT', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoCalcResult(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintocalcresult"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'CALCRESULT')


class MAPLUS_OT_PasteIntoAptSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoaptsrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'APTSRC')


class MAPLUS_OT_CopyFromAptSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromaptsrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('APTSRC', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoAptDest(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoaptdest"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'APTDEST')


class MAPLUS_OT_CopyFromAptDest(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromaptdest"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('APTDEST', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoAlnSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoalnsrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'ALNSRC')


class MAPLUS_OT_CopyFromAlnSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromalnsrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('ALNSRC', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoAlnDest(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoalndest"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'ALNDEST')


class MAPLUS_OT_CopyFromAlnDest(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromalndest"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('ALNDEST', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoAplSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoaplsrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'APLSRC')


class MAPLUS_OT_CopyFromAplSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromaplsrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('APLSRC', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoAplDest(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoapldest"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'APLDEST')


class MAPLUS_OT_CopyFromAplDest(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromapldest"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('APLDEST', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoAxrSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintoaxrsrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'AXRSRC')


class MAPLUS_OT_CopyFromAxrSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromaxrsrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('AXRSRC', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoDsSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintodssrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'DSSRC')


class MAPLUS_OT_CopyFromDsSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromdssrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('DSSRC', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoSmeSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintosmesrc"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'SMESRC')


class MAPLUS_OT_CopyFromSmeSrc(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromsmesrc"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('SMESRC', 'INTERNALCLIPBOARD')


class MAPLUS_OT_PasteIntoSmeDest(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.pasteintosmedest"
    bl_label = "Paste into this item"
    bl_description = "Pastes from the internal clipboard into this item"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('INTERNALCLIPBOARD', 'SMEDEST')


class MAPLUS_OT_CopyFromSmeDest(MAPLUS_OT_CopyToOtherBase):
    bl_idname = "maplus.copyfromsmedest"
    bl_label = "Copy from this item"
    bl_description = "Copies this item into the internal clipboard"
    bl_options = {'REGISTER', 'UNDO'}
    # A tuple of strings indicating the source and destination
    source_dest_pair = ('SMEDEST', 'INTERNALCLIPBOARD')
