"""Calculate and Compose tool, internals & UI."""


import math

import bpy
import mathutils

import mesh_mesh_align_plus.utils.geom as maplus_geom
import mesh_mesh_align_plus.utils.storage as maplus_storage
import mesh_mesh_align_plus.utils.gui_tools as maplus_guitools


class MAPLUS_OT_CalcLineLengthBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and calc_target_item.kind != 'LINE'):
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

        src_global_data = maplus_geom.get_modified_global_coords(
            geometry=calc_target_item,
            kind='LINE'
        )
        src_line = src_global_data[1] - src_global_data[0]
        result = src_line.length
        setattr(active_calculation, result_attrib, result)
        if addon_data.calc_result_to_clipboard:
            bpy.context.window_manager.clipboard = str(result)

        return {'FINISHED'}


class MAPLUS_OT_CalcLineLength(MAPLUS_OT_CalcLineLengthBase):
    bl_idname = "maplus.calclinelength"
    bl_label = "Calculate Line Length"
    bl_description = "Calculates the length of the targeted line item"
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickCalcLineLength(MAPLUS_OT_CalcLineLengthBase):
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


class MAPLUS_OT_CalcRotationalDiffBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and not (calc_target_one.kind == 'LINE'
                and calc_target_two.kind == 'LINE')):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Calculate Rotational Difference" can'
                 ' only operate on two lines')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if (calc_target_one.kind != 'LINE'
                    or calc_target_two.kind != 'LINE'):
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Line").')
                )

        src_global_data = maplus_geom.get_modified_global_coords(
            geometry=calc_target_one,
            kind='LINE'
        )
        dest_global_data = maplus_geom.get_modified_global_coords(
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


class MAPLUS_OT_CalcRotationalDiff(MAPLUS_OT_CalcRotationalDiffBase):
    bl_idname = "maplus.calcrotationaldiff"
    bl_label = "Angle of Lines"
    bl_description = (
        "Calculates the rotational difference between line items"
    )
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickCalcRotationalDiff(MAPLUS_OT_CalcRotationalDiffBase):
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


class MAPLUS_OT_ComposeNewLineFromOriginBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and calc_target_item.kind != 'LINE'):
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
        src_global_data = maplus_geom.get_modified_global_coords(
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
            maplus_storage.copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class MAPLUS_OT_ComposeNewLineFromOrigin(MAPLUS_OT_ComposeNewLineFromOriginBase):
    bl_idname = "maplus.composenewlinefromorigin"
    bl_label = "New Line from Origin"
    bl_description = "Composes a new line item starting at the world origin"
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickComposeNewLineFromOrigin(MAPLUS_OT_ComposeNewLineFromOriginBase):
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


class MAPLUS_OT_ComposeNormalFromPlaneBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and not calc_target_item.kind == 'PLANE'):
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

        src_global_data = maplus_geom.get_modified_global_coords(
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
            maplus_storage.copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class MAPLUS_OT_ComposeNormalFromPlane(MAPLUS_OT_ComposeNormalFromPlaneBase):
    bl_idname = "maplus.composenormalfromplane"
    bl_label = "Get Plane Normal"
    bl_description = "Get the plane's normal as a new line item"
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickComposeNormalFromPlane(MAPLUS_OT_ComposeNormalFromPlaneBase):
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


class MAPLUS_OT_ComposeNewLineFromPointBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and calc_target_item.kind != 'POINT'):
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

        src_global_data = maplus_geom.get_modified_global_coords(
            geometry=calc_target_item,
            kind='POINT'
        )

        result_item.kind = 'LINE'
        result_item.line_start = start_loc
        result_item.line_end = src_global_data[0]
        if addon_data.calc_result_to_clipboard:
            addon_data.internal_storage_clipboard.kind = 'LINE'
            maplus_storage.copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class MAPLUS_OT_ComposeNewLineFromPoint(MAPLUS_OT_ComposeNewLineFromPointBase):
    bl_idname = "maplus.composenewlinefrompoint"
    bl_label = "New Line from Point"
    bl_description = (
        "Composes a new line item from the supplied point,"
        " starting at the world origin"
    )
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickComposeNewLineFromPoint(MAPLUS_OT_ComposeNewLineFromPointBase):
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


