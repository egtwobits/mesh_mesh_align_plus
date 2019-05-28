"""Align Planes tool, internals & UI."""


import bmesh
import bpy
import mathutils

import mesh_mesh_align_plus.utils.exceptions as maplus_except
import mesh_mesh_align_plus.utils.geom as maplus_geom
import mesh_mesh_align_plus.utils.gui_tools as maplus_guitools


class MAPLUS_OT_AlignPlanesBase(bpy.types.Operator):
    bl_idname = "maplus.alignplanesbase"
    bl_label = "Align Planes base"
    bl_description = "Align Planes base class"
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
            active_item = addon_data.quick_align_planes_transf

        if (maplus_geom.get_active_object() and
                type(maplus_geom.get_active_object().data) == bpy.types.Mesh):

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
                        addon_data.quick_align_planes_src,
                        vert_attribs_to_set,
                        vert_data
                    )

                src_global_data = maplus_geom.get_modified_global_coords(
                    geometry=addon_data.quick_align_planes_src,
                    kind='PLANE'
                )
                dest_global_data = maplus_geom.get_modified_global_coords(
                    geometry=addon_data.quick_align_planes_dest,
                    kind='PLANE'
                )

            else:
                src_global_data = maplus_geom.get_modified_global_coords(
                    geometry=prims[active_item.apl_src_plane],
                    kind='PLANE'
                )
                dest_global_data = maplus_geom.get_modified_global_coords(
                    geometry=prims[active_item.apl_dest_plane],
                    kind='PLANE'
                )

            # These global point coordinate vectors will be used to construct
            # geometry and transformations in both object (global) space
            # and mesh (local) space
            if active_item.apl_alternate_pivot:
                src_pt_a = src_global_data[1]
                src_pt_b = src_global_data[0]
            else:
                src_pt_a = src_global_data[0]
                src_pt_b = src_global_data[1]
            src_pt_c = src_global_data[2]

            if active_item.apl_alternate_pivot:
                dest_pt_a = dest_global_data[1]
                dest_pt_b = dest_global_data[0]
            else:
                dest_pt_a = dest_global_data[0]
                dest_pt_b = dest_global_data[1]
            dest_pt_c = dest_global_data[2]

            # create common vars needed for object and for mesh level transfs
            active_obj_transf = maplus_geom.get_active_object().matrix_world.copy()
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

            # TODO: Disabled until Blender 2.8 custom transform
            #       orientations status is known
            # # Create custom transform orientation, for sliding the user's
            # # target along the destination face after it has been aligned.
            # # We do this by making a basis matrix out of the dest plane
            # # leading edge vector, the dest normal vector, and the cross
            # # of those two (each vector is normalized first)
            # vdest = dest_pln_ln_BA.copy()
            # vdest.normalize()
            # vnorm = dest_normal.copy()
            # vnorm.normalize()
            # # vnorm.negate()
            # vcross = vdest.cross(vnorm)
            # vcross.normalize()
            # vcross.negate()
            # custom_orientation = mathutils.Matrix(
            #     [
            #         [vcross[0], vnorm[0], vdest[0]],
            #         [vcross[1], vnorm[1], vdest[1]],
            #         [vcross[2], vnorm[2], vdest[2]]
            #     ]
            # )
            # bpy.ops.transform.create_orientation(
            #     name='MAPlus',
            #     use=active_item.apl_use_custom_orientation,
            #     overwrite=True
            # )
            # bpy.context.scene.orientations['MAPlus'].matrix = (
            #     custom_orientation
            # )

            multi_edit_targets = [
                model for model in bpy.context.scene.objects if (
                    maplus_geom.get_select_state(model) and model.type == 'MESH'
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
                    bpy.context.view_layer.update()

                    # Parallelize the leading edges
                    item.rotation_euler.rotate(
                        parallelize_edges
                    )
                    bpy.context.view_layer.update()

                    # get local coords using active object as basis, in
                    # other words, determine coords of the source pivot
                    # relative to the active object's origin by reversing
                    # the active object's transf from the pivot's coords
                    local_src_pivot_coords = (
                        unaltered_inverse @ src_pt_b
                    )

                    # find the new global location of the pivot (we access
                    # the item's matrix_world directly here since we
                    # changed/updated it earlier)
                    new_global_src_pivot_coords = (
                        item.matrix_world @ local_src_pivot_coords
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
                    bpy.context.view_layer.update()

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
                    src_a_loc = unaltered_inverse_loc @ src_pt_a
                    src_b_loc = unaltered_inverse_loc @ src_pt_b
                    src_c_loc = unaltered_inverse_loc @ src_pt_c

                    dest_a_loc = unaltered_inverse_loc @ dest_pt_a
                    dest_b_loc = unaltered_inverse_loc @ dest_pt_b
                    dest_c_loc = unaltered_inverse_loc @ dest_pt_c

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
                        parallelize_planes_loc @ src_ba_loc
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
                        pivot_to_dest_loc @
                        parallelize_edges_loc @
                        parallelize_planes_loc @
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


class MAPLUS_OT_AlignPlanesObject(MAPLUS_OT_AlignPlanesBase):
    bl_idname = "maplus.alignplanesobject"
    bl_label = "Align Planes"
    bl_description = "Makes planes coplanar (flat against each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class MAPLUS_OT_QuickAlignPlanesObject(MAPLUS_OT_AlignPlanesBase):
    bl_idname = "maplus.quickalignplanesobject"
    bl_label = "Align Planes"
    bl_description = "Makes planes coplanar (flat against each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class MAPLUS_OT_AlignPlanesMeshSelected(MAPLUS_OT_AlignPlanesBase):
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


class MAPLUS_OT_AlignPlanesWholeMesh(MAPLUS_OT_AlignPlanesBase):
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


class MAPLUS_OT_QuickAlignPlanesMeshSelected(MAPLUS_OT_AlignPlanesBase):
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


class MAPLUS_OT_QuickAlignPlanesWholeMesh(MAPLUS_OT_AlignPlanesBase):
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


class MAPLUS_PT_QuickAlignPlanesGUI(bpy.types.Panel):
    bl_idname = "MAPLUS_PT_QuickAlignPlanesGUI"
    bl_label = "Quick Align Planes"
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

        apl_top = layout.row()
        apl_gui = layout.box()
        apl_top.label(
            text="Align Planes",
            icon="MOD_ARRAY"
        )
        apl_grab_col = apl_gui.column()
        apl_grab_col.prop(
            addon_data,
            'quick_align_planes_auto_grab_src',
            text='Auto Grab Source from Selected Vertices'
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
                apl_src_geom_top.label(
                    text="Source Coordinates",
                    icon="OUTLINER_OB_MESH"
                )

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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
                    parent_layout=apl_src_geom_editor,
                    coordvec_label="Pt. B:",
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

                maplus_guitools.layout_coordvec(
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
            apl_dest_geom_top.label(
                text="Destination Coordinates",
                icon="OUTLINER_OB_MESH"
            )

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

            maplus_guitools.layout_coordvec(
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

            maplus_guitools.layout_coordvec(
                parent_layout=apl_dest_geom_editor,
                coordvec_label="Pt. B:",
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

            maplus_guitools.layout_coordvec(
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

        apl_gui.label(text="Operator settings:", icon="PREFERENCES")
        apl_mods = apl_gui.box()
        apl_mods_row1 = apl_mods.row()
        apl_mods_row1.prop(
            addon_data.quick_align_planes_transf,
            'apl_flip_normal',
            text='Flip Normal'
        )
        apl_mods_row1.prop(
            addon_data.quick_align_planes_transf,
            'apl_use_custom_orientation',
            text='Use Transf. Orientation'
        )
        apl_mods_row2 = apl_mods.row()
        apl_mods_row2.prop(
            addon_data.quick_align_planes_transf,
            'apl_alternate_pivot',
            text='Pivot is A'
        )
        apl_apply_header = apl_gui.row()
        apl_apply_header.label(text="Apply to:")
        apl_apply_header.prop(
            addon_data,
            'use_experimental',
            text='Enable Experimental Mesh Ops.'
        )
        apl_apply_items = apl_gui.split(factor=.33)
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
