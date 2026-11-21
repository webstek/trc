# Teapot Gallery — Checkpoint A Report & Notes

## 0. MCP Capability Check (Step 0)
Connected to **Blender 5.3.0** via `blender-mcp` (protocol v16, addon v2.0).
- **Run arbitrary Python (`execute_blender_code`):** Supported (`bpy`, `bmesh`, `mathutils`, file I/O, procedural texture generation, importers/exporters).
- **Viewport screenshot (`look`):** Supported (`viewport`, `camera`, `angles`, `frames` in `solid`, `material`, `rendered`, `wireframe`, `xray`).
- **Render image:** Supported via `look(mode="camera", shading="rendered")` and `bpy.ops.render.render(write_still=True)` (Cycles GPU OptiX and EEVEE).
- **Read/write files:** Supported both from Blender Python and workspace file tools. External asset libraries (Poly Haven, Sketchfab, etc.) and 3D generators are disabled and unused.

---

## 1. Asset Import & Mesh Inspection (Step 2)

Matched the six `.obj` files in `assets/meshes/` to the plan keys and updated `gallery_scene_plan_v1.md`:

| Key | File in `assets/meshes/` | Triangles | Vertices | Raw Bounding Box (mesh units) | Origin | Has UVs | Non-Manifold / Boundary Edges | Scaled Size (m) at `teapot_scale = 0.08` |
|---|---|---|---|---|---|---|---|---|
| `TEAPOT_CRYSTAL` | `teapot_crystal.obj` | 284 | 140 | `x: [-0.72043, 0.82324]`<br>`y: [-0.41432, 0.41956]`<br>`z: [0.0, 0.75645]` | `(0, 0, 0)` | Yes (`UVMap`) | 12 non-manifold (4 boundary) | Normalized by `3.0 / 0.75645 = 3.96589x` then `0.08x` -> `0.4898 x 0.2646 x 0.2400 m` |
| `TEAPOT_LOW` | `teapot_res2_nochamfer_nocc_flat_nointerior_outertrim_lidccap_bijective.obj` | 270 | 135 | `x: [-3.0, 3.42812]`<br>`y: [-2.0, 2.0]`<br>`z: [0.0, 3.0]` | `(0, 0, 0)` | Yes (`UVMap`) | 0 / 0 (watertight) | `0.5143 x 0.3200 x 0.2400 m` |
| `TEAPOT_CAVITY_HI` | `teapot_res48_nolid_flat_ceminterior_bijective.obj` | 225,844 | 112,920 | `x: [-3.0, 3.44502]`<br>`y: [-2.0, 2.0]`<br>`z: [0.0, 2.35053]` | `(0, 0, 0)` | Yes (`UVMap`) | 0 / 0 (watertight) | `0.5156 x 0.3200 x 0.1880 m` (body; spout tip at `0.1880 m`, rim at `0.1799 m`) |
| `TEAPOT_CAVITY_LID` | `teapot_res48_onlylid_bijective.obj` | 91,776 | 45,890 | `x: [-1.3, 1.3]`<br>`y: [-1.3, 1.3]`<br>`z: [2.325, 3.15]` | `(0, 0, 0)` | Yes (`UVMap`) | 0 / 0 (watertight) | `0.2080 x 0.2080 x 0.0660 m` (`z: [0.1860, 0.2520] m`) |
| `TEAPOT_SOLID_HI` | `teapot_res48_flat_ceminterior_bijective.obj` | 317,620 | 158,810 | `x: [-3.0, 3.44502]`<br>`y: [-2.0, 2.0]`<br>`z: [0.0, 3.0]` | `(0, 0, 0)` | Yes (`UVMap`) | 0 / 0 (watertight) | `0.5156 x 0.3200 x 0.2400 m` |
| `MELITTA` | `teapot_res48_melitta_bijective.obj` | 317,338 | 158,669 | `x: [-3.0, 3.44502]`<br>`y: [-2.0, 2.0]`<br>`z: [0.0, 4.0]` | `(0, 0, 0)` | Yes (`UVMap`) | 0 / 0 (watertight) | `0.5156 x 0.3200 x 0.3200 m` |