class MAPLUS_OT_ComposeNewLineAtPointLocationBase(bpy.types.Operator):
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

        pt_global_data = maplus_geom.get_modified_global_coords(
            geometry=targets_by_kind['POINT'],
            kind='POINT'
        )
        line_global_data = maplus_geom.get_modified_global_coords(
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
            maplus_storage.copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class MAPLUS_OT_ComposeNewLineAtPointLocation(MAPLUS_OT_ComposeNewLineAtPointLocationBase):
    bl_idname = "maplus.composenewlineatpointlocation"
    bl_label = "New Line at Point Location"
    bl_description = "Composes a new line item starting at the point location"
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickComposeNewLineAtPointLocation(MAPLUS_OT_ComposeNewLineAtPointLocationBase):
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


class MAPLUS_OT_CalcDistanceBetweenPointsBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and not (calc_target_one.kind == 'POINT'
                and calc_target_two.kind == 'POINT')):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Calculate Distance Between Points" can'
                 ' only operate on two points')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if (calc_target_one.kind != 'POINT'
                    or calc_target_two.kind != 'POINT'):
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Point").')
                )

        src_global_data = maplus_geom.get_modified_global_coords(
            geometry=calc_target_one,
            kind='POINT'
        )
        dest_global_data = maplus_geom.get_modified_global_coords(
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


class MAPLUS_OT_CalcDistanceBetweenPoints(MAPLUS_OT_CalcDistanceBetweenPointsBase):
    bl_idname = "maplus.calcdistancebetweenpoints"
    bl_label = "Distance Between Points"
    bl_description = "Calculate the distance between provided point items"
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickCalcDistanceBetweenPoints(MAPLUS_OT_CalcDistanceBetweenPointsBase):
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


class MAPLUS_OT_ComposeNewLineFromPointsBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and not (calc_target_one.kind == 'POINT'
                and calc_target_two.kind == 'POINT')):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Compose New Line from Points" can'
                 ' only operate on two points')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if (calc_target_one.kind != 'POINT'
                    or calc_target_two.kind != 'POINT'):
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Point").')
                )

        src_global_data = maplus_geom.get_modified_global_coords(
            geometry=calc_target_one,
            kind='POINT'
        )
        dest_global_data = maplus_geom.get_modified_global_coords(
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
            maplus_storage.copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class MAPLUS_OT_ComposeNewLineFromPoints(MAPLUS_OT_ComposeNewLineFromPointsBase):
    bl_idname = "maplus.composenewlinefrompoints"
    bl_label = "New Line from Points"
    bl_description = "Composes a new line item from provided point items"
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickComposeNewLineFromPoints(MAPLUS_OT_ComposeNewLineFromPointsBase):
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


class MAPLUS_OT_ComposeNewLineVectorAdditionBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and not (calc_target_one.kind == 'LINE'
                and calc_target_two.kind == 'LINE')):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Add Lines" can only operate on'
                 ' two lines')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if (calc_target_one.kind != 'LINE'
                    or calc_target_two.kind != 'LINE'):
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Line").')
                )

        start_loc = mathutils.Vector((0, 0, 0))

        src_global_data = maplus_geom.get_modified_global_coords(
            geometry=calc_target_one,
            kind='LINE'
        )
        dest_global_data = maplus_geom.get_modified_global_coords(
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
            maplus_storage.copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class MAPLUS_OT_ComposeNewLineVectorAddition(MAPLUS_OT_ComposeNewLineVectorAdditionBase):
    bl_idname = "maplus.composenewlinevectoraddition"
    bl_label = "Add Lines"
    bl_description = "Composes a new line item by vector-adding provided lines"
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickComposeNewLineVectorAddition(MAPLUS_OT_ComposeNewLineVectorAdditionBase):
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


class MAPLUS_OT_ComposeNewLineVectorSubtractionBase(bpy.types.Operator):
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

        if ((not hasattr(self, 'quick_calc_target'))
                and not (calc_target_one.kind == 'LINE'
                and calc_target_two.kind == 'LINE')):
            self.report(
                {'ERROR'},
                ('Wrong operand: "Add Lines" can only operate on'
                 ' two lines')
            )
            return {'CANCELLED'}
        if hasattr(self, 'quick_calc_target'):
            if (calc_target_one.kind != 'LINE'
                    or calc_target_two.kind != 'LINE'):
                self.report(
                    {'WARNING'},
                    ('Operand type warning: Slot 1 and/or Slot 2 are not'
                     ' explicitly using the correct types for this'
                     ' calculation (item type for both should be'
                     ' set to "Line").')
                )

        start_loc = mathutils.Vector((0, 0, 0))

        src_global_data = maplus_geom.get_modified_global_coords(
            geometry=calc_target_one,
            kind='LINE'
        )
        dest_global_data = maplus_geom.get_modified_global_coords(
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
            maplus_storage.copy_source_attribs_to_dest(
                result_item,
                addon_data.internal_storage_clipboard,
                ("line_start",
                 "line_end",
                 "ln_make_unit_vec",
                 "ln_flip_direction",
                 "ln_multiplier")
            )

        return {'FINISHED'}


class MAPLUS_OT_ComposeNewLineVectorSubtraction(MAPLUS_OT_ComposeNewLineVectorSubtractionBase):
    bl_idname = "maplus.composenewlinevectorsubtraction"
    bl_label = "Subtract Lines"
    bl_description = (
        "Composes a new line item by performing vector-subtraction"
        " (first line minus second line)"
    )
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickComposeNewLineVectorSubtraction(MAPLUS_OT_ComposeNewLineVectorSubtractionBase):
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


class MAPLUS_OT_ComposePointIntersectingLinePlaneBase(bpy.types.Operator):
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

        line_global_data = maplus_geom.get_modified_global_coords(
            geometry=targets_by_kind['LINE'],
            kind='LINE'
        )
        plane_global_data = maplus_geom.get_modified_global_coords(
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
                maplus_storage.copy_source_attribs_to_dest(
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


class MAPLUS_OT_ComposePointIntersectingLinePlane(MAPLUS_OT_ComposePointIntersectingLinePlaneBase):
    bl_idname = "maplus.composepointintersectinglineplane"
    bl_label = "Intersect Line/Plane"
    bl_description = (
        "Composes a new point item by intersecting a line and a plane"
    )
    bl_options = {'REGISTER', 'UNDO'}


class MAPLUS_OT_QuickComposePointIntersectingLinePlane(MAPLUS_OT_ComposePointIntersectingLinePlaneBase):
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


class MAPLUS_PT_CalculateAndComposeGUI(bpy.types.Panel):
    bl_idname = "MAPLUS_PT_CalculateAndComposeGUI"
    bl_label = "Calculate and Compose"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mesh Align Plus"
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
            slot1_geom_top.label(text="Slot 1 Coordinates")
            slot1_geom_editor = calc_gui.box()
            types_row = slot1_geom_editor.row()
            types_row.label(text="Item type:")
            types_row.prop(
                bpy.types.AnyType(addon_data.internal_storage_slot_1),
                'kind',
                text=""
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
                modifier_header.label(text="Point Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = slot1_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'pt_make_unit_vec',
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'pt_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'pt_multiplier',
                    text="Multiplier"
                )

                maplus_guitools.layout_coordvec(
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
                    icon='LIGHT_HEMI',
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
                modifier_header.label(text="Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'

                item_mods_box = slot1_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'ln_make_unit_vec',
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'ln_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_1),
                    'ln_multiplier',
                    text="Multiplier"
                )

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
                    parent_layout=slot1_geom_editor,
                    coordvec_label="Pt. B:",
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

                maplus_guitools.layout_coordvec(
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
            slot2_geom_top.label(text="Slot 2 Coordinates")
            slot2_geom_editor = calc_gui.box()
            types_row = slot2_geom_editor.row()
            types_row.label(text="Item type:")
            types_row.prop(
                bpy.types.AnyType(addon_data.internal_storage_slot_2),
                'kind',
                text=""
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
                modifier_header.label(text="Point Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                item_mods_box = slot2_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'pt_make_unit_vec',
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'pt_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'pt_multiplier',
                    text="Multiplier"
                )

                maplus_guitools.layout_coordvec(
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
                    icon='LIGHT_HEMI',
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
                modifier_header.label(text="Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                item_mods_box = slot2_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'ln_make_unit_vec',
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'ln_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.internal_storage_slot_2),
                    'ln_multiplier',
                    text="Multiplier"
                )

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
                    parent_layout=slot2_geom_editor,
                    coordvec_label="Pt. B:",
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

                maplus_guitools.layout_coordvec(
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
        calcs_and_results_header.label(text=
            "Result:"
        )
        clipboard_row_right = calcs_and_results_header.row()
        clipboard_row_right.alignment = 'RIGHT'
        clipboard_row_right.prop(
            bpy.types.AnyType(maplus_data_ptr),
            'calc_result_to_clipboard',
            text="Copy to Clipboard"
        )
        calc_gui.prop(
            bpy.types.AnyType(bpy.types.AnyType(addon_data)),
            'quick_calc_result_numeric',
            text=""
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
            result_geom_top.label(text="Calc. Result Coordinates")
            calcresult_geom_editor = calc_gui.box()
            types_row = calcresult_geom_editor.row()
            types_row.label(text="Item type:")
            types_row.prop(
                bpy.types.AnyType(addon_data.quick_calc_result_item),
                'kind',
                text=""
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
                modifier_header.label(text="Point Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                item_mods_box = calcresult_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'pt_make_unit_vec',
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'pt_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'pt_multiplier',
                    text="Multiplier"
                )

                maplus_guitools.layout_coordvec(
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
                    icon='LIGHT_HEMI',
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
                modifier_header.label(text="Line Modifiers:")
                apply_mods = modifier_header.row()
                apply_mods.alignment = 'RIGHT'
                item_mods_box = calcresult_geom_editor.box()
                mods_row_1 = item_mods_box.row()
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'ln_make_unit_vec',
                    text="Set Length Equal to One"
                )
                mods_row_1.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'ln_flip_direction',
                    text="Flip Direction"
                )
                mods_row_2 = item_mods_box.row()
                mods_row_2.prop(
                    bpy.types.AnyType(addon_data.quick_calc_result_item),
                    'ln_multiplier',
                    text="Multiplier"
                )

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
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

                maplus_guitools.layout_coordvec(
                    parent_layout=calcresult_geom_editor,
                    coordvec_label="Pt. B:",
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

                maplus_guitools.layout_coordvec(
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
        ops_header.label(text="Available Calc.'s:")
        ops_header.prop(
            bpy.types.AnyType(addon_data),
            'quick_calc_check_types',
            text="Check/Verify Types"
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
            icon='LIGHT_SUN',
            text="New Line from Origin"
        )
        calc_gui.operator(
            "maplus.quickcomposenormalfromplane",
            icon='LIGHT_SUN',
            text="Get Plane Normal (Normalized)"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinefrompoint",
            icon='LIGHT_SUN',
            text="New Line from Point"
        )
        calc_gui.operator(
            "maplus.quickcalcdistancebetweenpoints",
            text="Distance Between Points"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlineatpointlocation",
            icon='LIGHT_SUN',
            text="New Line at Point"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinefrompoints",
            icon='LIGHT_SUN',
            text="New Line from Points"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinevectoraddition",
            icon='LIGHT_SUN',
            text="Add Lines"
        )
        calc_gui.operator(
            "maplus.quickcomposenewlinevectorsubtraction",
            icon='LIGHT_SUN',
            text="Subtract Lines"
        )
        calc_gui.operator(
            "maplus.quickcomposepointintersectinglineplane",
            icon='LAYER_ACTIVE',
            text="Intersect Line/Plane"
        )
