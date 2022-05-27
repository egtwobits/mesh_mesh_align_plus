"""Legacy tools system (A unified list-style GUI with geometry/transforms)."""


import bpy

import mesh_mesh_align_plus.utils.exceptions as maplus_except
import mesh_mesh_align_plus.utils.geom as maplus_geom
import mesh_mesh_align_plus.utils.gui_tools as maplus_guitools


# Custom list, for displaying combined list of all primitives (Used at top
# of main panel and for item pointers in transformation primitives
class MAPLUS_UL_MAPlusList(bpy.types.UIList):
    bl_idname = "MAPLUS_UL_MAPlusList"

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
            layout.label(text=item.name, icon="LAYER_ACTIVE")
        elif item.kind == 'LINE':
            layout.label(text=item.name, icon="LIGHT_SUN")
        elif item.kind == 'PLANE':
            layout.label(text=item.name, icon="OUTLINER_OB_MESH")
        elif item.kind == 'CALCULATION':
            layout.label(text=item.name, icon="NODETREE")
        elif item.kind == 'TRANSFORMATION':
            layout.label(text=item.name, icon="GRAPH")


class MAPLUS_OT_AddListItemBase(bpy.types.Operator):
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
                raise maplus_except.UniqueNameError('Cannot add, unique name error.')
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
        except maplus_except.UniqueNameError:
            self.report({'ERROR'}, 'Cannot add item, unique name error.')
            return {'CANCELLED'}

        return {'FINISHED'}


class MAPLUS_OT_RemoveListItem(bpy.types.Operator):
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


class MAPLUS_OT_AddNewPoint(MAPLUS_OT_AddListItemBase):
    bl_idname = "maplus.addnewpoint"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "POINT"


class MAPLUS_OT_AddNewLine(MAPLUS_OT_AddListItemBase):
    bl_idname = "maplus.addnewline"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "LINE"


class MAPLUS_OT_AddNewPlane(MAPLUS_OT_AddListItemBase):
    bl_idname = "maplus.addnewplane"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "PLANE"


class MAPLUS_OT_AddNewCalculation(MAPLUS_OT_AddListItemBase):
    bl_idname = "maplus.addnewcalculation"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "CALCULATION"


class MAPLUS_OT_AddNewTransformation(MAPLUS_OT_AddListItemBase):
    bl_idname = "maplus.addnewtransformation"
    bl_label = "Add a new item"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = "TRANSFORMATION"


class MAPLUS_OT_DuplicateItemBase(bpy.types.Operator):
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
            new_item = MAPLUS_OT_AddListItemBase.add_new_named(self)
        except maplus_except.UniqueNameError:
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


# Basic type selector functionality, derived classes provide
# the "kind" to switch to (target_type attrib)
class MAPLUS_OT_ChangeTypeBaseClass(bpy.types.Operator):
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


class MAPLUS_OT_ChangeTypeToPointPrim(MAPLUS_OT_ChangeTypeBaseClass):
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


class MAPLUS_OT_ChangeTypeToLinePrim(MAPLUS_OT_ChangeTypeBaseClass):
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


class MAPLUS_OT_ChangeTypeToPlanePrim(MAPLUS_OT_ChangeTypeBaseClass):
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


class MAPLUS_OT_ChangeTypeToCalcPrim(MAPLUS_OT_ChangeTypeBaseClass):
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


class MAPLUS_OT_ChangeTypeToTransfPrim(MAPLUS_OT_ChangeTypeBaseClass):
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



class MAPLUS_OT_ChangeCalcBaseClass(bpy.types.Operator):
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


class MAPLUS_OT_ChangeCalcToSingle(MAPLUS_OT_ChangeCalcBaseClass):
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


class MAPLUS_OT_ChangeCalcToMulti(MAPLUS_OT_ChangeCalcBaseClass):
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
class MAPLUS_OT_ChangeTransfBaseClass(bpy.types.Operator):
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


class MAPLUS_OT_ChangeTransfToAlignPoints(MAPLUS_OT_ChangeTransfBaseClass):
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


class MAPLUS_OT_ChangeTransfToDirectionalSlide(MAPLUS_OT_ChangeTransfBaseClass):
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


class MAPLUS_OT_ChangeTransfToScaleMatchEdge(MAPLUS_OT_ChangeTransfBaseClass):
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


class MAPLUS_OT_ChangeTransfToAxisRotate(MAPLUS_OT_ChangeTransfBaseClass):
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


class MAPLUS_OT_ChangeTransfToAlignLines(MAPLUS_OT_ChangeTransfBaseClass):
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


