# Mesh Align Plus [Blender Addon]

Mesh Align Plus helps you place geometry precisely where it needs to go in your scene. You pick surface features that you want to align, and the addon moves your geometry according to your specifications.

Mesh Align Plus can move objects and leave the underlying mesh data unmodified, or it can move mesh fragments during the modeling process. You can also use measurements from your scene like angle differences, lengths, average positions, normals and other imaginary geometry like an implicit axis, projected points of intersection, etc.

Mesh Align Plus is designed to provide precision modeling capabilities, especially for hard surface modelers, mechanical, architectural and CAD/CAM users. See the simple demo clips below for a general sense of what the addon can do, read the <a href="https://github.com/egtwobits/mesh_mesh_align_plus/wiki">Wiki</a> above (with tons of GIF's), or watch the video tutorials on <a href="https://youtu.be/VBoic2MIC8U">YouTube</a>.

## Quick Examples

![alt](https://i.imgur.com/r6eBnKN.gif)
![alt](https://i.postimg.cc/4yhvz7x2/face-align-4.gif)
![alt](http://i.imgur.com/JOa7Fcd.gif)
![alt](https://i.imgur.com/dtXq2aX.gif)

# Installation

Mesh Align Plus should only be installed from the `mesh_mesh_align_plus.zip` files found on the [releases page](https://github.com/egtwobits/mesh_mesh_align_plus/releases), attached to the end of each post (don't zip and download the repo). These zip files are specifically formatted to work with Blender's addon system.

Once you have the right file, use Blender's addon installation feature to load it (`Edit` > `Preferences` > `Addons` > `Install`), and check the checkbox next to the addon name to enable and use it.

Open the sidebar (N) in the 3D View, go to the "Align" tab, and you will find panels for all the Mesh Align Plus tools (each panel name has `(MAPlus)` at the end).

![The addon tab in the 3D View](https://user-images.githubusercontent.com/15041801/231289939-af304ee9-40e8-4143-bcbf-0b6c84ad6738.png)

# Basic Usage

*Note: See the [wiki (above)](https://github.com/egtwobits/mesh_mesh_align_plus/wiki) for more in-depth tutorials and reference info*

Mesh Align Plus has both **Easy Mode** tools, and **Expert Mode** tools. **Easy Mode** provides the fastest, easiest workflows for common use cases, and as such should suit most people's needs most of the time. **Expert mode** is available for especially complex cases, and for who need more options, flexibility and control over their transformations.

In both cases, Mesh Align Plus tools will operate on surface features that you pick.
