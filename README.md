![maplus_banner_v3](https://github.com/egtwobits/mesh_mesh_align_plus/assets/104786633/16e67025-49cc-4138-b28c-85c44288d6fd)

# Mesh Align Plus [Blender Addon]

**Mesh Align Plus** helps you move things around, precisely: arrange objects in your scene, align mesh parts to each other while you're modeling, and create complex custom transformations using measurements from your models. You pick surface features that you want to align, and the addon moves your geometry according to your specifications.

Mesh Align Plus can **move objects** and leave the underlying mesh data unmodified, or it can **move mesh fragments** inside a mesh during the modeling process. You can also use measurements from your scene like angle differences, lengths, average positions, normals and other imaginary geometry like an implicit axis, projected points of intersection, etc.

Mesh Align Plus is designed to provide precision modeling capabilities, especially for hard surface modelers, mechanical, architectural and CAD/CAM users. See the simple demo clips below for a general sense of what the addon can do, read the <a href="https://github.com/egtwobits/mesh_mesh_align_plus/wiki">Wiki</a> above (with tons of GIF's), or watch the video tutorials on <a href="https://www.youtube.com/watch?v=2wkWo512mew">YouTube</a>.

[![Youtube Video Mesh Align Plus 1.0](https://i.postimg.cc/43wjMKYL/video-thumb-1.png)](https://www.youtube.com/watch?v=2wkWo512mew)

## Quick Examples

![easy_apl_frontpage2](https://user-images.githubusercontent.com/15041801/231297281-8ac7eca9-74a1-4e25-817c-ed612c0dc317.gif)
![basics](https://user-images.githubusercontent.com/15041801/231297300-6877026b-0da3-4586-b259-9b5a99829c0e.gif)
![meshops_demo3](https://github.com/egtwobits/mesh_mesh_align_plus/assets/15041801/82985eb8-0389-427f-8bad-70a38d30a541)

# Installation

Mesh Align Plus should only be installed from the `mesh_mesh_align_plus.zip` files found on the [releases page](https://github.com/egtwobits/mesh_mesh_align_plus/releases), attached to the end of each release announcement (don't zip and download the repo). These zip files are specifically formatted to work with Blender's addon system.

Once you have the right file, use Blender's addon installation feature to load it (`Edit` > `Preferences` > `Addons` > `Install`), and check the checkbox next to the addon name to enable and use it.

Open the sidebar (N) in the 3D View, go to the "Align" tab, and you will find panels for all the Mesh Align Plus tools (each panel name has `(MAPlus)` at the end):

![The addon tab in the 3D View](https://user-images.githubusercontent.com/15041801/231289939-af304ee9-40e8-4143-bcbf-0b6c84ad6738.png)

# Basic Usage

*Note: See the [wiki (above)](https://github.com/egtwobits/mesh_mesh_align_plus/wiki) for more in-depth tutorials and reference info*

![panelinfo2](https://user-images.githubusercontent.com/15041801/231296982-6c4c8367-c67d-4e28-a9c6-7d5cfe18b95d.png)

Mesh Align Plus has both **Easy Mode** tools, and **Expert Mode** tools. **Easy Mode** provides the fastest, easiest workflows for common use cases, and as such should suit most people's needs most of the time. **Expert mode** is available for especially complex cases, and for those who need more options, flexibility and control over their transformations.

In both cases, Mesh Align Plus tools will operate on surface features that you pick. Even though there are several tools and multiple workflows available, you always need some kind of alignment key(s), and a target (the thing(s) you want to move). Typical workflows usually look something ROUGHLY like this:

- Pick a surface feature by selecting some geometry as an alignment key (the source key) and hit grab
- Pick another surface feature by selecting some other geometry (the destination key) and hit grab
- Select some object(s) or mesh fragments to apply the motion to and hit apply

![usage_diagram7a](https://user-images.githubusercontent.com/15041801/231576070-e052b92e-937d-4a7f-a117-7e13df262d99.png)

Here's what aligning faces looks like with **easy mode:**

- Select three verts on an object you want to move and hit "Start Alignment" to designate the **source key**
- Select another three verts (same object, different object, whatever) and hit "Apply to Active" to designate a **destination key** and auto-align your source object from the first step (the **target**)

![easy_apl_simple2](https://user-images.githubusercontent.com/15041801/232251537-ace16b1a-a10f-473a-a2f8-98be9e2249ff.gif)

So, easy mode is faster and takes out some steps, but also isn't as flexible (the same basic ingredients pictured above are still captured though).

With expert mode, the source key, destination key, and target can be defined independently. The source and dest keys have alternate grab modes (average vertex position, grab normals for lines, etc.), and can use geometry from many objects. The target can also be completely independent of the source key, and there are additional target types beyond just objects (mesh piece, object origin, etc.).

### Why would I need that?

For simple cases, you don't! Just use easy mode. But for more complex cases, the extra flexibility given by expert mode is essential. For example:

- You want to center an object along an axis (an invisible/imaginary location)
- You want to align related components so that feature A aligns to feature B, but want to maintain that object's position relative to its friends
- You want to move a feature some percentage of the way between two points (or two imaginary locations)

So, Mesh Align Plus does alignments, but more generally it is a precision modeling tool that can help you ARRANGE objects or mesh fragments in your scenes, often by exploiting measurements and locations implicit in your scene's geometry.