### Lid-to-Body Rim Gap (`TEAPOT_CAVITY_LID` vs `TEAPOT_CAVITY_HI`)
- **Body opening rim height (`r < 1.32` mesh units):** `z_max = 2.24851` mesh units (`0.17988 m` at scale `0.08`). Note: the overall `z_max = 2.35053` of `TEAPOT_CAVITY_HI` is the spout tip (`x ≈ 3.445`), not the lid opening rim.
- **Lid lowest vertex height:** `z_min = 2.32500` mesh units (`0.18600 m` at scale `0.08`), `z_max = 3.15000` mesh units (`0.25200 m`).
- **Measured vertical gap (`z_min(lid) - z_max(body_rim)`):** **`+0.07649` mesh units (`+6.12 mm` at `teapot_scale = 0.08`)**. The lid sits coaxially in place above the body opening rim at identity transform with a `6.12 mm` non-intersecting separation gap (preventing coincident dielectric interface artifacts in path tracing).

---

## 2. Derived Room Layout & On-Screen Teapot Heights (Steps 3–5)

### Derived Room Dimensions & Main Camera Framing
- **Enclosure:** `rope.clearance = 0.55 m` around a `0.70 x 0.70 m` plinth gives a `1.80 x 1.80 m` square stanchion enclosure (`rope_half = 0.90 m`).
- **Bay wall offset:** `1.00 m` from the inner wall face to each plinth center (leaving `0.10 m` clearance behind the rear stanchions).
- **Room Width (`W`, along X):** 3 back bays at `bay_spacing = 2.60 m` (`X = -2.60, 0.00, +2.60 m`), plus `0.90 m` rope half-width and `1.00 m` corner wall margin -> **`W = 9.00 m`** (`X ∈ [-4.50, +4.50] m`). Side bays sit at `X = ±3.50 m`.
- **Main Camera (`CAM_main`):** Located at `(0.00, 1.00, 1.60) m` (`wall_gap = 1.00 m` in front of the `Y = 0.00 m` front wall), focal length `20.0 mm` on a `36.0 mm` horizontal sensor -> **`HFOV = 83.97°`** (`≤ 90°`), **`VFOV = 41.58°`** at `2560 x 1080`.
- **Room Depth (`D`, along Y):** Placing the nearest side bays (`L1, R1` at `|X| = 3.50 m`) inside the central `80%` of the horizontal frame requires `d_y = (3.50 / 0.80) / tan(83.97° / 2) = 4.86 m` -> `Y_L1 = Y_R1 = 5.86 m`. Adding `bay_spacing = 2.60 m` gives `Y_L2 = Y_R2 = 8.46 m`. Adding `2 * 0.90 + 0.50 = 2.30 m` corner rope clearance gives `Y_B1..B3 = 10.76 m`, plus `1.00 m` bay wall offset -> **`D = 11.76 m`** (`Y ∈ [0.00, 11.76] m`).
- **Ceiling Height (`H`, along Z):** **`H = 3.60 m`** (`Z ∈ [0.00, 3.60] m`).

### Measured On-Screen Teapot Heights in `CAM_main` (`2560 x 1080`)

