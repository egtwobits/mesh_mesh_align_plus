"""Distribute Objects tool, internals & UI."""


import bpy
import mathutils

import mesh_mesh_align_plus.utils.geom as maplus_geom
import mesh_mesh_align_plus.utils.gui_tools as maplus_guitools


class MAPLUS_OT_QuickDistributeObjectsBetween(bpy.types.Operator):
    bl_idname = "maplus.quickdistributeobjectsbetween"
    bl_label = "Distribute Objects"
    bl_description = "Distribute Objects Between Start and End Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """User picks a start object and end object, then we align all
        selected objects between the start object's location and the end
        object's location, ordered by distance from the start object in
        the direction of the end object"""
        addon_data = bpy.context.scene.maplus_data

        start_obj_name = addon_data.quick_dist_obj_bet_start
        end_obj_name = addon_data.quick_dist_obj_bet_end
        # The user picked a start object and we stored a name,
        # make sure an object with that name still exists
        if start_obj_name not in bpy.data.objects:
            self.report(
                {'ERROR'},
                f'Cannot complete: Start object "{start_obj_name}" does not exist'
            )
            return {'CANCELLED'}
        # The user picked an end object and we stored a name,
        # make sure an object with that name still exists
        if end_obj_name not in bpy.data.objects:
            self.report(
                {'ERROR'},
                f'Cannot complete: End object "{end_obj_name}" does not exist'
            )
            return {'CANCELLED'}
        start_object = bpy.data.objects[start_obj_name]
        end_object = bpy.data.objects[end_obj_name]
        start_location = start_object.location
        end_location = end_object.location

        # Apply distribute-between to the selected objects
        selected = [
            item
            for item in bpy.context.scene.objects if maplus_geom.get_select_state(item)
        ]
        sort_func = lambda item: maplus_geom.pt_distance_in_direction(
            start_location,
            end_location,
            item.location
        )
        selected.sort(key=sort_func)

        total_gaps = len(selected) - (1 if len(selected) > 1 else 0)
        span = end_location - start_location
        start_index = 0

        if addon_data.quick_dist_obj_bet_offset_start:
            start_index += 1
            total_gaps += 1 if len(selected) > 1 else 0

            # #### OLD ####
            # # If user offsets from start, first item gets shifted 1 space
            # index_modifier = 1
            # total_gaps_between_items += 1
            # # TODO: Generalize this to offset by n spaces by multiplying by n
        if addon_data.quick_dist_obj_bet_offset_end:
            total_gaps += 1

            # #### OLD ####
            # # If user offsets from end, pretend there's an extra item
            # # so the last item falls short 1 space of the end point
            # total_gaps_between_items += 1
            # # TODO: Generalize this to offset by n spaces by multiplying by n
        gap_length = span / total_gaps
        if len(selected) >= 1:

            for index, item in enumerate(selected):
                new_position = start_location + (gap_length * (index + start_index))
                item.location = new_position

        else:
            self.report(
                {'ERROR'},
                'Cannot complete: need at least 1 object to distribute.'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class MAPLUS_OT_QuickDistObjBetweenGrabStart(bpy.types.Operator):
    bl_idname = "maplus.quickdistobjbetweengrabstart"
    bl_label = "Grab Start"
    bl_description = "Grab the Starting Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not maplus_geom.get_active_object():
            self.report(
                {'ERROR'},
                'Cannot complete: no active object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data

        # Store the name of the start object, we grab its location
        # as the starting point of the distribute operation
        addon_data.quick_dist_obj_bet_start = maplus_geom.get_active_object().name

        return {'FINISHED'}


class MAPLUS_OT_QuickDistObjBetweenGrabEnd(bpy.types.Operator):
    bl_idname = "maplus.quickdistobjbetweengrabend"
    bl_label = "Grab End"
    bl_description = "Grab the Ending Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not maplus_geom.get_active_object():
            self.report(
                {'ERROR'},
                'Cannot complete: no active object.'
            )
            return {'CANCELLED'}
        addon_data = bpy.context.scene.maplus_data

        # Store the name of the start object, we grab its location
        # as the starting point of the distribute operation
        addon_data.quick_dist_obj_bet_end = maplus_geom.get_active_object().name

        return {'FINISHED'}


class MAPLUS_OT_QuickDistributeObjectsAlongLine(bpy.types.Operator):
    bl_idname = "maplus.quickdistributeobjectsalongline"
    bl_label = "Distribute Objects"
    bl_description = "Distribute Objects Randomly Along a Specified Line"
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
        if len(selected) >= 3:  # TODO: This is dumb, fix it

            # Get global coordinate data for each geometry item, with
            # modifiers applied.
            src_global_data = maplus_geom.get_modified_global_coords(
                geometry=addon_data.quick_dist_obj_along_line_src,
                kind='LINE'
            )
            start_location = src_global_data[0]
            end_location = src_global_data[1]
            distribute_vector = (end_location - start_location) / (len(selected) - 1)

            for index, item in enumerate(selected):
                new_position = start_location + (distribute_vector * index)
                item.location = new_position

                # current_mat = item.matrix_world
                # current_trs = [
                #     mathutils.Matrix.Translation(current_mat.decompose()[0]),
                #     current_mat.decompose()[1].to_matrix(),
                #     mathutils.Matrix.Scale(current_mat.decompose()[2][0], 4),
                # ]
                # current_trs[1].resize_4x4()
                # item.matrix_world = (
                #     active_trs[0] @
                #     active_trs[1] @
                #     current_trs[2]
                # )
        else:
            self.report(
                {'ERROR'},
                'Cannot complete: need at least 3 objects to distribute.'
            )
            return {'CANCELLED'}

        return {'FINISHED'}


class MAPLUS_PT_QuickDistributeObjectsGUI(bpy.types.Panel):
    bl_idname = "MAPLUS_PT_QuickDistributeObjectsGUI"
    bl_label = "Quick Distribute Objects"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mesh Align Plus"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        maplus_data_ptr = bpy.types.AnyType(bpy.context.scene.maplus_data)
        addon_data = bpy.context.scene.maplus_data
        prims = addon_data.prim_list

        # GUI for "Distribute Between First/Last Objects"

        dist_between_obj_top = layout.column()
        dist_between_obj_top.label(
            text="Distribute Between Start/End Objects",
            icon="NODE_INSERT_OFF",
        )
        dist_obj_between_gui = layout.box()
        dist_obj_bet_grab_start = dist_obj_between_gui.column(align=True)
        dist_obj_bet_grab_start.operator(
            "maplus.quickdistobjbetweengrabstart",
            text="Grab Start"
        )
        dist_obj_bet_grab_start.prop(
            addon_data,
            'quick_dist_obj_bet_start',
            text=""
        )
        dist_obj_bet_grab_end = dist_obj_between_gui.column(align=True)
        dist_obj_bet_grab_end.operator(
            "maplus.quickdistobjbetweengrabend",
            text="Grab End"
        )
        dist_obj_bet_grab_end.prop(
            addon_data,
            'quick_dist_obj_bet_end',
            text=""
        )
        dist_obj_between_settings_area = dist_obj_between_gui.column(align=True)
        dist_obj_between_settings_area.label(text="Operator settings:", icon="PREFERENCES")
        dist_obj_between_settings = dist_obj_between_settings_area.box()
        dist_obj_bet_offsets = dist_obj_between_settings.row()
        dist_obj_bet_offsets.prop(
            addon_data,
            'quick_dist_obj_bet_offset_start',
            text="Start Offset"
        )
        dist_obj_bet_offsets.prop(
            addon_data,
            'quick_dist_obj_bet_offset_end',
            text="End Offset"
        )
        dist_obj_between_gui.operator(
            "maplus.quickdistributeobjectsbetween",
            text="Distribute Between"
        )
        layout.separator()

        # GUI for "Distribute Objects Along Line"

        dist_obj_along_line_top = layout.row()
        dist_obj_along_line_top.label(
            text="Distribute Objects Along Line",
            icon="MOD_ARRAY",
        )
        dist_obj_along_line_gui = layout.box()

        dist_obj_along_line_grab_col = dist_obj_along_line_gui.column()
        dist_obj_along_line_geom_top = dist_obj_along_line_grab_col.row(align=True)

        # TODO: FINISH WRITING THIS, PARTS ARE INCOMPLETE/REFERENCING THE WRONG DATA/OPS

        if not addon_data.quick_dist_obj_along_line_show_src_geom:
            dist_obj_along_line_geom_top.operator(
                "maplus.showhidedistalonglinegeom",
                icon='TRIA_RIGHT',
                text="",
                emboss=False
            )
            preserve_button_roundedge = dist_obj_along_line_geom_top.row()
            preserve_button_roundedge.operator(
                "maplus.distobjalonglinegrabsrc",
                icon='CURVE_PATH',
                text="Grab Line"
            )
            preserve_button_roundedge.operator(
                "maplus.quickaxrsrcgrablinestartfromcursor",  # distobjalonglinegrabnormalsrc
                icon='LIGHT_HEMI',
                text=""
            )
        else:
            dist_obj_along_line_geom_top.operator(
                "maplus.showhidedistalonglinegeom",
                icon='TRIA_DOWN',
                text="",
                emboss=False
            )
            dist_obj_along_line_geom_top.label(
                text="Source Coordinates",
                icon="CURVE_PATH"
            )

            dist_obj_along_line_geom_editor = dist_obj_along_line_grab_col.box()
            ln_grab_all = dist_obj_along_line_geom_editor.row(align=True)
            ln_grab_all.operator(
                "maplus.distobjalonglinegrabsrcloc",
                icon='VERTEXSEL',
                text="Grab All Local"
            )
            ln_grab_all.operator(
                "maplus.distobjalonglinegrabsrc",
                icon='WORLD',
                text="Grab All Global"
            )

            modifier_header = dist_obj_along_line_geom_editor.row()
            modifier_header.label(text="Line Modifiers:")
            apply_mods = modifier_header.row()
            apply_mods.alignment = 'RIGHT'

            item_mods_box = dist_obj_along_line_geom_editor.box()
            mods_row_1 = item_mods_box.row()
            mods_row_1.prop(
                bpy.types.AnyType(addon_data.quick_dist_obj_along_line_src),
                'ln_make_unit_vec',
                text="Set Length Equal to One"
            )
            mods_row_1.prop(
                bpy.types.AnyType(addon_data.quick_dist_obj_along_line_src),
                'ln_flip_direction',
                text="Flip Direction"
            )
            mods_row_2 = item_mods_box.row()
            mods_row_2.prop(
                bpy.types.AnyType(addon_data.quick_dist_obj_along_line_src),
                'ln_multiplier',
                text="Multiplier"
            )

            maplus_guitools.layout_coordvec(
                parent_layout=dist_obj_along_line_geom_editor,
                coordvec_label="Start:",
                op_id_cursor_grab=(
                    "maplus.quickdistobjalonglinesrcgrablinestartfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quickdistobjalonglinegrabavgsrclinestart"
                ),
                op_id_local_grab=(
                    "maplus.quickdistobjalonglinesrcgrablinestartfromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quickdistobjalonglinesrcgrablinestartfromactiveglobal"
                ),
                coord_container=addon_data.quick_dist_obj_along_line_src,
                coord_attribute="line_start",
                op_id_cursor_send=(
                    "maplus.quickdistobjalonglinesrcsendlinestarttocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quickdistobjalonglinesrcswaplinepoints",
                    "End"
                )
            )

            maplus_guitools.layout_coordvec(
                parent_layout=dist_obj_along_line_geom_editor,
                coordvec_label="End:",
                op_id_cursor_grab=(
                    "maplus.quickdistobjalonglinesrcgrablineendfromcursor"
                ),
                op_id_avg_grab=(
                    "maplus.quickdistobjalonglinegrabavgsrclineend"
                ),
                op_id_local_grab=(
                    "maplus.quickdistobjalonglinesrcgrablineendfromactivelocal"
                ),
                op_id_global_grab=(
                    "maplus.quickdistobjalonglinesrcgrablineendfromactiveglobal"
                ),
                coord_container=addon_data.quick_dist_obj_along_line_src,
                coord_attribute="line_end",
                op_id_cursor_send=(
                    "maplus.quickdistobjalonglinesrcsendlineendtocursor"
                ),
                op_id_text_tuple_swap_first=(
                    "maplus.quickdistobjalonglinesrcswaplinepoints",
                    "Start"
                )
            )
            # maplus_guitools.layout_coordvec(
            #     parent_layout=dist_obj_along_line_geom_editor,
            #     coordvec_label="End:",
            #     op_id_cursor_grab=(
            #         "maplus.quickaxrsrcgrablineendfromcursor"
            #     ),
            #     op_id_avg_grab=(
            #         "maplus.quickaxrgrabavgsrclineend"
            #     ),
            #     op_id_local_grab=(
            #         "maplus.quickaxrsrcgrablineendfromactivelocal"
            #     ),
            #     op_id_global_grab=(
            #         "maplus.quickaxrsrcgrablineendfromactiveglobal"
            #     ),
            #     coord_container=addon_data.quick_dist_obj_along_line_src,
            #     coord_attribute="line_end",
            #     op_id_cursor_send=(
            #         "maplus.quickaxrsrcsendlineendtocursor"
            #     ),
            #     op_id_text_tuple_swap_first=(
            #         "maplus.quickaxrsrcswaplinepoints",
            #         "Start"
            #     )
            # )
        dist_obj_along_line_gui.operator(
            "maplus.quickdistributeobjectsalongline",
            text="Distribute Along Line"
        )
