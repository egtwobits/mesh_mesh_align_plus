"""This module holds required Blender addon info/utility calls."""
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


import mesh_mesh_align_plus.utils.system as maplus_sys


# Blender requires addons to provide this information.
bl_info = {
    "name": "Mesh Align Plus",
    "description": (
        "Precisely move mesh parts and objects around "
        "based on geometry and measurements from your scene."
    ),
    "author": "Eric Gentry",
    "version": (0, 5, 3),
    "blender": (2, 80, 0),
    "location": (
        "3D View > N Panel > Mesh Align Plus tab, and"
        " Properties -> Scene -> Mesh Align Plus"
    ),
    "warning": (
        "Operations on objects with non-uniform scaling are "
        "not currently supported."
    ),
    "wiki_url": (
        "https://github.com/egtwobits/mesh_mesh_align_plus/wiki"
    ),
    "support": "COMMUNITY",
    "category": "Mesh"
}


register = maplus_sys.register
unregister = maplus_sys.unregister


if __name__ == "__main__":
    maplus_sys.register()
