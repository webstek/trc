# Teapot Gallery: Blender Blockout Plan (v1.0)

## How to use this document

You are building a Blender 5.3 blockout of a gallery scene through the community Blender MCP. Read the whole document before starting. Work through the build order in section 10 and follow the working rules in section 12.

The message that accompanies this document gives the file paths for the teapot meshes, the output folder, the report format, and whether to pause at checkpoints.

Where a spec is ambiguous, do not stop to ask. Pick the most reversible option and list it under "Assumptions and questions" in your report. Section 13 lists things that are known to be undecided or missing, with the default to use for each.

Scope: this task only builds the Blender scene and its notes. Translating the exported glTF into C++ is a separate task. Do not modify the renderer's codebase.

---

## 1. Goal

Build a Blender 5.3 blockout of a dim, realistic, fully enclosed art gallery in which seven teapot exhibits are visible together in one frame. This is for a rendering competition entry. The only content rule is that the Utah teapot must feature.

The Blender file has three jobs:

1. Judge composition, scale, lighting mood and camera before any expensive rendering.
2. Be the source of truth for placement, camera and textures.
3. Be exported (glTF, OBJ meshes, PNG textures) so a different agent can translate it into a C++ function for a custom path-tracing renderer. Keep every choice exportable and simple.

The main camera shows layout and mood. The final entry will also use a close-up shot of each exhibit, so every exhibit needs its own close-up camera.

The first pass is done when:

- All exhibits are visible and distinguishable from `CAM_main` at 2560x1080.
- The enclosed room, bays (plinth, velvet ropes, emitter, placard), paintings and lights exist, at least as primitive blockouts.
- The bays are built from one template.
- Every enabled exhibit has a close-up camera.
- `models_needed.md` lists everything that is still a placeholder.
- Checkpoint screenshots and the report are delivered.

### Deliverables

All go in the output folder named in the accompanying message.

- `gallery_v001.blend`, `gallery_v002.blend`, and so on (versioned saves).
- `build_gallery.py`, which regenerates the scene from `PARAMS`.
- `models_needed.md` (format in section 11).
- `handoff_notes.md` containing: the derived room dimensions and field of view; an exhibit table (id, slot, mesh, material, yaw, placeholder flag, `needs_model`); an emitter table (slot, position, aim direction, size, `lobe_exponent`, color, strength); the camera table (section 8); the painting table (section 9); the export settings used (section 10, step 6); and "Assumptions and questions".
- `textures/` with the placeholder paintings and placards.
- `export_test/` with the dry-run exports.
- Screenshots from each checkpoint and from every camera.

---

## 2. Target renderer: what it can and cannot take

The exported scene will be translated by hand, so the Blender scene must stay inside these limits. You do not implement any of this. It tells you what to build and how.

| Topic | Fact |
|---|---|
| Units | Meters. |
| Axes | Z-up, Y-forward. The camera looks toward +Y. |
| Meshes | `.obj` only, and every mesh must have UVs. 700k-triangle meshes load fine. |
| Textures | PNG. Meshes and analytic shapes share one geometry abstraction, so every shape takes a transform and textures. |
| Instancing | Supported, with a two-level BVH. Use it heavily. |
| Analytic shapes | Sphere, plane, cube, each transformable, each with an optional surface. They match Blender's default primitives exactly: plane [-1,1]^2 (size 2), cube [-1,1]^3 (size 2), sphere radius 1. |
| Shading normals | None. Geometric normals only. In Blender use flat shading, no normal or bump maps, no displacement nodes. Any detail that must survive export has to be real geometry. Curved geometry must be tessellated finely enough to look smooth under flat shading. |
| Lights | Point lights, and area lights on analytic primitives. The area lights take a cosine-power directional emission profile (exponent n), and all exhibit lighting uses it. Point lights are not used for exhibit lighting. Emitters are emissive primitives with custom properties (see section 7). |
| Environment | No environment map. The room must be fully enclosed, and all light comes from emitters inside it. |
| Media | Heterogeneous media use 3D textures for absorption and scattering coefficients, placed inside a primitive instance. There is no loader yet, so in Blender a medium is only a bounding primitive plus notes. |
| Camera | Pinhole and thin lens. |
| Scene format | None. A translator agent converts the glTF into a C++ function. |

