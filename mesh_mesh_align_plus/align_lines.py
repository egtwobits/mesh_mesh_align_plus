"""Align Lines tool, internals & UI."""


import bmesh
import bpy
import mathutils

import mesh_mesh_align_plus.utils.exceptions as maplus_except
import mesh_mesh_align_plus.utils.geom as maplus_geom
import mesh_mesh_align_plus.utils.gui_tools as maplus_guitools


class MAPLUS_OT_AlignLinesBase(bpy.types.Operator):
    bl_idname = "maplus.alignlinesbase"
    bl_label = "Align Lines Base"
    bl_description = "Align lines base class"
    bl_options = {'REGISTER', 'UNDO'}
    target = None

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list
        previous_mode = maplus_geom.get_active_object().mode
        if hasattr(self, "quick_op_target"):
            active_item = addon_data.quick_align_lines_transf
        else:
            active_item = prims[addon_data.active_list_item]
        # Gather selected Blender object(s) to apply the transform to
        multi_edit_targets = [
            item for item in bpy.context.scene.objects if (
                maplus_geom.get_select_state(item)
            )
        ]
        # Check prerequisites for mesh level transforms, need an active/selected object
        if (self.target != 'OBJECT' and not (maplus_geom.get_active_object()
                and maplus_geom.get_select_state(maplus_geom.get_active_object()))):
            self.report(
                {'ERROR'},
                ('Cannot complete: cannot perform mesh-level transform'
                 ' without an active (and selected) object.')
            )
            return {'CANCELLED'}
        # Check auto grab prerequisites
        if addon_data.quick_align_lines_auto_grab_src:
            if not (maplus_geom.get_active_object()
                    and maplus_geom.get_select_state(maplus_geom.get_active_object())):
                self.report(
                    {'ERROR'},
                    ('Cannot complete: cannot auto-grab source verts '
                     ' without an active (and selected) object.')
                )
                return {'CANCELLED'}
            if maplus_geom.get_active_object().type != 'MESH':
                self.report(
                    {'ERROR'},
                    ('Cannot complete: cannot auto-grab source verts '
                     ' from a non-mesh object.')
                )
                return {'CANCELLED'}

        # Proceed only if selected Blender objects are compatible with the transform target
        # (Do not allow mesh-level transforms when there are non-mesh objects selected)
        if not (self.target in {'MESH_SELECTED', 'WHOLE_MESH', 'OBJECT_ORIGIN'}
                and [item for item in multi_edit_targets if item.type != 'MESH']):

            if not hasattr(self, "quick_op_target"):
                if (prims[active_item.aln_src_line].kind != 'LINE' or
                        prims[active_item.aln_dest_line].kind != 'LINE'):
                    self.report(
                        {'ERROR'},
                        ('Wrong operands: "Align Lines" can only operate on '
                         'two lines')
                    )
                    return {'CANCELLED'}

            if maplus_geom.get_active_object().type == 'MESH':
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
                        addon_data.quick_align_lines_src,
                        vert_attribs_to_set,
                        vert_data
                    )

                src_global_data = maplus_geom.get_modified_global_coords(
                    geometry=addon_data.quick_align_lines_src,
                    kind='LINE'
                )
                dest_global_data = maplus_geom.get_modified_global_coords(
                    geometry=addon_data.quick_align_lines_dest,
                    kind='LINE'
                )

            else:
                src_global_data = maplus_geom.get_modified_global_coords(
                    geometry=prims[active_item.aln_src_line],
                    kind='LINE'
                )
                dest_global_data = maplus_geom.get_modified_global_coords(
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

            if self.target in {'OBJECT', 'OBJECT_ORIGIN'}:
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
                    bpy.context.view_layer.update()

                    # put the original line starting point (before the object
                    # was rotated) into the local object space
                    src_pivot_location_local = unaltered_inverse @ src_start

                    # get final global position of pivot (source line
                    # start coords) after object rotation
                    new_global_src_pivot_coords = (
                        item.matrix_world @
                        src_pivot_location_local
                    )
                    # get translation, pivot to dest
                    pivot_to_dest = (
                        dest_start - new_global_src_pivot_coords
                    )

                    item.location = (
                        item.location + pivot_to_dest
                    )
                    bpy.context.view_layer.update()

            if self.target in {'MESH_SELECTED', 'WHOLE_MESH', 'OBJECT_ORIGIN'}:
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
                    src_start_loc = unaltered_inverse_loc @ src_start
                    src_end_loc = unaltered_inverse_loc @ src_end

                    dest_start_loc = unaltered_inverse_loc @ dest_start
                    dest_end_loc = unaltered_inverse_loc @ dest_end

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
                        pivot_to_dest_loc @
                        parallelize_lines_loc @
                        src_pivot_to_loc_origin
                    )

                    if self.target == 'MESH_SELECTED':
                        src_mesh.transform(
                            loc_make_collinear,
                            filter={'SELECT'}
                        )
                    elif self.target == 'WHOLE_MESH':
                        src_mesh.transform(loc_make_collinear)
                    elif self.target == 'OBJECT_ORIGIN':
                        # Note: a target of 'OBJECT_ORIGIN' is equivalent
                        # to performing an object transf. + an inverse
                        # whole mesh level transf. To the user,
                        # the object appears to stay in the same place,
                        # while only the object's origin moves.
                        src_mesh.transform(loc_make_collinear.inverted())

                    bpy.ops.object.mode_set(mode='OBJECT')
                    src_mesh.to_mesh(item.data)
                    src_mesh.free()

            # Go back to whatever mode we were in before doing this
            bpy.ops.object.mode_set(mode=previous_mode)

        else:
            # The selected Blender objects are not compatible with the
            # requested transformation type (we can't apply a transform
            # to mesh data when there are non-mesh objects selected)
            self.report(
                {'ERROR'},
                ('Cannot complete: Cannot apply mesh-level'
                 ' transformations to selected non-mesh objects.')
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class MAPLUS_OT_AlignLinesObject(MAPLUS_OT_AlignLinesBase):
    bl_idname = "maplus.alignlinesobject"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'


class MAPLUS_OT_QuickAlignLinesObject(MAPLUS_OT_AlignLinesBase):
    bl_idname = "maplus.quickalignlinesobject"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT'
    quick_op_target = True


class MAPLUS_OT_QuickAlignLinesObjectOrigin(MAPLUS_OT_AlignLinesBase):
    bl_idname = "maplus.quickalignlinesobjectorigin"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'OBJECT_ORIGIN'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class MAPLUS_OT_AlignLinesMeshSelected(MAPLUS_OT_AlignLinesBase):
    bl_idname = "maplus.alignlinesmeshselected"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESH_SELECTED'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class MAPLUS_OT_AlignLinesWholeMesh(MAPLUS_OT_AlignLinesBase):
    bl_idname = "maplus.alignlineswholemesh"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLE_MESH'

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class MAPLUS_OT_QuickAlignLinesMeshSelected(MAPLUS_OT_AlignLinesBase):
    bl_idname = "maplus.quickalignlinesmeshselected"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'MESH_SELECTED'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class MAPLUS_OT_QuickAlignLinesWholeMesh(MAPLUS_OT_AlignLinesBase):
    bl_idname = "maplus.quickalignlineswholemesh"
    bl_label = "Align Lines"
    bl_description = "Makes lines collinear (in line with each other)"
    bl_options = {'REGISTER', 'UNDO'}
    target = 'WHOLE_MESH'
    quick_op_target = True

    @classmethod
    def poll(cls, context):
        addon_data = bpy.context.scene.maplus_data
        if not addon_data.use_experimental:
            return False
        return True


class MAPLUS_OT_ClearEasyAlignLines(bpy.types.Operator):
    bl_idname = "maplus.cleareasyalignlines"
    bl_label = "Reset Easy Align Lines"
    bl_description = "Clear/Restart Easy Align Lines"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Set the Easy Align Lines operator back to stage one, reset data"""
        addon_data = bpy.context.scene.maplus_data
        addon_data.easy_aln_is_first_press = True
        addon_data.easy_aln_designated_objects.clear()

        maplus_geom.set_item_coords(
            addon_data.easy_align_lines_src,
            ('line_start', 'line_end'),
            [[0, 0, 0], [0, 0, 0]],
        )
        maplus_geom.set_item_coords(
            addon_data.easy_align_lines_dest,
            ('line_start', 'line_end'),
            [[0, 0, 0], [0, 0, 0]],
        )

        return {'FINISHED'}


class MAPLUS_OT_EasyAlignLines(bpy.types.Operator):
    bl_idname = "maplus.easyalignlines"
    bl_label = "Easy Align Lines"
    bl_description = (
        # TODO fix
        "Easy two-stage"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """TODO fix"""
        addon_data = bpy.context.scene.maplus_data
        previous_mode = maplus_geom.get_active_object().mode
        # Get valid objects from the target list
        valid_targets = [
            item
            for item in addon_data.easy_aln_designated_objects
                if item.val_str in bpy.context.scene.objects
        ]
        multi_edit_targets = [bpy.context.scene.objects[name.val_str] for name in valid_targets]
        # Check prerequisites for mesh level transforms, need an active/selected object
        if (addon_data.easy_aln_transf_type != 'OBJECT'
                and not (maplus_geom.get_active_object()
                         and maplus_geom.get_select_state(maplus_geom.get_active_object()))):
            self.report(
                {'ERROR'},
                ('Cannot complete: cannot perform mesh-level transform'
                 ' without an active (and selected) object.')
            )
            return {'CANCELLED'}
        # Easy mode MUST auto-grab on first and second click: check auto grab prerequisites
        if not (maplus_geom.get_active_object()
                and maplus_geom.get_select_state(maplus_geom.get_active_object())):
            self.report(
                {'ERROR'},
                ('Cannot complete: cannot auto-grab vert data'
                 ' without an active (and selected) object.')
            )
            return {'CANCELLED'}
        if maplus_geom.get_active_object().type != 'MESH':
            self.report(
                {'ERROR'},
                ('Cannot complete: cannot auto-grab vert data'
                 ' from a non-mesh object.')
            )
            return {'CANCELLED'}

        # Proceed only if selected Blender objects are compatible with the transform target
        # (Do not allow mesh-level transforms when there are non-mesh objects selected)
        if not (addon_data.easy_aln_transf_type in {'WHOLE_MESH'}
                and [item for item in multi_edit_targets if item.type != 'MESH']):

            # Make sure we're in edit mode with no stale data for proper vert-grabbing
            if maplus_geom.get_active_object().type == 'MESH':
                # a bmesh can only be initialized in edit mode...
                if previous_mode != 'EDIT':
                    bpy.ops.object.editmode_toggle()
                else:
                    # else we could already be in edit mode with some stale
                    # updates, exiting and reentering forces an update
                    bpy.ops.object.editmode_toggle()
                    bpy.ops.object.editmode_toggle()

            # Stage one (first-press) behavior
            if addon_data.easy_aln_is_first_press:

                # Auto-grab the SOURCE key from selected verts on the active obj
                vert_attribs_to_set = (
                    'line_start',
                    'line_end'
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

                # Store the obtained vert data
                maplus_geom.set_item_coords(
                    addon_data.easy_align_lines_src,
                    vert_attribs_to_set,
                    vert_data
                )

                # Go back to whatever mode we were in before doing this
                bpy.ops.object.mode_set(mode=previous_mode)

                # Get/store the objects selected during the first press, these
                # are used later during stage two, where the alignment will be run
                # against all of these objects
                selected = [
                    item
                    for item in bpy.context.scene.objects if maplus_geom.get_select_state(item)
                ]
                target_list = addon_data.easy_aln_designated_objects
                target_list.clear()
                for item in selected:
                    target_list_item = target_list.add()
                    target_list_item.val_str = item.name

                # Stage one has finished, set the flag to indicate that the
                # next run will follow stage-two behavior
                addon_data.easy_aln_is_first_press = False

                return {'FINISHED'}

            # Stage two (second-press) behavior (apply the alignment)
            else:

                # Auto-grab the DESTINATION key from selected verts on the active obj
                vert_attribs_to_set = (
                    'line_start',
                    'line_end'
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

                # Store the obtained vert data
                maplus_geom.set_item_coords(
                    addon_data.easy_align_lines_dest,
                    vert_attribs_to_set,
                    vert_data
                )

                src_global_data = maplus_geom.get_modified_global_coords(
                    geometry=addon_data.easy_align_lines_src,
                    kind='LINE'
                )
                dest_global_data = maplus_geom.get_modified_global_coords(
                    geometry=addon_data.easy_align_lines_dest,
                    kind='LINE'
                )

                # These global point coordinate vectors will be used to construct
                # geometry and transformations in both object (global) space
                # and mesh (local) space
                src_start = src_global_data[0]
                src_end = src_global_data[1]

                dest_start = dest_global_data[0]
                dest_end = dest_global_data[1]

                if addon_data.easy_aln_transf_type in {'OBJECT'}:
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
                        if addon_data.easy_aln_transform_settings.aln_flip_direction:
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
                        bpy.context.view_layer.update()

                        # put the original line starting point (before the object
                        # was rotated) into the local object space
                        src_pivot_location_local = unaltered_inverse @ src_start

                        # get final global position of pivot (source line
                        # start coords) after object rotation
                        new_global_src_pivot_coords = (
                                item.matrix_world @
                                src_pivot_location_local
                        )
                        # get translation, pivot to dest
                        pivot_to_dest = (
                                dest_start - new_global_src_pivot_coords
                        )

                        item.location = (
                                item.location + pivot_to_dest
                        )
                        bpy.context.view_layer.update()

                if addon_data.easy_aln_transf_type in {'WHOLE_MESH'}:
                    for item in multi_edit_targets:

                        # Init source mesh
                        src_mesh = bmesh.new()
                        src_mesh.from_mesh(item.data)

                        # Get the object world matrix
                        item_matrix_unaltered_loc = item.matrix_world.copy()
                        unaltered_inverse_loc = item_matrix_unaltered_loc.copy()
                        unaltered_inverse_loc.invert()

                        # Stored geom data in local coords
                        src_start_loc = unaltered_inverse_loc @ src_start
                        src_end_loc = unaltered_inverse_loc @ src_end

                        dest_start_loc = unaltered_inverse_loc @ dest_start
                        dest_end_loc = unaltered_inverse_loc @ dest_end

                        # Construct vectors for each line in local space
                        loc_src_line = src_end_loc - src_start_loc
                        loc_dest_line = dest_end_loc - dest_start_loc

                        # Take modifiers on the transformation item into account,
                        # in local (mesh) space
                        if addon_data.easy_aln_transform_settings.aln_flip_direction:
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
                                pivot_to_dest_loc @
                                parallelize_lines_loc @
                                src_pivot_to_loc_origin
                        )

                        src_mesh.transform(loc_make_collinear)

                        bpy.ops.object.mode_set(mode='OBJECT')
                        src_mesh.to_mesh(item.data)
                        src_mesh.free()

                # Clear stored source data once the transform is applied
                addon_data.easy_aln_is_first_press = True
                addon_data.easy_aln_designated_objects.clear()

            # Go back to whatever mode we were in before doing this
            bpy.ops.object.mode_set(mode=previous_mode)

        else:
            # The selected Blender objects are not compatible with the
            # requested transformation type (we can't apply a transform
            # to mesh data when there are non-mesh objects selected)
            self.report(
                {'ERROR'},
                ('Cannot complete: Cannot apply mesh-level'
                 ' transformations to selected non-mesh objects.')
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class MAPLUS_OT_ShowHideEasyAln(bpy.types.Operator):
    bl_idname = "maplus.showhideeasyaln"
    bl_label = "Show/hide easy align lines"
    bl_description = "Expands/collapses the easy align lines UI"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        addon_data.easy_aln_show = (
            not addon_data.easy_aln_show
        )

        return {'FINISHED'}


class MAPLUS_OT_ShowHideQuickAln(bpy.types.Operator):
    bl_idname = "maplus.showhidequickaln"
    bl_label = "Show/hide quick align lines"
    bl_description = "Expands/collapses the quick align lines UI"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_data = bpy.context.scene.maplus_data
        addon_data.quick_align_lines_show = (
            not addon_data.quick_align_lines_show
        )

        return {'FINISHED'}


class MAPLUS_PT_QuickAlignLinesGUI(bpy.types.Panel):
    bl_idname = "MAPLUS_PT_QuickAlignLinesGUI"
    bl_label = "Quick Align Lines"
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

        easy_aln_top = layout.row()
        if not addon_data.easy_aln_show:
            easy_aln_top.operator(
                "maplus.showhideeasyaln",
                icon='TRIA_RIGHT',
                text="",
                emboss=False
            )
        else:
            easy_aln_top.operator(
                "maplus.showhideeasyaln",
                icon='TRIA_DOWN',
                text="",
                emboss=False
            )
        easy_aln_top.label(
            text="Easy Align Lines",
            icon="SNAP_EDGE",
        )

        # If expanded, show the easy align lines GUI
        if addon_data.easy_aln_show:
            easy_aln_layout = layout.box()
            easy_aln_options = easy_aln_layout.box()
            easy_aln_options.prop(
                addon_data.easy_aln_transform_settings,
                'aln_flip_direction',
                text='Flip Direction'
            )
            transf_type_controls = easy_aln_layout.row()
            transf_type_controls.label(text='Align Mode:')
            transf_type_controls.prop(addon_data, 'easy_aln_transf_type', expand=True)
            easy_aln_controls = easy_aln_layout.row()
            if addon_data.easy_aln_is_first_press:
                easy_aln_controls.operator(
                    "maplus.easyalignlines",
                    text="Start Alignment",
                )
            else:
                easy_aln_controls.operator(
                    "maplus.easyalignlines",
                    text="Align to Active",
                )
            easy_aln_controls.operator(
                "maplus.cleareasyalignlines",
                text="",
                icon="PANEL_CLOSE",
            )
        layout.separator()

        aln_top = layout.row()
        if not addon_data.quick_align_lines_show:
            aln_top.operator(
                "maplus.showhidequickaln",
                icon='TRIA_RIGHT',
                text="",
                emboss=False
            )
        else:
            aln_top.operator(
                "maplus.showhidequickaln",
                icon='TRIA_DOWN',
                text="",
                emboss=False
            )
        aln_top.label(
            text="Align Lines (Expert)",
            icon="SNAP_EDGE",
        )

        # If expanded, show the quick align lines GUI
        if addon_data.quick_align_lines_show:

            aln_gui = layout.box()
            aln_grab_col = aln_gui.column()
            aln_grab_col.prop(
                addon_data,
                'quick_align_lines_auto_grab_src',
                text='Auto Grab Source from Selected Vertices'
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
                            icon='CURVE_PATH',
                            text="Grab Source"
                    )
                    preserve_button_roundedge.operator(
                        "maplus.quickalngrabnormalsrc",
                        icon='LIGHT_HEMI',
                        text=""
                    )
                else:
                    aln_src_geom_top.operator(
                            "maplus.showhidequickalnsrcgeom",
                            icon='TRIA_DOWN',
                            text="",
                            emboss=False
                    )
                    aln_src_geom_top.label(
                        text="Source Coordinates",
                        icon="CURVE_PATH"
                    )

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
                        icon='LIGHT_HEMI',
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
                    modifier_header.label(text="Line Modifiers:")
                    apply_mods = modifier_header.row()
                    apply_mods.alignment = 'RIGHT'

                    item_mods_box = aln_src_geom_editor.box()
                    mods_row_1 = item_mods_box.row()
                    mods_row_1.prop(
                        bpy.types.AnyType(addon_data.quick_align_lines_src),
                        'ln_make_unit_vec',
                        text="Set Length Equal to One"
                    )
                    mods_row_1.prop(
                        bpy.types.AnyType(addon_data.quick_align_lines_src),
                        'ln_flip_direction',
                        text="Flip Direction"
                    )
                    mods_row_2 = item_mods_box.row()
                    mods_row_2.prop(
                        bpy.types.AnyType(addon_data.quick_align_lines_src),
                        'ln_multiplier',
                        text="Multiplier"
                    )

                    maplus_guitools.layout_coordvec(
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

                    maplus_guitools.layout_coordvec(
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
                        icon='CURVE_PATH',
                        text="Grab Destination"
                )
                preserve_button_roundedge.operator(
                    "maplus.quickalngrabnormaldest",
                    icon='LIGHT_HEMI',
                    text=""
                )
            else:
                aln_dest_geom_top.operator(
                        "maplus.showhidequickalndestgeom",
                        icon='TRIA_DOWN',
                        text="",
                        emboss=False
                )
                aln_dest_geom_top.label(
                    text="Destination Coordinates",
                    icon="CURVE_PATH"
                )

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
                    icon='LIGHT_HEMI',
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
                modifier_header.label(text="Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = aln_dest_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_align_lines_dest),
                    'ln_make_unit_vec',
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_align_lines_dest),
                    'ln_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_align_lines_dest),
                    'ln_multiplier',
                    text="Multiplier"
                )

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

            aln_gui.label(text="Operator settings:", icon="PREFERENCES")
            aln_mods = aln_gui.box()
            aln_mods_row1 = aln_mods.row()
            aln_mods_row1.prop(
                addon_data.quick_align_lines_transf,
                'aln_flip_direction',
                text='Flip Direction'
            )
            aln_apply_header = aln_gui.row()
            aln_apply_header.label(text="Apply to:")
            aln_apply_header.prop(
                addon_data,
                'use_experimental',
                text='Enable Experimental Mesh Ops.'
            )
            aln_apply_items = aln_gui.row()
            aln_to_object_and_origin = aln_apply_items.column()
            aln_to_object_and_origin.operator(
                "maplus.quickalignlinesobject",
                text="Object"
            )
            aln_to_object_and_origin.operator(
                "maplus.quickalignlinesobjectorigin",
                text="Obj. Origin"
            )
            aln_mesh_apply_items = aln_apply_items.column(align=True)
            aln_mesh_apply_items.operator(
                "maplus.quickalignlinesmeshselected",
                text="Mesh Piece"
            )
            aln_mesh_apply_items.operator(
                "maplus.quickalignlineswholemesh",
                text="Whole Mesh"
            )
