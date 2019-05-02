"""Layout and interface utilities."""


import bpy


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
    coordvec_container.label(text=coordvec_label)
    type_or_grab_coords = coordvec_container.column()

    grab_buttons = type_or_grab_coords.row(align=True)
    grab_buttons.label(text="Grab:")
    grab_buttons.operator(
        op_id_cursor_grab,
        icon='PIVOT_CURSOR',
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
        text=""
    )

    coordvec_lowers = type_or_grab_coords.row()

    if op_id_text_tuple_swap_first:
        coordvec_lowers.label(text="Swap:")
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

    coordvec_lowers.label(text="Send:")
    coordvec_lowers.operator(
        op_id_cursor_send,
        icon='DRIVER',
        text=""
    )


def specials_menu_items(self, context):
    self.layout.separator()
    self.layout.label(text='Add Mesh Align Plus items')
    self.layout.operator('maplus.specialsaddpointfromactiveglobal')
    self.layout.operator('maplus.specialsaddlinefromactiveglobal')
    self.layout.operator('maplus.specialsaddplanefromactiveglobal')
