# Raspbot V2 model

The URDF and seven STL meshes came from `yahboomcar_description` in the cached
`yahboomtechnology/ros-humble:0.1.0` Docker layer in [Yahboom's factory disk image](https://drive.google.com/drive/folders/1RV4pGs8N0ATYlibx3DoaTCyOxKGn9I08).
The factory `package.xml` has `TODO: License declaration` in its license field.
The package gives no model license.

## Mesh reduction

Use Trimesh 5.2.2 and [Fast Simplification](https://github.com/pyvista/fast-simplification) 0.2.0.
Load the original binary STLs with `process=False`.
Merge vertices with `digits_vertex=6`.
Remove duplicate and degenerate faces.
Split each mesh with `only_watertight=False, repair=False`.
Simplify each connected part separately with `agg=5`.

Keep 6% of the base, 22% of the pan bracket, 25% of the camera, and 8% of each wheel.
Keep 70% for base parts wider and deeper than 70 mm and taller than 20 mm.
Apply each percentage to the face count of each connected part.
Keep at least eight faces in the target.
Keep the original part if its face count is below the target or simplification leaves fewer than four faces.
Join the parts and export binary STLs.
The seven files total 3.03 MB.

## Camera joints

At zero, the CAD camera points forward along +X. This is the model pose for
hardware pan at 90° and tilt at 25°. In the URDF, positive pan rotates about
+Z toward +Y (left). Positive tilt rotates about −Y toward +Z (up).
Lab check R.16 compares these directions and the centre pose with the real camera.