| Exhibit ID | Slot | Bay Center `(X, Y)` (m) | Mesh Used | Yaw (deg) | Teapot Height on Screen (px) | Full Exhibit Bounding Box on Screen (px) | Horizontal Frame Span (%) | Placeholder | `needs_model` |
|---|---|---|---|---|---|---|---|---|---|
| `melitta` | `L1` | `(-3.50, 5.86)` | `MELITTA` | `-25.0°` | **110.1 px** | `192.9 x 110.1 px` | `6.4% – 13.9%` | `True` | `M01` |
| `metal` | `L2` | `(-3.50, 8.46)` | `TEAPOT_CAVITY_HI` + `LID` | `-25.0°` | **54.3 px** | `121.6 x 54.3 px` | `21.7% – 26.4%` | `True` | `M03` |
| `jade` | `B1` | `(-2.60, 10.76)` | `TEAPOT_CAVITY_HI` + `LID` | `-25.0°` | **40.4 px** | `90.7 x 40.4 px` | `33.5% – 37.1%` | `False` | — |
| `stained_glass` | `B2` | `(0.00, 10.76)` | `TEAPOT_LOW` (+ thin shell) | `-25.0°` | **39.3 px** | `87.6 x 39.3 px` | `48.4% – 51.8%` | `True` | `M02` |
| `cloud` | `B3` | `(+2.60, 10.76)` | `TEAPOT_LOW` (`0.80x` in case) | `-155.0°` | **30.9 px** (case: **65.7 px**) | `114.8 x 65.7 px` | `62.6% – 67.1%` | `True` | `M04`, `M07` |
| `crystal` | `R2` | `(+3.50, 8.46)` | `TEAPOT_CRYSTAL` | `-155.0°` | **52.3 px** | `109.3 x 52.3 px` | `73.8% – 78.1%` | `False` | — |
| `porcelain` | `R1` | `(+3.50, 5.86)` | `TEAPOT_CAVITY_HI` + `LID` | `-155.0°` | **88.6 px** | `192.2 x 88.6 px` | `86.1% – 93.6%` | `False` | — |

---

## 3. Emitter Table (Step 7)

| Emitter Object | Collection | Slot / Role | Position `(X, Y, Z)` (m) | Aim Direction | Size (m) | `lobe_exponent` | Color (RGB) | Strength |
|---|---|---|---|---|---|---|---|---|
| `PRIM_PLANE_emitter_L1` | `LIGHT_dim` | `L1` spot | `(-3.50, 5.86, 3.45)` | `(0, 0, -1)` | `0.12 x 0.12` | `100` | `[1.0, 0.95, 0.88]` | `120.0` |
| `PRIM_PLANE_emitter_L2` | `LIGHT_dim` | `L2` spot | `(-3.50, 8.46, 3.45)` | `(0, 0, -1)` | `0.12 x 0.12` | `100` | `[1.0, 0.95, 0.88]` | `120.0` |
| `PRIM_PLANE_emitter_B1` | `LIGHT_dim` | `B1` spot | `(-2.60, 10.76, 3.45)` | `(0, 0, -1)` | `0.12 x 0.12` | `100` | `[1.0, 0.95, 0.88]` | `120.0` |
| `PRIM_PLANE_emitter_B2` | `LIGHT_dim` | `B2` spot | `(0.00, 10.76, 3.45)` | `(0, 0, -1)` | `0.12 x 0.12` | `100` | `[1.0, 0.95, 0.88]` | `120.0` |
| `PRIM_PLANE_emitter_B3` | `LIGHT_dim` | `B3` spot | `(+2.60, 10.76, 3.45)` | `(0, 0, -1)` | `0.12 x 0.12` | `100` | `[1.0, 0.95, 0.88]` | `120.0` |
| `PRIM_PLANE_emitter_R1` | `LIGHT_dim` | `R1` spot | `(+3.50, 5.86, 3.45)` | `(0, 0, -1)` | `0.12 x 0.12` | `100` | `[1.0, 0.95, 0.88]` | `120.0` |
| `PRIM_PLANE_emitter_R2` | `LIGHT_dim` | `R2` spot | `(+3.50, 8.46, 3.45)` | `(0, 0, -1)` | `0.12 x 0.12` | `100` | `[1.0, 0.95, 0.88]` | `120.0` |
| `PRIM_SPHERE_stained_glass_emitter` | `LIGHT_dim` | `B2` internal bulb | `(0.00, 10.76, 1.01)` | Isotropic sphere | `r = 0.02` | `0` | `[1.0, 0.92, 0.75]` | `45.0` |
| `PRIM_PLANE_cloud_backlight` | `LIGHT_dim` | `B3` rim backlight | `(+2.60, 11.12, 1.25)` | `(0, -0.819, -0.574)` | `0.18 x 0.09` | `1` | `[0.95, 0.97, 1.0]` | `12.0` |
| `PRIM_PLANE_cove_back` | `LIGHT_dim` | Back ceiling cove | `(0.00, 11.68, 3.48)` | `(0, 0, -1)` | `7.80 x 0.08` | `1` | `[1.0, 0.91, 0.80]` | `0.65` |
| `PRIM_PLANE_cove_front` | `LIGHT_dim` | Front ceiling cove | `(0.00, 0.08, 3.48)` | `(0, 0, -1)` | `7.80 x 0.08` | `1` | `[1.0, 0.91, 0.80]` | `0.65` |
| `PRIM_PLANE_cove_left` | `LIGHT_dim` | Left ceiling cove | `(-4.42, 5.88, 3.48)` | `(0, 0, -1)` | `0.08 x 10.16` | `1` | `[1.0, 0.91, 0.80]` | `0.65` |
| `PRIM_PLANE_cove_right` | `LIGHT_dim` | Right ceiling cove | `(+4.42, 5.88, 3.48)` | `(0, 0, -1)` | `0.08 x 10.16` | `1` | `[1.0, 0.91, 0.80]` | `0.65` |
| `PRIM_PLANE_bright_panel_01..06` | `LIGHT_bright` | Comparison ceiling grid (`2x3`) | `(±2.20, {3.2, 6.4, 9.6}, 3.55)` | `(0, 0, -1)` | `2.20 x 2.20` | `1` | `[1.0, 0.98, 0.95]` | `14.0` |