---

## 3. Conventions

- **Units:** meters, unit scale 1.0. No centimeters anywhere.
- **Axes:** Z-up, Y-forward. All exports keep this convention (see section 10, step 6).
- **Render settings:** 2560 x 1080 at 100%, pixel aspect 1:1 (aspect ratio 64:27). Camera sensor fit set to horizontal.
- **Blender version:** 5.3. Verify Python API calls against 5.3 rather than assuming 4.x behavior.
- **Parametric layout:** build the whole scene from one `PARAMS` dict (see section 5). Keep a `build_gallery.py` in the output folder that regenerates the scene from `PARAMS`, so changes mean editing `PARAMS` and re-running, not hand edits. MCP calls may be incremental, but the script is the record.
- **Teapot scale:** the teapot meshes have no physical units and are 3 units tall. The spout axis (X) is the long one, about 6.4 units, and the width along Y is about 4 units. `teapot_scale` (meters per mesh unit) defaults to 0.08, giving a teapot 0.24 m tall, 0.51 m long and 0.32 m wide. It is a single parameter. In an enclosed room the camera stands inside, and the near side-wall bays have to sit far enough from it to stay in frame, so in `CAM_main` the teapots come out roughly 35 px tall at the back wall and 70 px at the nearest side bays (rough estimate: `2560 x teapot height / frame width at that depth`). `CAM_main` is therefore for layout and mood, and the close-ups carry the detail. Report the actual on-screen teapot heights in your report so the scale can be adjusted.

---

## 4. Inputs

File paths are given in the accompanying message.

| Key | Matched file (`assets/meshes/`) | Description | Used for |
|---|---|---|---|
| `TEAPOT_CRYSTAL` | `teapot_crystal.obj` | Low-poly, deliberately faceted, no interior | Crystal |
| `TEAPOT_LOW` | `teapot_res2_nochamfer_nocc_flat_nointerior_outertrim_lidccap_bijective.obj` | Less faceted low-res single-walled mesh with UVs | Base for the stained-glass conversion, cloud proxy |
| `TEAPOT_CAVITY_HI` | `teapot_res48_flat_ceminterior_bijective.obj` | Watertight, high-res, thick closed-wall interior cavity (with lid) | Jade, porcelain, metal (hammered derivative), thin-film (optional) |
| `TEAPOT_CAVITY_LID` | `teapot_res48_onlylid_bijective.obj` (paired with `teapot_res48_nolid_flat_ceminterior_bijective.obj`) | The lid of the cavity version, as its own mesh | Same exhibits as `TEAPOT_CAVITY_HI` (when using separate body/lid) |
| `TEAPOT_SOLID_HI` | *(not supplied separately; `teapot_res48_nolid_flat_ceminterior_bijective.obj` is the no-lid cavity body)* | Watertight, high-res, no interior | No exhibit assigned at the moment. Import it and keep it available. |
| `MELITTA` | `teapot_res48_melitta_bijective.obj` | Melitta teapot mesh | Melitta exhibit |
| `TEAPOT_LOW_BREAKDOWN` | *(not supplied)* | Optional image showing what is where on `TEAPOT_LOW` (its parts and their UV regions), supplied by the user if available | Identifying parts, for example to color the stained-glass preview per part. The first pass does not depend on it. |

Mesh frame:

- Z-up, spout toward +X. The origin is on the body's vertical axis and the lowest point is at z=0. The lid file sits in place at an identity transform relative to the body.
- Expected bounding box in mesh units: x [-3, 3.4], y [-2, 2], z [0, 3]. No physical units. Verify this on import. If the long axis turns out to be Y, stop and report before normalizing.

On import, report for each mesh: file name, triangle count, bounding box, origin location, whether it has UVs, and any non-manifold edges. For the lid, also report the gap between the lid's lowest point and the body's rim, to confirm it sits in place. Then apply `teapot_scale` only. The native frame (Z-up, spout +X) is the canonical exhibit frame, so no rotation is needed except the per-exhibit yaw at placement. Store the unmodified originals in a hidden `ASSETS` collection. Originals are never edited. Derivatives are new objects.

