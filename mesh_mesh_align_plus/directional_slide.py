"""Directional Slide tool, internals & UI."""


import bmesh
import bpy
import mathutils

import mesh_mesh_align_plus.utils.exceptions as maplus_except
import mesh_mesh_align_plus.utils.geom as maplus_geom
import mesh_mesh_align_plus.utils.gui_tools as maplus_guitools


class MAPLUS_OT_DirectionalSlideBase(bpy.types.Operator):
    bl_idname = "maplus.directionalslidebase"
    bl_label = "Directional Slide Base"
    bl_description = "Directional slide base class"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not (maplus_geom.get_active_object() and maplus_geom.get_select_state(maplus_geom.get_active_object())):
            self.report(
                {'ERROR'},
                ('Cannot complete: need at least'
                 ' one active (and selected) object.')
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = maplus_geom.get_active_object().mode
        if not hasattr(self, "quick_op_target"):
            active_item = prims[addon_data.active_list_item]
        else:
            active_item = addon_data.quick_directional_slide_transf

        if (maplus_geom.get_active_object() and
                type(maplus_geom.get_active_object().data) == bpy.types.Mesh):

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
                        vert_data = maplus_geom.return_selected_verts(
                            maplus_geom.get_active_object(),
                            len(vert_attribs_to_set),
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

                    maplus_geom.set_item_coords(
                        addon_data.quick_directional_slide_src,
                        vert_attribs_to_set,
                        vert_data
                    )

                src_global_data = maplus_geom.get_modified_global_coords(
                    geometry=addon_data.quick_directional_slide_src,
                    kind='LINE'
                )

            else:
                src_global_data = maplus_geom.get_modified_global_coords(
                    geometry=prims[active_item.ds_direction],
                    kind='LINE'
                )

            # These global point coordinate vectors will be used to construct
            # geometry and transformations in both object (global) space
            # and mesh (local) space
            dir_start = src_global_data[0]
            dir_end = src_global_data[1]

            # create common vars needed for object and for mesh level transfs
            active_obj_transf = maplus_geom.get_active_object().matrix_world.copy()
            inverse_active = active_obj_transf.copy()
            inverse_active.invert()

            multi_edit_targets = [
                model for model in bpy.context.scene.objects if (
                    maplus_geom.get_select_state(model) and model.type == 'MESH'
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
                    dir_start_loc = unaltered_inverse_loc @ dir_start
                    dir_end_loc = unaltered_inverse_loc @ dir_end

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


class MAPLUS_OT_DirectionalSlideObject(MAPLUS_OT_DirectionalSlideBase):
    bl_idname = "maplus.directionalslideobject"
    bl_label = "Directional Slide Object"
    bl_description = "Translates a target object (moves in a direction)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class MAPLUS_OT_QuickDirectionalSlideObject(MAPLUS_OT_DirectionalSlideBase):
    bl_idname = "maplus.quickdirectionalslideobject"
    bl_label = "Directional Slide Object"
    bl_description = "Translates a target object (moves in a direction)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class MAPLUS_OT_DirectionalSlideMeshSelected(MAPLUS_OT_DirectionalSlideBase):
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


class MAPLUS_OT_DirectionalSlideWholeMesh(MAPLUS_OT_DirectionalSlideBase):
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


class MAPLUS_OT_QuickDirectionalSlideMeshSelected(MAPLUS_OT_DirectionalSlideBase):
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


class MAPLUS_OT_QuickDirectionalSlideWholeMesh(MAPLUS_OT_DirectionalSlideBase):
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


class MAPLUS_PT_QuickDirectionalSlideGUI(bpy.types.Panel):
    bl_idname = "MAPLUS_PT_QuickDirectionalSlideGUI"
    bl_label = "Quick Directional Slide"
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

        ds_top = layout.row()
        ds_gui = layout.box()
        ds_top.label(text=
            "Directional Slide",
            icon="CURVE_PATH"
        )
        ds_grab_col = ds_gui.column()
        ds_grab_col.prop(
            addon_data,
            'quick_directional_slide_auto_grab_src',
            text='Auto Grab Source from Selected Vertices'
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
                        icon='LIGHT_SUN',
                        text="Grab Source"
                )
                preserve_button_roundedge.operator(
                    "maplus.quickdsgrabnormalsrc",
                    icon='LIGHT_HEMI',
                    text=""
                )

            else:
                ds_src_geom_top.operator(
                        "maplus.showhidequickdssrcgeom",
                        icon='TRIA_DOWN',
                        text="",
                        emboss=False
                )
                ds_src_geom_top.label(
                    text="Source Coordinates",
                    icon="LIGHT_SUN"
                )

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
                    icon='LIGHT_HEMI',
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
                modifier_header.label(text="Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = ds_src_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_directional_slide_src),
                    'ln_make_unit_vec',
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_directional_slide_src),
                    'ln_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_directional_slide_src),
                    'ln_multiplier',
                    text="Multiplier"
                )

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

        ds_gui.label(text="Operator settings:", icon="PREFERENCES")
        ds_mods = ds_gui.box()
        ds_box_row1 = ds_mods.row()
        ds_box_row1.prop(
            addon_data.quick_directional_slide_transf,
            'ds_make_unit_vec',
            text='Set Length to 1'
        )
        ds_box_row1.prop(
            addon_data.quick_directional_slide_transf,
            'ds_flip_direction',
            text='Flip Direction'
        )
        ds_box_row2 = ds_mods.row()
        ds_box_row2.prop(
            addon_data.quick_directional_slide_transf,
            'ds_multiplier',
            text='Multiplier'
        )
        ds_apply_header = ds_gui.row()
        ds_apply_header.label(text="Apply to:")
        ds_apply_header.prop(
            addon_data,
            'use_experimental',
            text='Enable Experimental Mesh Ops.'
        )
        ds_apply_items = ds_gui.split(factor=.33)
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