---

## 4. Camera Table (Step 8)

| Camera Name | Location `(X, Y, Z)` (m) | Rotation Euler `XYZ` (deg) | Look-At Target `(X, Y, Z)` (m) | HFOV / VFOV (deg) | Focal / Sensor (mm) | Model | f-stop | Focus Dist (m) | Aperture Diam (m) |
|---|---|---|---|---|---|---|---|---|---|
| `CAM_main` | `(0.000, 1.000, 1.600)` | `(88.67°, 0.00°, 0.00°)` | `(0.00, 11.76, 1.35)` | `83.97° / 41.58°` | `20.0 / 36.0` | `pinhole` | `2.8` | `10.7629` | `0.00714` |
| `CAM_close_melitta` | `(-2.457, 4.191, 1.320)` | `(82.47°, 0.00°, 32.00°)` | `(-3.50, 5.86, 1.06)` | `23.91° / 10.21°` | `85.0 / 36.0` | `pinhole` | `2.8` | `1.9847` | `0.03036` |
| `CAM_close_metal` | `(-2.499, 6.858, 1.280)` | `(82.16°, 0.00°, 32.00°)` | `(-3.50, 8.46, 1.02)` | `23.91° / 10.21°` | `85.0 / 36.0` | `pinhole` | `2.8` | `1.9067` | `0.03036` |
| `CAM_close_jade` | `(-1.832, 9.034, 1.280)` | `(82.16°, 0.00°, 24.00°)` | `(-2.60, 10.76, 1.02)` | `23.91° / 10.21°` | `85.0 / 36.0` | `pinhole` | `2.8` | `1.9067` | `0.03036` |
| `CAM_close_stained_glass` | `(0.708, 9.009, 1.280)` | `(82.16°, 0.00°, 22.00°)` | `(0.00, 10.76, 1.02)` | `23.91° / 10.21°` | `85.0 / 36.0` | `pinhole` | `2.8` | `1.9067` | `0.03036` |
| `CAM_close_cloud` | `(1.448, 8.172, 1.360)` | `(84.76°, 0.00°, -24.00°)` | `(+2.60, 10.76, 1.10)` | `23.91° / 10.21°` | `85.0 / 36.0` | `pinhole` | `2.8` | `2.8452` | `0.03036` |
| `CAM_close_porcelain` | `(2.499, 4.258, 1.280)` | `(82.16°, 0.00°, -32.00°)` | `(+3.50, 5.86, 1.02)` | `23.91° / 10.21°` | `85.0 / 36.0` | `pinhole` | `2.8` | `1.9067` | `0.03036` |
| `CAM_close_crystal` | `(2.499, 6.858, 1.280)` | `(82.16°, 0.00°, -32.00°)` | `(+3.50, 8.46, 1.02)` | `23.91° / 10.21°` | `85.0 / 36.0` | `pinhole` | `2.8` | `1.9067` | `0.03036` |
| `CAM_overview_top` | `(0.000, 5.880, 7.600)` | `(0.00°, 0.00°, 0.00°)` | `(0.00, 5.88, 0.00)` | Orthographic (`scale = 32.06 m`) | — | `ortho` | — | `7.6000` | — |
| `CAM_alt_front_ortho` | `(0.000, 0.500, 1.800)` | `(90.00°, 0.00°, 0.00°)` | `(0.00, 11.76, 1.80)` | Orthographic (`scale = 9.72 m`) | — | `ortho` | — | `11.2600` | — |