---

## 5. Exhibits and configuration

The number of exhibits and their slots must be configurable. Adding, removing or moving an exhibit means editing `PARAMS` and re-running the build.

```python
PARAMS = {
    "teapot_scale": 0.08,                          # meters per mesh unit
    "stand_ins": {"TEAPOT_LOW": "TEAPOT_CRYSTAL"}, # used while a mesh file is missing
    "bays": {"back": 3, "left": 2, "right": 2},    # slots B1..B3, L1..L2, R1..R2
    "bay_spacing": 2.6,                            # meters between bay centers along a wall
    "ceiling_height": 3.6,
    "plinth": {"top": 0.7, "height": 0.9},
    "rope": {"enclosure": "u3", "clearance": 0.55,
             "post_height": 0.95, "rope_height": 0.85, "sag": 0.08},
    "emitter": {"size": 0.12, "lobe_exponent": 100},
    "glass_thickness_m": 0.004,                    # stained-glass preview shell
    "camera_main": {"eye_height": 1.6, "wall_gap": 1.0, "max_hfov_deg": 90,
                    "sensor_width_mm": 36},
    "camera_close": {"focal_length_mm": 85, "sensor_width_mm": 36, "fstop": 2.8,
                     "dof_enabled": False},
    "paintings": {"count": 12, "center_height": 1.5,
                  "mix": {"16:9": 5, "1:1": 5, "9:16": 1, "3:2": 1}},
    "skip_empty_bays": False,
    "exhibits": [
        {"id": "melitta",       "slot": "L1", "mesh": "MELITTA",          "renderer_material": "melitta",       "enabled": True, "needs_model": "M01"},
        {"id": "metal",         "slot": "L2", "mesh": "TEAPOT_CAVITY_HI", "renderer_material": "metal",         "enabled": True, "needs_model": "M03"},
        {"id": "jade",          "slot": "B1", "mesh": "TEAPOT_CAVITY_HI", "renderer_material": "jade",          "enabled": True},
        {"id": "stained_glass", "slot": "B2", "mesh": "TEAPOT_LOW",       "renderer_material": "stained_glass", "enabled": True, "needs_model": "M02"},
        {"id": "cloud",         "slot": "B3", "mesh": "TEAPOT_LOW",       "renderer_material": "cloud",         "enabled": True, "needs_model": "M04"},
        {"id": "porcelain",     "slot": "R1", "mesh": "TEAPOT_CAVITY_HI", "renderer_material": "porcelain",     "enabled": True},
        {"id": "crystal",       "slot": "R2", "mesh": "TEAPOT_CRYSTAL",   "renderer_material": "crystal",       "enabled": True},
        {"id": "thin_film",     "slot": None, "mesh": "TEAPOT_CAVITY_HI", "renderer_material": "thin_film",     "enabled": False, "needs_model": "M06"},
    ],
}
```

Rules for the configuration:

- Slot names: `B1..Bn` on the back wall, left to right as seen from `CAM_main`. `L1..Ln` and `R1..Rn` on the side walls, from the camera end to the back wall.
- Room dimensions are derived from the bay counts, `bay_spacing`, the camera layout rule in section 6, and a margin and corner clearance so rope enclosures at a corner do not collide. Explicit overrides are allowed.
- A slot with no enabled exhibit gets an empty plinth, or is skipped when `skip_empty_bays` is true.
- More enabled exhibits than slots is an error to report, not to fix silently.
- `renderer_material` is a free string. Known keys: `crystal`, `stained_glass`, `jade`, `porcelain`, `metal`, `melitta`, `cloud`, `thin_film`.
- When a mesh key has no file yet, use its `stand_ins` entry and set `placeholder = true` on the object.
- Default yaw per exhibit: the spout (local +X) points toward the room's centerline (for the center slot, to the viewer's right), then turned about 25 degrees toward the camera. Overridable per exhibit with `yaw_deg`.