class MAPLUS_OT_ChangeTransfToAlignPlanes(MAPLUS_OT_ChangeTransfBaseClass):
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


class MAPLUS_OT_SpecialsAddFromActiveBase(bpy.types.Operator):
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
            vert_data = maplus_geom.return_selected_verts(
                maplus_geom.get_active_object(),
                len(self.vert_attribs_to_set),
                maplus_geom.get_active_object().matrix_world
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

        target_data = dict(zip(self.vert_attribs_to_set, vert_data))
        try:
            new_item = MAPLUS_OT_AddListItemBase.add_new_named(self)
        except maplus_except.UniqueNameError:
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


class MAPLUS_OT_SpecialsAddPointFromActiveGlobal(MAPLUS_OT_SpecialsAddFromActiveBase):
    bl_idname = "maplus.specialsaddpointfromactiveglobal"
    bl_label = "Point From Active Global"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = 'POINT'
    message_geom_type = 'Point'
    vert_attribs_to_set = ('point',)
    multiply_by_world_matrix = True


class MAPLUS_OT_SpecialsAddLineFromActiveGlobal(MAPLUS_OT_SpecialsAddFromActiveBase):
    bl_idname = "maplus.specialsaddlinefromactiveglobal"
    bl_label = "Line From Active Global"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = 'LINE'
    message_geom_type = 'Line'
    vert_attribs_to_set = ('line_start', 'line_end')
    multiply_by_world_matrix = True


class MAPLUS_OT_SpecialsAddPlaneFromActiveGlobal(MAPLUS_OT_SpecialsAddFromActiveBase):
    bl_idname = "maplus.specialsaddplanefromactiveglobal"
    bl_label = "Plane From Active Global"
    bl_options = {'REGISTER', 'UNDO'}
    new_kind = 'PLANE'
    message_geom_type = 'Plane'
    vert_attribs_to_set = ('plane_pt_a', 'plane_pt_b', 'plane_pt_c')
    multiply_by_world_matrix = True


# Advanced Tools panel
class MAPLUS_PT_MAPlusGui(bpy.types.Panel):
    bl_idname = "MAPLUS_PT_MAPlusGui"
    bl_label = "Mesh Align Plus Advanced Tools"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    # bl_category = "Mesh Align Plus"
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
            "MAPLUS_UL_MAPlusList",
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
            icon='LIGHT_SUN',
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
            icon='GRAPH',
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
            layout.label(text="Add items above")
        else:
            basic_item_attribs_col = layout.column()
            basic_item_attribs_col.label(text="Item Name and Type:")
            item_name_and_types = basic_item_attribs_col.split(
                align=True,
                factor=.8
            )
            item_name_and_types.prop(
                bpy.types.AnyType(active_item),
                'name',
                text=""
            )
            item_name_and_types.prop(
                bpy.types.AnyType(active_item),
                'kind',
                text=""
            )
            basic_item_attribs_col.separator()

            # Item-specific UI elements (primitive-specific data like coords
            # for plane points, transformation type etc.)
            item_info_col = layout.column()

            if active_item.kind == 'POINT':
                modifier_header = item_info_col.row()
                modifier_header.label(text="Point Modifiers:")
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
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(active_item),
                    'pt_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(active_item),
                    'pt_multiplier',
                    text="Multiplier"
                )
                item_info_col.separator()

                item_info_col.label(text="Point Coordinates:")
                pt_grab_all = item_info_col.row(align=True)
                pt_grab_all.operator(
                    "maplus.grabpointfromcursor",
                    icon='PIVOT_CURSOR',
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

                maplus_guitools.layout_coordvec(
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
                modifier_header.label(text="Line Modifiers:")
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
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(active_item),
                    'ln_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(active_item),
                    'ln_multiplier',
                    text="Multiplier"
                )
                item_info_col.separator()

                item_info_col.label(text="Line Coordinates:")
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
                    icon='LIGHT_HEMI',
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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
                item_info_col.label(text="Plane Coordinates:")
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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
                item_info_col.label(text="Calculation Type:")
                calc_type_switcher = item_info_col.row()
                calc_type_switcher.operator(
                    "maplus.changecalctosingle",
                    # icon='PIVOT_INDIVIDUAL',
                    text="Single Item"
                )
                calc_type_switcher.operator(
                    "maplus.changecalctomulti",
                    # icon='PIVOT_INDIVIDUAL',
                    text="Multi-Item"
                )
                item_info_col.separator()
                if active_item.calc_type == 'SINGLEITEM':
                    item_info_col.label(text="Target:")
                    item_info_col.template_list(
                        "MAPLUS_UL_MAPlusList",
                        "single_calc_target_list",
                        maplus_data_ptr,
                        "prim_list",
                        active_item,
                        "single_calc_target",
                        type='DEFAULT'
                    )
                    item_info_col.separator()
                    calcs_and_results_header = item_info_col.row()
                    calcs_and_results_header.label(text=
                        "Available Calc.'s and Result:"
                    )
                    clipboard_row_right = calcs_and_results_header.row()
                    clipboard_row_right.alignment = 'RIGHT'
                    clipboard_row_right.prop(
                        bpy.types.AnyType(maplus_data_ptr),
                        'calc_result_to_clipboard',
                        text="Copy to Clipboard"
                    )
                    item_info_col.prop(
                        bpy.types.AnyType(active_item),
                        'single_calc_result',
                        text="Result"
                    )
                    # Check if the target pointer is valid, since we attempt
                    # to access that index in prims at the beginning here.
                    if active_item.single_calc_target < len(prims):
                        calc_target = prims[active_item.single_calc_target]
                        if calc_target.kind == 'POINT':
                            item_info_col.operator(
                                "maplus.composenewlinefrompoint",
                                icon='LIGHT_SUN',
                                text="New Line from Point"
                            )
                        elif calc_target.kind == 'LINE':
                            item_info_col.operator(
                                "maplus.calclinelength",
                                text="Line Length"
                            )
                            item_info_col.operator(
                                "maplus.composenewlinefromorigin",
                                icon='LIGHT_SUN',
                                text="New Line from Origin"
                            )
                        elif calc_target.kind == 'PLANE':
                            item_info_col.operator(
                                "maplus.composenormalfromplane",
                                icon='LIGHT_SUN',
                                text="Get Plane Normal (Normalized)"
                            )
                elif active_item.calc_type == 'MULTIITEM':

                    item_info_col.label(text="Targets:")
                    calc_targets = item_info_col.row()
                    calc_targets.template_list(
                        "MAPLUS_UL_MAPlusList",
                        "multi_calc_target_one_list",
                        maplus_data_ptr,
                        "prim_list",
                        active_item,
                        "multi_calc_target_one",
                        type='DEFAULT'
                    )
                    calc_targets.template_list(
                        "MAPLUS_UL_MAPlusList",
                        "multi_calc_target_two_list",
                        maplus_data_ptr,
                        "prim_list",
                        active_item,
                        "multi_calc_target_two",
                        type='DEFAULT'
                    )
                    item_info_col.separator()
                    calcs_and_results_header = item_info_col.row()
                    calcs_and_results_header.label(text=
                        "Available Calc.'s and Result:"
                    )
                    clipboard_row_right = calcs_and_results_header.row()
                    clipboard_row_right.alignment = 'RIGHT'
                    clipboard_row_right.prop(
                        bpy.types.AnyType(maplus_data_ptr),
                        'calc_result_to_clipboard',
                        text="Copy to Clipboard"
                    )
                    item_info_col.prop(
                        bpy.types.AnyType(active_item),
                        'multi_calc_result',
                        text="Result"
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
                                icon='LIGHT_SUN',
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
                                icon='LIGHT_SUN',
                                text="Add Lines"
                            )
                            item_info_col.operator(
                                "maplus.composenewlinevectorsubtraction",
                                icon='LIGHT_SUN',
                                text="Subtract Lines"
                            )
                        elif 'POINT' in type_combo and 'LINE' in type_combo:
                            item_info_col.operator(
                                "maplus.composenewlineatpointlocation",
                                icon='LIGHT_SUN',
                                text="New Line at Point"
                            )
                        elif 'LINE' in type_combo and 'PLANE' in type_combo:
                            item_info_col.operator(
                                "maplus.composepointintersectinglineplane",
                                icon='LAYER_ACTIVE',
                                text="Intersect Line/Plane"
                            )

            elif active_item.kind == 'TRANSFORMATION':
                item_info_col.label(text="Transformation Type Selectors:")
                transf_types = item_info_col.row(align=True)
                transf_types.operator(
                    "maplus.changetransftoalignpoints",
                    icon='PIVOT_INDIVIDUAL',
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
                    item_info_col.label(text="Select a transformation above")
                else:
                    apply_buttons_header = item_info_col.row()
                    if active_item.transf_type == 'ALIGNPOINTS':
                        apply_buttons_header.label(
                            text='Apply Align Points to:'
                        )
                        apply_buttons = item_info_col.split(factor=.33)
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
                        apply_buttons_header.label(text=
                            'Apply Directional Slide to:'
                        )
                        apply_buttons = item_info_col.split(factor=.33)
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
                        apply_buttons_header.label(text=
                            'Apply Scale Match Edge to:'
                        )
                        apply_buttons = item_info_col.split(factor=.33)
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
                        apply_buttons_header.label(
                            text='Apply Axis Rotate to:'
                        )
                        apply_buttons = item_info_col.split(factor=.33)
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
                        apply_buttons_header.label(
                            text='Apply Align Lines to:'
                        )
                        apply_buttons = item_info_col.split(factor=.33)
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
                        apply_buttons_header.label(
                            text='Apply Align Planes to:'
                        )
                        apply_buttons = item_info_col.split(factor=.33)
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
                            text='Enable Experimental Mesh Ops.'
                    )

                    active_transf = bpy.types.AnyType(active_item)

                    if (active_item.transf_type != 'SCALEMATCHEDGE' and
                            active_item.transf_type != 'AXISROTATE'):
                        item_info_col.label(text='Transformation Modifiers:')
                        item_mods_box = item_info_col.box()
                        mods_row_1 = item_mods_box.row()
                        mods_row_2 = item_mods_box.row()
                    if active_item.transf_type == "ALIGNPOINTS":
                        mods_row_1.prop(
                            active_transf,
                            'apt_make_unit_vector',
                            text='Set Length Equal to One'
                        )
                        mods_row_1.prop(
                            active_transf,
                            'apt_flip_direction',
                            text='Flip Direction'
                        )
                        mods_row_2.prop(
                            active_transf,
                            'apt_multiplier',
                            text='Multiplier'
                        )
                    if active_item.transf_type == "DIRECTIONALSLIDE":
                        item_info_col.label(text='Item Modifiers:')
                        mods_row_1.prop(
                            active_transf,
                            'ds_make_unit_vec',
                            text="Set Length Equal to One"
                        )
                        mods_row_1.prop(
                            active_transf,
                            'ds_flip_direction',
                            text="Flip Direction"
                        )
                        mods_row_2.prop(
                            active_transf,
                            'ds_multiplier',
                            text="Multiplier"
                        )
                    if active_item.transf_type == "ALIGNLINES":
                        mods_row_1.prop(
                            active_transf,
                            'aln_flip_direction',
                            text="Flip Direction"
                        )
                    if active_item.transf_type == "ALIGNPLANES":
                        mods_row_1.prop(
                            active_transf,
                            'apl_flip_normal',
                            text="Flip Source Normal"
                        )
                        # Todo: determine how to handle this from Adv. Tools
                        # ('use' arg only valid from a 3d view editor/context)
                        # mods_row_1.prop(
                        #    active_transf,
                        #    'apl_use_custom_orientation',
                        #    text="Use Transf. Orientation"
                        # )
                    item_info_col.separator()

                    # Designate operands for the transformation by pointing to
                    # other primitive items in the main list. The indices are
                    # stored on each primitive item
                    if active_item.transf_type == "ALIGNPOINTS":
                        item_info_col.label(text="Source Point")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "apt_pt_one_list",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "apt_pt_one",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.label(text="Destination Point")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "apt_pt_two_list",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "apt_pt_two",
                            type='DEFAULT'
                        )
                    if active_item.transf_type == "DIRECTIONALSLIDE":
                        item_info_col.label(text="Source Line")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "vs_targetLineList",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "ds_direction",
                            type='DEFAULT'
                        )
                    if active_item.transf_type == "SCALEMATCHEDGE":
                        item_info_col.label(text="Source Edge")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "sme_src_edgelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "sme_edge_one",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.label(text="Destination Edge")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "sme_dest_edgelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "sme_edge_two",
                            type='DEFAULT'
                        )
                    if active_item.transf_type == "AXISROTATE":
                        item_info_col.label(text="Axis")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
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
                            text='Amount'
                        )
                    if active_item.transf_type == "ALIGNLINES":
                        item_info_col.label(text="Source Line")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "aln_src_linelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "aln_src_line",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.label(text="Destination Line")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "aln_dest_linelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "aln_dest_line",
                            type='DEFAULT'
                        )
                    if active_item.transf_type == "ALIGNPLANES":
                        item_info_col.label(text="Source Plane")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "apl_src_planelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "apl_src_plane",
                            type='DEFAULT'
                        )
                        item_info_col.separator()
                        item_info_col.label(text="Destination Plane")
                        item_info_col.template_list(
                            "MAPLUS_UL_MAPlusList",
                            "apl_dest_planelist",
                            maplus_data_ptr,
                            "prim_list",
                            active_transf,
                            "apl_dest_plane",
                            type='DEFAULT'
                        )