---

## 5. Export Dry Run Verification (Step 6)

Exported slot `B1` (`EX_jade`, `EX_jade_lid`, `PRIM_CUBE_plinth_B1`, `STANCHION_B1_1..4`, `ROPE_B1_front/left/right`, `PRIM_PLANE_placard_B1`, `PRIM_PLANE_emitter_B1`) to `blender/export_test/dry_run_B1.gltf` and `blender/export_test/dry_run_B1.obj`, plus canonical M05 meshes `assets/meshes/stanchion_m05_placeholder.obj` and `assets/meshes/rope_m05_placeholder.obj`.

- **Blender 5.3 glTF Exporter settings:**
  ```python
  bpy.ops.export_scene.gltf(
      filepath=...,
      export_format='GLTF_SEPARATE',
      use_selection=True,
      export_yup=False,      # disables "+Y Up", keeping Blender's Z-up, Y-forward meters
      export_extras=True,    # exports custom properties in node["extras"]
      export_apply=False,    # preserves analytic primitive scales and linked-duplicate instancing
      export_texcoords=True,
      export_normals=True,
      export_materials='EXPORT',
      export_lights=False,   # excludes PREVIEW_ONLY_LIGHTS
  )
  ```
- **Blender 5.3 OBJ Exporter settings:**
  ```python
  bpy.ops.wm.obj_export(
      filepath=...,
      export_selected_objects=True,
      forward_axis='Y',
      up_axis='Z',
      global_scale=1.0,
      export_uv=True,
      export_normals=True,
      export_materials=True,
      apply_modifiers=True,
  )
  ```
- **Verified in `dry_run_B1.gltf`:**
  - 12 nodes reference only 7 unique mesh indices (`STANCHION_B1_1..4` all share `mesh: 6`; `ROPE_B1_front/left/right` all share `mesh: 5`).
  - `EX_jade` translation is `[-2.6, 10.76, 0.90]` (Z-up, Y-forward meters) with `extras: {"exhibit_id": "jade", "slot": "B1", "renderer_material": "jade", "placeholder": false, "yaw_deg": -25.0}`.
  - `PRIM_PLANE_emitter_B1` translation is `[-2.6, 10.76, 3.45]`, scale `[0.06, 0.06, 1.0]`, with `extras: {"renderer_material": "emitter_spot", "slot": "B1", "emission_color": [1.0, 0.95, 0.88], "emission_strength": 120.0, "lobe_exponent": 100, "aim_direction": [0.0, 0.0, -1.0]}`.
- **Verified in `dry_run_B1.obj`:** `166,604` vertices, `169,277` UV coordinates (`vt`), `325,668` faces; first vertex `v -2.950000 10.410000 0.000000` matches plinth `B1` lower-left corner `(-2.60 - 0.35, 10.76 - 0.35, 0.00)`.