| Exhibit | Mesh | Preview material intent | Notes |
|---|---|---|---|
| Melitta | `MELITTA` (primitive stand-in for now) | Light ceramic | Stand-in: ellipsoid body, cylinder spout, torus handle. |
| Metal | Hammered derivative of `TEAPOT_CAVITY_HI` | Brass or copper | Hammering is real geometry, not a bump map (M03). |
| Jade | `TEAPOT_CAVITY_HI` | Translucent green with vein and cloud variation, waxy coat | |
| Stained glass | `TEAPOT_LOW`, converted | Colored glass panels with dark lead (solder) lines, light source inside the hollow | See the stained glass subsection below (M02). |
| Cloud | See below | White scattering medium inside a glass case | |
| Porcelain | `TEAPOT_CAVITY_HI` | White glazed body, blue-and-white painted pattern | |
| Crystal | `TEAPOT_CRYSTAL` | Clear, high-dispersion glass | Flat facets are intentional. |
| Thin film (optional) | `TEAPOT_CAVITY_HI` | Iridescent bubble or oil-slick look | Disabled by default. |

Preview materials are Principled BSDF only and only approximate. They are for judging mood, not for matching the renderer. Each exhibit object gets these custom properties:

- `exhibit_id`
- `renderer_material`
- `placeholder` (true or false)
- `needs_model` (an ID from `models_needed.md`, if any)

Export glTF with custom properties enabled so the translator can read them.

### Stained glass exhibit

The final model (M02) is a thin-walled, hollow teapot converted from `TEAPOT_LOW`, with solder marks along the panel edges. `TEAPOT_LOW` still has slightly too much detail to turn into glass pieces, so the user will simplify it further as part of M02. The conversion and the panel layout are the user's job, not yours.

First pass:

- The placeholder is the unmodified `TEAPOT_LOW` (stand-in `TEAPOT_CRYSTAL` until supplied) with a stained-glass-looking preview material. Per-panel colors can be approximated (for example a random color per face from a color attribute, or per part if `TEAPOT_LOW_BREAKDOWN` is available). This does not need to survive export.
- Optional: build a thin-walled preview shell as a derivative named `EX_stained_glass_thin` (Solidify inward by `glass_thickness_m`, then apply the modifier) so the hollow interior and the emitter placement can be judged.
- The light source is a small emissive sphere (`PRIM_SPHERE`, radius 0.02 m) at the center of the hollow interior.

### Cloud exhibit: cumulonimbus teapot in a glass case

The cloud is a teapot-shaped cloud with a cumulonimbus look (billowing, cauliflower sides) sealed in a glass display case so it cannot escape.

- **Case, for now:** two nested analytic cubes, `PRIM_CUBE_case_outer` and `PRIM_CUBE_case_inner`, with wall thickness `case_wall_m` (default 0.01 m). Both are plain, outward-facing, positive-scale cubes. The inner cube is not inverted (no negative scale, no flipped normals), because the renderer handles the medium boundary. The inner cube is the medium bounds in the renderer. The final case design is the user's decision (M07).
- **Fit:** the case must fit on the plinth top (0.7 m). If it does not, scale the cloud proxy down, not the plinth.
- **Cloud proxy:** `TEAPOT_LOW` (stand-in `TEAPOT_CRYSTAL` until supplied) scaled and centered inside the inner cube with at least 0.05 m clearance, named `CLOUD_PROXY`, custom property `cloud_proxy = true`. It only has to be a smooth medium boundary shape. Preview material: Volume Scatter with noise-modulated density and no surface. The renderer does not draw the proxy as geometry. Its OBJ is exported only so the density grid can be generated from the teapot shape.
- **Density grid:** the 3D texture is not built in Blender. It is model M04.
- **Optional:** a backlight emitter behind the case in `LIGHT_dim` for a silver-lining rim, controlled by a `cloud_backlight` parameter.

---

## 6. Room layout (U-shape, enclosed)

The room is fully enclosed: floor, ceiling and four walls. The renderer has no environment map, so there are no windows or skylights unless they are emissive panels. The "open end" of the U is the side where the camera stands, not an opening in the room.

Plan view, Y forward:

```
 +--------------------- back wall (+Y) ----------------------+
 |        [B1]            [B2]            [B3]               |
 |                                                           |
 |  [L2]                                            [R2]     |
 |                                                           |
 |  [L1]                                            [R1]     |
 |                                                           |
 |                  camera, on the centerline                |
 +---------------- wall behind the camera -------------------+
```

**Layout rule for the camera:** the camera is inside the room on the centerline, `camera_main.wall_gap` (1.0 m) from the wall behind it. Choose side-bay positions so all enabled exhibits sit inside the central ~80% of the horizontal frame, with horizontal field of view no wider than about `max_hfov_deg` (90). That pushes the nearest side bays well away from the camera, so the room depth is derived from this rule. Report the derived room dimensions and the field of view.

**Bay template** (plinths are freestanding in front of the wall, with a VIP velvet-rope look). Built once, then instanced per slot as linked duplicates.

- **Plinth:** `PRIM_CUBE`, top 0.7 x 0.7 m, height 0.9 m. Pale matte material so caustics and glints read on it.
- **Velvet rope enclosure:** four brass stanchions at the corners of a square centered on the plinth, `rope.clearance` (0.55 m) from the plinth edges. `rope.enclosure = "u3"` means three rope spans (the side facing the camera and the two adjacent sides) with the side against the wall left open. `"ring4"` closes all four sides. The rope is a sagging catenary tube mesh in red velvet. Because the enclosure is a square, one rope mesh is reused for every span as a linked duplicate. Stanchion and rope meshes need UVs and fine tessellation (for example 24 or more sides on the rope and 48 or more segments around the posts).
- **Emitter:** one small emissive plane under the ceiling, aimed at the plinth top center (see section 7).
- **Placard:** a small textured plane on the wall beside the bay at about 1.5 m, with a generated PNG showing the exhibit's name and material.

---

## 7. Lighting

Intent: a dim room, a small, bright, narrow emitter on each bay, a faint cove strip for fill, a polished dark floor and charcoal walls. Because the room is enclosed and there is no environment map, every photon comes from these emitters, so the cove strips matter for keeping the dark regions from going black.

- Build lighting as toggleable collections: `LIGHT_dim` (default) and `LIGHT_bright` (white-cube gallery, for comparison). Both variants are fully emitter-based.
- **Exhibit emitters** are small emissive planes (`PRIM_PLANE`, scaled to `emitter.size`) with custom properties `emission_color`, `emission_strength` and `lobe_exponent` (default 100, which gives a pool of about 0.3 m half-power radius from an emitter about 2.5 m above the plinth). Blender's units do not map to the renderer's, so record the values. These planes are the exported emitters.
- **Preview in Blender:** for each emitter plane, place a co-located Blender Area light (square, size `emitter.size`, aimed the same way, spread chosen by eye to look like the lobe) in a `PREVIEW_ONLY_LIGHTS` collection that is excluded from export. Give the emitter plane a non-emissive preview material so the light is not counted twice. As far as I know the Blender glTF exporter only carries point, spot and sun lights, so Blender area lights would not survive export. This is why the plane with custom properties is the real emitter. The export dry run (step 6) confirms that the emitter planes and their properties survive and that the preview lights are excluded.
- **Diffuse emitters** (cove strips, the stained-glass sphere, the bright variant's panels) have no lobe. Their Blender emission shader is the preview, with no separate preview light.
- The stained glass exhibit has a small emissive sphere inside its hollow interior (see section 5).
- Do not use Blender Point, Spot or Area lights in exported collections.
- Use Cycles at low samples with the denoiser to judge the look, and EEVEE for fast iteration.

---

## 8. Cameras

The renderer has both a pinhole and a thin-lens camera. Most shots use the pinhole. Some close-ups may use the thin lens.

- `CAM_main`: pinhole, eye height around 1.6 m, inside the room on the centerline of the U, looking +Y, 2560x1080, rectilinear.
- `CAM_close_<exhibit_id>`: one close-up per enabled exhibit, a three-quarter view from the viewer's side of the ropes, same resolution as `CAM_main`.
  - Defaults: the exhibit fills about 60% of the frame width, focal length 85 mm on a 36 mm sensor to limit distortion. Adjust as needed.
  - Ropes in the foreground are acceptable. If they block the exhibit, raise the camera or move closer, and report it if you cannot avoid it.
  - Pinhole by default. Blender's depth of field is off, with the focus distance set to the exhibit's center and the f-stop set to `camera_close.fstop` (2.8), so the user can switch it on for a thin-lens shot.
- `CAM_overview_top`: orthographic plan view.
- `CAM_alt_*`: composition alternatives (for example an orthographic front elevation).
- Record every camera in `handoff_notes.md`: location, rotation or look-at target, horizontal and vertical field of view, focal length and sensor width, model (pinhole or thin lens), f-stop, focus distance, and aperture diameter (focal length divided by f-stop, in meters).

---

## 9. Paintings and dressing

- About 12 paintings fill the empty wall space on all four walls. The wall behind the camera gets a few (about three), seen only in the metal and glass reflections. Later these become the user's own renders.
- Aspect ratios are varied, with 16:9 and 1:1 the main two. Default mix: 5 at 16:9, 5 at 1:1, 1 at 9:16 and 1 at 3:2. Sizes are chosen by you, between 0.7 and 1.8 m on the long side, centered at `paintings.center_height` (1.5 m). Distribute them by available wall space and report the result. Keep the wall directly behind each bay plain so the exhibit reads against a clean backdrop, and hang paintings in the gaps and on the remaining wall. Paintings must not overlap bays or placards.
- Each painting is an analytic plane (`PRIM_PLANE`, scale = half the width and half the height) with an image texture, plus a thin box frame (`PRIM_CUBE`) just behind it. The plane's front face is its +Z side, so rotate it to face into the room, and verify the texture is not mirrored.
- Generate distinct placeholder PNGs (flat color, large ID number, border showing the aspect ratio) so every position is identifiable in screenshots. Name them `paint_01.png` and so on, with objects `PAINT_01` and so on.
- The painting table (ID, wall, position, size, aspect ratio, file) goes in `handoff_notes.md`.
- Other dressing: a viewing bench, wall cove strips and floor and wall materials (dark polished floor, charcoal walls). These are primitive blockouts, lower priority.

---

## 10. Build order and checkpoints

0. **Capability check.** Report which of these the MCP can do: run arbitrary Python, return a viewport screenshot, render an image, read and write files.
1. Scene setup: units, axes, render settings, collection skeleton, `PARAMS` and `build_gallery.py`.
2. Import assets and report the per-mesh details from section 4.
3. Room shell: floor, ceiling and four walls, with dimensions derived from the bay counts and the camera layout rule.
4. Bay template (plinth, stanchions, rope, emitter, placard), then one instance per slot.
5. Place exhibits with placeholder materials and primitives, including the cloud case and the stained glass preview.
6. **Export dry run.** Export one exhibit, one bay and one emitter to glTF and OBJ and verify axes, units, UVs and custom properties. glTF must keep Z-up and Y-forward, so turn off the exporter's Y-up conversion (its "+Y Up" option; verify the name in 5.3) and confirm a known object's coordinates in the exported file. For OBJ, use forward Y, up Z, scale 1.0, UVs on. Record the settings used.
7. Dim lighting, then bright lighting.
8. Cameras and screenshots (**Checkpoint A**).
9. Paintings.
10. Dressing blockouts.
11. `models_needed.md`, `handoff_notes.md` and the report.

---

## 11. `models_needed.md` format

A markdown table with these columns:

| ID | Name | Used where | Current placeholder | Approx. size (m) | UVs needed | Priority | Notes |
|---|---|---|---|---|---|---|---|

Priority: P1 needed for the first real render, P2 needed for the final, P3 nice to have.

Seed rows:

| ID | Name | Used where | Current placeholder |
|---|---|---|---|
| M01 | Melitta teapot mesh | Melitta slot | Primitive stand-in |
| M02 | Thin-walled stained-glass teapot (simplified `TEAPOT_LOW`, with panel layout and solder marks) | Stained glass slot | Unmodified `TEAPOT_LOW` (or its stand-in), optional thin preview shell |
| M03 | Hammered-metal derivative | Metal slot | Unmodified `TEAPOT_CAVITY_HI` |
| M04 | Cumulonimbus density grid (teapot-shaped) | Cloud slot | `CLOUD_PROXY` with a volume shader |
| M05 | Brass stanchion and velvet rope meshes (final quality) | All bays | Agent-built meshes |
| M06 | Thin-film teapot (only if enabled) | Optional slot | Unmodified `TEAPOT_CAVITY_HI` |
| M07 | Cloud container: glass case, possibly with metal posts and clamps (design to be determined) | Cloud slot | Two nested cubes |
| M08 | `TEAPOT_LOW`: less faceted low-res single-walled mesh (supplied by the user) | Stained glass and cloud slots | `TEAPOT_CRYSTAL` as a stand-in |

Add rows for anything else you find. Placeholder rules:

- Use plain primitives (cube, sphere, cylinder, plane) at real-world size.
- Name them `PLACEHOLDER_<ID>_<part>`.
- Set the custom property `placeholder_for = M0x`.

---

## 12. Working rules

- **Collections:** `ASSETS` (hidden), `ROOM`, `BAY_TEMPLATE`, `EXHIBITS`, `LIGHT_dim`, `LIGHT_bright`, `PREVIEW_ONLY_LIGHTS` (excluded from export), `PAINTINGS`, `DRESSING`, `CAMERAS`.
- **Idempotent build:** re-running `build_gallery.py` deletes and recreates the objects it generated. It never touches the originals in `ASSETS`.
- **Instancing:** use linked duplicates that share mesh data, not copies. Apply rotation and scale on source objects before instancing, so instances differ only by transform. Prefer linked duplicates over collection instances for anything that must survive export, and verify in the export dry run.
- **Analytic primitives:** objects named `PRIM_CUBE_*`, `PRIM_SPHERE_*` and `PRIM_PLANE_*` must be unmodified default Blender primitives (plane size 2, cube size 2, sphere radius 1), which match the renderer's analytic shapes exactly, with only a transform. Use them for walls, floor, ceiling, plinths, frames, paintings, placards, emitters and the glass case. Scale is the half-extent (or radius), not the full size. Never use negative scale or flipped normals on them.
- **Mesh hygiene:** flat shading, no custom normals, UVs on every mesh, no unapplied modifiers on exported meshes.
- **Materials:** Principled BSDF and image textures only on anything meant to be exported. Textures are PNGs in a `textures/` folder, referenced by relative path. Every exportable object gets a `renderer_material` property.
- **Saves:** versioned (`gallery_v001.blend`, `gallery_v002.blend`, ...). Save before any large change. Never overwrite an earlier version.
- **Verification:** take a screenshot after each major step and check it by looking, not by assuming. Take checkpoint screenshots from camera view.
- **MCP notes:** this uses the community Blender MCP. Expect scene info, object info, viewport screenshot and execute-Python tools, and verify them in step 0. Keep each Python call short and save before heavy ones, since a long call blocks Blender. If the MCP offers asset-download integrations (Poly Haven, Sketchfab, Hyper3D), do not use them. Build from primitives and the supplied meshes only.
- **No silent assumptions:** when something is ambiguous or the MCP cannot do it, pick the most reversible option and list it under "Assumptions and questions" in `handoff_notes.md` and the report.

---

## 13. Known unknowns (they do not block the work)

| Item | Status | What to do |
|---|---|---|
| `TEAPOT_LOW` | Not supplied yet | Use `TEAPOT_CRYSTAL` as a stand-in and set `placeholder = true`. |
| Stained-glass panel layout | `TEAPOT_LOW` needs slight further simplification, and the user may supply a breakdown image (`TEAPOT_LOW_BREAKDOWN`) | Approximate panels in the preview (section 5). The real layout is M02. |
| Cloud container final design | Undecided (M07) | Use the two nested cubes. |
| `MELITTA` | Not supplied yet | Use the primitive stand-in. |
| Cloud density grid | Not built yet (M04) | Use `CLOUD_PROXY` with a volume shader. |
