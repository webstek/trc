"""
Teapot Gallery: Parametric Blender 5.3 Blockout Builder
Regenerates the gallery scene from PARAMS.
Idempotent: preserves unmodified original meshes in ASSETS and recreates all scene collections.
"""

import bpy
import bmesh
import math
import os
import random
import struct
import zlib
from mathutils import Vector, Matrix, Euler

WORKSPACE_DIR = r"W:\docs-dev\trc"
MESH_DIR = os.path.join(WORKSPACE_DIR, "assets", "meshes")
TEXTURE_DIR = os.path.join(WORKSPACE_DIR, "assets", "textures")
BLEND_DIR = os.path.join(WORKSPACE_DIR, "blender")
DOCS_DIR = os.path.join(WORKSPACE_DIR, "docs")

MESH_FILES = {
    "TEAPOT_CRYSTAL": "teapot_crystal.obj",
    "TEAPOT_LOW": "teapot_res2_nochamfer_nocc_flat_nointerior_outertrim_lidccap_bijective.obj",
    "TEAPOT_CAVITY_HI": "teapot_res48_flat_ceminterior_bijective.obj",
    "TEAPOT_CAVITY_NOLID": "teapot_res48_nolid_flat_ceminterior_bijective.obj",
    "TEAPOT_CAVITY_LID": "teapot_res48_onlylid_bijective.obj",
    "MELITTA": "teapot_res48_melitta_bijective.obj",
}

PARAMS = {
    "teapot_scale": 0.08,                          # meters per mesh unit
    "normalize_crystal_to_3_units": True,          # teapot_crystal.obj raw z_max is 0.75645 (~1/4 of 3.0)
    "use_melitta_mesh": True,                      # True uses teapot_res48_melitta_bijective.obj; False uses primitive stand-in
    "show_stained_glass_thin_shell": False,        # EX_stained_glass_thin is built; False hides it so it doesn't z-fight EX_stained_glass
    "stand_ins": {"TEAPOT_LOW": "TEAPOT_CRYSTAL"}, # used while a mesh file is missing
    "bays": {"back": 3, "left": 2, "right": 2},    # slots B1..B3, L1..L2, R1..R2
    "bay_spacing": 2.6,                            # meters between bay centers along a wall
    "ceiling_height": 3.6,
    "plinth": {"top": 0.7, "height": 0.9},
    "rope": {"enclosure": "u3", "clearance": 0.55,
             "post_height": 0.95, "rope_height": 0.85, "sag": 0.08},
    "emitter": {"size": 0.12, "lobe_exponent": 100, "height_above_plinth": 2.55,
                "color": [1.0, 0.95, 0.88], "strength": 120.0, "preview_watts": 65.0},
    "glass_thickness_m": 0.004,                    # stained-glass preview shell
    "case_wall_m": 0.01,                           # cloud glass display case wall thickness
    "cloud_backlight": True,                       # optional rim backlight behind cloud case in LIGHT_dim
    "camera_main": {"eye_height": 1.6, "wall_gap": 1.0, "max_hfov_deg": 90,
                    "focal_length_mm": 20.0, "sensor_width_mm": 36, "frame_fraction": 0.80},
    "camera_close": {"focal_length_mm": 85, "sensor_width_mm": 36, "fstop": 2.8,
                     "dof_enabled": False, "fill_fraction": 0.60},
    "paintings": {"count": 12, "center_height": 1.5,
                  "mix": {"16:9": 5, "1:1": 5, "9:16": 1, "3:2": 1}},
    "skip_empty_bays": False,
    "exhibits": [
        {"id": "melitta",       "slot": "L1", "mesh": "MELITTA",          "renderer_material": "melitta",       "enabled": True,  "needs_model": "M01"},
        {"id": "metal",         "slot": "L2", "mesh": "TEAPOT_CAVITY_HI", "renderer_material": "metal",         "enabled": True,  "needs_model": "M03"},
        {"id": "jade",          "slot": "B1", "mesh": "TEAPOT_CAVITY_HI", "renderer_material": "jade",          "enabled": True},
        {"id": "stained_glass", "slot": "B2", "mesh": "TEAPOT_LOW",       "renderer_material": "stained_glass", "enabled": True,  "needs_model": "M02"},
        {"id": "cloud",         "slot": "B3", "mesh": "TEAPOT_LOW",       "renderer_material": "cloud",         "enabled": True,  "needs_model": "M04"},
        {"id": "porcelain",     "slot": "R1", "mesh": "TEAPOT_CAVITY_HI", "renderer_material": "porcelain",     "enabled": True},
        {"id": "crystal",       "slot": "R2", "mesh": "TEAPOT_CRYSTAL",   "renderer_material": "crystal",       "enabled": True},
        {"id": "thin_film",     "slot": None, "mesh": "TEAPOT_CAVITY_HI", "renderer_material": "thin_film",     "enabled": False, "needs_model": "M06"},
    ],
}


# ---------------------------------------------------------------------------
# Minimal Pure-Python PNG Writer with 5x7 Bitmap Font (zero external deps)
# ---------------------------------------------------------------------------
FONT_5X7 = {
    ' ': [0,0,0,0,0,0,0],
    'A': [0b01110,0b10001,0b10001,0b11111,0b10001,0b10001,0b10001],
    'B': [0b11110,0b10001,0b10001,0b11110,0b10001,0b10001,0b11110],
    'C': [0b01110,0b10001,0b10000,0b10000,0b10000,0b10001,0b01110],
    'D': [0b11100,0b10010,0b10001,0b10001,0b10001,0b10010,0b11100],
    'E': [0b11111,0b10000,0b10000,0b11110,0b10000,0b10000,0b11111],
    'F': [0b11111,0b10000,0b10000,0b11110,0b10000,0b10000,0b10000],
    'G': [0b01110,0b10001,0b10000,0b10111,0b10001,0b10001,0b01110],
    'H': [0b10001,0b10001,0b10001,0b11111,0b10001,0b10001,0b10001],
    'I': [0b01110,0b00100,0b00100,0b00100,0b00100,0b00100,0b01110],
    'J': [0b00111,0b00010,0b00010,0b00010,0b10010,0b10010,0b01100],
    'K': [0b10001,0b10010,0b10100,0b11000,0b10100,0b10010,0b10001],
    'L': [0b10000,0b10000,0b10000,0b10000,0b10000,0b10000,0b11111],
    'M': [0b10001,0b11011,0b10101,0b10101,0b10001,0b10001,0b10001],
    'N': [0b10001,0b11001,0b10101,0b10011,0b10001,0b10001,0b10001],
    'O': [0b01110,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110],
    'P': [0b11110,0b10001,0b10001,0b11110,0b10000,0b10000,0b10000],
    'Q': [0b01110,0b10001,0b10001,0b10001,0b10101,0b10010,0b01101],
    'R': [0b11110,0b10001,0b10001,0b11110,0b10100,0b10010,0b10001],
    'S': [0b01111,0b10000,0b10000,0b01110,0b00001,0b00001,0b11110],
    'T': [0b11111,0b00100,0b00100,0b00100,0b00100,0b00100,0b00100],
    'U': [0b10001,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110],
    'V': [0b10001,0b10001,0b10001,0b10001,0b10001,0b01010,0b00100],
    'W': [0b10001,0b10001,0b10001,0b10101,0b10101,0b11011,0b10001],
    'X': [0b10001,0b10001,0b01010,0b00100,0b01010,0b10001,0b10001],
    'Y': [0b10001,0b10001,0b01010,0b00100,0b00100,0b00100,0b00100],
    'Z': [0b11111,0b00001,0b00010,0b00100,0b01000,0b10000,0b11111],
    '0': [0b01110,0b10001,0b10011,0b10101,0b11001,0b10001,0b01110],
    '1': [0b00100,0b01100,0b00100,0b00100,0b00100,0b00100,0b01110],
    '2': [0b01110,0b10001,0b00001,0b00110,0b01000,0b10000,0b11111],
    '3': [0b11110,0b00001,0b00001,0b01110,0b00001,0b00001,0b11110],
    '4': [0b00010,0b00110,0b01010,0b10010,0b11111,0b00010,0b00010],
    '5': [0b11111,0b10000,0b10000,0b11110,0b00001,0b00001,0b11110],
    '6': [0b01110,0b10000,0b10000,0b11110,0b10001,0b10001,0b01110],
    '7': [0b11111,0b00001,0b00010,0b00100,0b01000,0b01000,0b01000],
    '8': [0b01110,0b10001,0b10001,0b01110,0b10001,0b10001,0b01110],
    '9': [0b01110,0b10001,0b10001,0b01111,0b00001,0b00001,0b01110],
    ':': [0b00000,0b00100,0b00100,0b00000,0b00100,0b00100,0b00000],
    '-': [0b00000,0b00000,0b00000,0b11111,0b00000,0b00000,0b00000],
    '_': [0b00000,0b00000,0b00000,0b00000,0b00000,0b00000,0b11111],
    '/': [0b00001,0b00010,0b00010,0b00100,0b01000,0b01000,0b10000],
    '.': [0b00000,0b00000,0b00000,0b00000,0b00000,0b00110,0b00110],
}


def write_png_rgb(filepath, width, height, rgb_rows):
    """Write an 8-bit RGB PNG file from a list of bytearrays (each length width*3)."""
    def make_chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    raw = bytearray()
    for row in rgb_rows:
        raw.append(0)  # filter type 0
        raw.extend(row)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 6)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", idat)
        + make_chunk(b"IEND", b"")
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(png_bytes)


def draw_text_on_buffer(rows, width, height, text, x0, y0, scale, color):
    r, g, b = color
    cursor_x = x0
    for ch in text.upper():
        glyph = FONT_5X7.get(ch, FONT_5X7[' '])
        for gy in range(7):
            row_bits = glyph[gy]
            for gx in range(5):
                if (row_bits >> (4 - gx)) & 1:
                    for sy in range(scale):
                        py = y0 + gy * scale + sy
                        if 0 <= py < height:
                            row_buf = rows[py]
                            for sx in range(scale):
                                px = cursor_x + gx * scale + sx
                                if 0 <= px < width:
                                    idx = px * 3
                                    row_buf[idx] = r
                                    row_buf[idx + 1] = g
                                    row_buf[idx + 2] = b
        cursor_x += 6 * scale


def generate_placard_png(filepath, slot, exhibit_id, material_name):
    w, h = 512, 320
    bg = (238, 234, 224)
    border = (65, 58, 48)
    title_col = (25, 25, 28)
    sub_col = (90, 75, 55)

    rows = [bytearray(bg * w) for _ in range(h)]
    # Border frame
    bw = 10
    for y in range(h):
        for x in range(w):
            if x < bw or x >= w - bw or y < bw or y >= h - bw:
                idx = x * 3
                rows[y][idx:idx+3] = bytes(border)
            elif (20 <= x < w - 20 and (y == 20 or y == h - 21)) or (20 <= y < h - 20 and (x == 20 or x == w - 21)):
                idx = x * 3
                rows[y][idx:idx+3] = bytes(border)

    title = exhibit_id.replace("_", " ").upper()
    draw_text_on_buffer(rows, w, h, f"BAY {slot}", 40, 44, 4, sub_col)
    draw_text_on_buffer(rows, w, h, title, 40, 118, 5, title_col)
    draw_text_on_buffer(rows, w, h, f"MAT: {material_name}", 40, 215, 3, sub_col)
    write_png_rgb(filepath, w, h, rows)


def generate_porcelain_pattern_png(filepath):
    """Generate a blue-and-white porcelain motif PNG texture."""
    w, h = 512, 512
    rows = []
    for y in range(h):
        row = bytearray(w * 3)
        v = y / h
        for x in range(w):
            u = x / w
            # Classic blue-and-white floral/lattice wave bands
            band1 = abs(math.sin(v * math.pi * 6.0))
            wave = math.sin(u * math.pi * 16.0) * math.cos(v * math.pi * 12.0)
            medallion = math.cos(u * math.pi * 8.0) * math.cos(v * math.pi * 8.0)
            val = 0.0
            if v < 0.14 or v > 0.86 or (0.45 < v < 0.55):
                val = 0.85 if (int(u * 32) + int(v * 32)) % 2 == 0 else 0.15
            elif wave + 0.5 * medallion > 0.45:
                val = min(1.0, (wave + 0.5 * medallion - 0.45) * 2.2)
            elif band1 > 0.92:
                val = 0.75
            # Blend between porcelain white (242, 245, 250) and cobalt blue (28, 62, 145)
            r = int(242 * (1.0 - val) + 28 * val)
            g = int(245 * (1.0 - val) + 62 * val)
            b = int(250 * (1.0 - val) + 145 * val)
            idx = x * 3
            row[idx] = r
            row[idx + 1] = g
            row[idx + 2] = b
        rows.append(row)
    write_png_rgb(filepath, w, h, rows)


# ---------------------------------------------------------------------------
# Shader Node Helpers (lookup by node.type, never by localized name)
# ---------------------------------------------------------------------------
def get_or_create_material(name):
    if name in bpy.data.materials:
        mat = bpy.data.materials[name]
    else:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    return mat


def get_principled_bsdf(mat):
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def set_input_if_exists(node, candidates, value):
    for c in candidates:
        if c in node.inputs:
            node.inputs[c].default_value = value
            return True
    return False


def build_preview_materials():
    mats = {}

    # 1. Floor: dark polished floor
    m = get_or_create_material("MAT_floor")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.035, 0.035, 0.04, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.14)
    set_input_if_exists(bsdf, ["Coat Weight", "Clearcoat"], 0.35)
    m.diffuse_color = (0.035, 0.035, 0.04, 1.0)
    mats["floor"] = m

    # 2. Walls & Ceiling: matte charcoal
    m = get_or_create_material("MAT_wall")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.075, 0.078, 0.085, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.82)
    m.diffuse_color = (0.075, 0.078, 0.085, 1.0)
    mats["wall"] = m

    m = get_or_create_material("MAT_ceiling")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.045, 0.045, 0.05, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.9)
    m.diffuse_color = (0.045, 0.045, 0.05, 1.0)
    mats["ceiling"] = m

    # 3. Plinth: pale matte so caustics and glints read on it
    m = get_or_create_material("MAT_plinth")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.82, 0.80, 0.76, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.78)
    m.diffuse_color = (0.82, 0.80, 0.76, 1.0)
    mats["plinth"] = m

    # 4. Brass stanchion
    m = get_or_create_material("MAT_brass")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.85, 0.64, 0.22, 1.0))
    set_input_if_exists(bsdf, ["Metallic"], 1.0)
    set_input_if_exists(bsdf, ["Roughness"], 0.22)
    m.diffuse_color = (0.85, 0.64, 0.22, 1.0)
    mats["brass"] = m

    # 5. Red velvet rope
    m = get_or_create_material("MAT_velvet_red")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.48, 0.03, 0.05, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.88)
    set_input_if_exists(bsdf, ["Sheen Weight", "Sheen"], 0.85)
    m.diffuse_color = (0.48, 0.03, 0.05, 1.0)
    mats["velvet_red"] = m

    # 6. Bay emitter plane (non-emissive preview material so light isn't double-counted with Area light)
    m = get_or_create_material("MAT_emitter_plane_preview")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.95, 0.92, 0.85, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.4)
    set_input_if_exists(bsdf, ["Emission Strength"], 0.0)
    m.diffuse_color = (0.95, 0.92, 0.85, 1.0)
    mats["emitter_plane_preview"] = m

    # 7. Diffuse emitters (cove strips, stained-glass internal sphere, cloud backlight, bright panels)
    m = get_or_create_material("MAT_cove_emitter")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (1.0, 0.91, 0.80, 1.0))
    set_input_if_exists(bsdf, ["Emission Color"], (1.0, 0.91, 0.80, 1.0))
    set_input_if_exists(bsdf, ["Emission Strength"], 0.65)
    m.diffuse_color = (1.0, 0.91, 0.80, 1.0)
    mats["cove_emitter"] = m

    m = get_or_create_material("MAT_cloud_backlight")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.95, 0.97, 1.0, 1.0))
    set_input_if_exists(bsdf, ["Emission Color"], (0.95, 0.97, 1.0, 1.0))
    set_input_if_exists(bsdf, ["Emission Strength"], 3.5)
    m.diffuse_color = (0.95, 0.97, 1.0, 1.0)
    mats["cloud_backlight"] = m

    m = get_or_create_material("MAT_stained_glass_bulb")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (1.0, 0.92, 0.75, 1.0))
    set_input_if_exists(bsdf, ["Emission Color"], (1.0, 0.92, 0.75, 1.0))
    set_input_if_exists(bsdf, ["Emission Strength"], 45.0)
    m.diffuse_color = (1.0, 0.92, 0.75, 1.0)
    mats["stained_glass_bulb"] = m

    m = get_or_create_material("MAT_bright_panel")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (1.0, 0.98, 0.95, 1.0))
    set_input_if_exists(bsdf, ["Emission Color"], (1.0, 0.98, 0.95, 1.0))
    set_input_if_exists(bsdf, ["Emission Strength"], 14.0)
    m.diffuse_color = (1.0, 0.98, 0.95, 1.0)
    mats["bright_panel"] = m

    # 8. Exhibit preview materials (Principled BSDF)
    # Melitta: light warm ceramic
    m = get_or_create_material("MAT_EX_melitta")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.93, 0.90, 0.83, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.18)
    set_input_if_exists(bsdf, ["Coat Weight", "Clearcoat"], 0.6)
    m.diffuse_color = (0.93, 0.90, 0.83, 1.0)
    mats["melitta"] = m

    # Metal: hammered copper / warm brass
    m = get_or_create_material("MAT_EX_metal")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.88, 0.52, 0.30, 1.0))
    set_input_if_exists(bsdf, ["Metallic"], 1.0)
    set_input_if_exists(bsdf, ["Roughness"], 0.16)
    m.diffuse_color = (0.88, 0.52, 0.30, 1.0)
    mats["metal"] = m

    # Jade: translucent green with waxy coat
    m = get_or_create_material("MAT_EX_jade")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.14, 0.52, 0.32, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.22)
    set_input_if_exists(bsdf, ["Subsurface Weight", "Subsurface"], 0.65)
    set_input_if_exists(bsdf, ["Subsurface Scale"], 0.04)
    set_input_if_exists(bsdf, ["Coat Weight", "Clearcoat"], 0.7)
    set_input_if_exists(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.12)
    m.diffuse_color = (0.14, 0.52, 0.32, 1.0)
    mats["jade"] = m

    # Stained glass: reads per-face color attribute "panel_color" into Principled BSDF
    m = get_or_create_material("MAT_EX_stained_glass")
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "panel_color"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    if "Emission Color" in bsdf.inputs:
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 0.35
    set_input_if_exists(bsdf, ["Roughness"], 0.08)
    set_input_if_exists(bsdf, ["Transmission Weight", "Transmission"], 0.82)
    set_input_if_exists(bsdf, ["IOR"], 1.52)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = (0.85, 0.35, 0.20, 1.0)
    mats["stained_glass"] = m

    # Porcelain: white glazed body with blue-and-white image texture
    porcelain_png = os.path.join(TEXTURE_DIR, "porcelain_pattern.png")
    generate_porcelain_pattern_png(porcelain_png)
    m = get_or_create_material("MAT_EX_porcelain")
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img_name = os.path.basename(porcelain_png)
    if img_name in bpy.data.images:
        img = bpy.data.images[img_name]
        img.reload()
    else:
        img = bpy.data.images.load(porcelain_png)
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    set_input_if_exists(bsdf, ["Roughness"], 0.09)
    set_input_if_exists(bsdf, ["Coat Weight", "Clearcoat"], 0.9)
    set_input_if_exists(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.05)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = (0.75, 0.82, 0.95, 1.0)
    mats["porcelain"] = m

    # Crystal: clear high-dispersion glass
    m = get_or_create_material("MAT_EX_crystal")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.96, 0.98, 1.0, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.02)
    set_input_if_exists(bsdf, ["Transmission Weight", "Transmission"], 0.98)
    set_input_if_exists(bsdf, ["IOR"], 1.75)
    m.diffuse_color = (0.80, 0.92, 1.0, 0.5)
    mats["crystal"] = m

    # Cloud glass display case: clear architectural glass
    m = get_or_create_material("MAT_cloud_case_glass")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.94, 0.97, 1.0, 1.0))
    set_input_if_exists(bsdf, ["Roughness"], 0.03)
    set_input_if_exists(bsdf, ["Transmission Weight", "Transmission"], 0.95)
    set_input_if_exists(bsdf, ["IOR"], 1.50)
    set_input_if_exists(bsdf, ["Alpha"], 0.18)
    m.diffuse_color = (0.85, 0.93, 1.0, 0.25)
    mats["glass_case"] = m

    # Cloud proxy: Volume Scatter with noise-modulated density and no surface
    m = get_or_create_material("MAT_EX_cloud_volume")
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Color"].default_value = (0.96, 0.97, 1.0, 1.0)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 6.0
    math_mul = nt.nodes.new("ShaderNodeMath")
    math_mul.operation = 'MULTIPLY'
    math_mul.inputs[1].default_value = 38.0
    nt.links.new(noise.outputs["Fac"], math_mul.inputs[0])
    nt.links.new(math_mul.outputs["Value"], vol.inputs["Density"])
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    m.diffuse_color = (0.95, 0.97, 1.0, 0.6)
    mats["cloud_volume"] = m

    # Thin film (if enabled)
    m = get_or_create_material("MAT_EX_thin_film")
    bsdf = get_principled_bsdf(m)
    set_input_if_exists(bsdf, ["Base Color"], (0.55, 0.70, 0.92, 1.0))
    set_input_if_exists(bsdf, ["Metallic"], 0.6)
    set_input_if_exists(bsdf, ["Roughness"], 0.08)
    m.diffuse_color = (0.55, 0.70, 0.92, 1.0)
    mats["thin_film"] = m

    return mats


def create_placard_material(slot, exhibit_id, renderer_material):
    png_path = os.path.join(TEXTURE_DIR, f"placard_{exhibit_id}.png")
    generate_placard_png(png_path, slot, exhibit_id, renderer_material)
    mat_name = f"MAT_placard_{exhibit_id}"
    m = get_or_create_material(mat_name)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img_name = os.path.basename(png_path)
    if img_name in bpy.data.images:
        img = bpy.data.images[img_name]
        img.reload()
    else:
        img = bpy.data.images.load(png_path)
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    set_input_if_exists(bsdf, ["Roughness"], 0.6)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = (0.92, 0.90, 0.86, 1.0)
    return m


# ---------------------------------------------------------------------------
# Geometry Builders: Analytic Primitives, Stanchion, and Sagging Velvet Rope
# ---------------------------------------------------------------------------
def ensure_analytic_primitive_meshes():
    """Create canonical unmodified default Blender primitive meshes (cube size 2, plane size 2, sphere r=1)."""
    prims = {}

    # Cube [-1, 1]^3
    if "MESH_PRIM_CUBE" in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes["MESH_PRIM_CUBE"])
    bpy.ops.mesh.primitive_cube_add(size=2.0, calc_uvs=True, location=(0, 0, 0))
    obj = bpy.context.active_object
    mesh = obj.data
    mesh.name = "MESH_PRIM_CUBE"
    for p in mesh.polygons:
        p.use_smooth = False
    bpy.data.objects.remove(obj, do_unlink=True)
    prims["CUBE"] = mesh

    # Plane [-1, 1]^2
    if "MESH_PRIM_PLANE" in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes["MESH_PRIM_PLANE"])
    bpy.ops.mesh.primitive_plane_add(size=2.0, calc_uvs=True, location=(0, 0, 0))
    obj = bpy.context.active_object
    mesh = obj.data
    mesh.name = "MESH_PRIM_PLANE"
    for p in mesh.polygons:
        p.use_smooth = False
    bpy.data.objects.remove(obj, do_unlink=True)
    prims["PLANE"] = mesh

    # Sphere radius 1.0
    if "MESH_PRIM_SPHERE" in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes["MESH_PRIM_SPHERE"])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0, calc_uvs=True, location=(0, 0, 0))
    obj = bpy.context.active_object
    mesh = obj.data
    mesh.name = "MESH_PRIM_SPHERE"
    for p in mesh.polygons:
        p.use_smooth = False
    bpy.data.objects.remove(obj, do_unlink=True)
    prims["SPHERE"] = mesh

    return prims


def build_stanchion_mesh(post_height=0.95, radial_segments=48):
    """Build a finely tessellated brass stanchion mesh with UVs and flat shading."""
    if "MESH_stanchion" in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes["MESH_stanchion"])

    mesh = bpy.data.meshes.new("MESH_stanchion")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Profile points (radius, z): weighted base, tapered collar, post shaft, rope ring, top ball finial
    h = post_height
    profile = [
        (0.000, 0.000),
        (0.145, 0.000),
        (0.145, 0.018),
        (0.135, 0.028),
        (0.045, 0.045),
        (0.024, 0.065),
        (0.024, h - 0.110),
        (0.040, h - 0.102),
        (0.040, h - 0.092),
        (0.024, h - 0.084),
        (0.024, h - 0.065),
    ]
    # Add spherical finial at top (center at z = h - 0.032, radius 0.032)
    finial_r = 0.032
    finial_cz = h - finial_r
    for i in range(1, 10):
        ang = -math.pi * 0.35 + (math.pi * 0.85) * (i / 9.0)
        r = max(0.0001, finial_r * math.cos(ang))
        z = finial_cz + finial_r * math.sin(ang)
        profile.append((r, z))
    profile.append((0.0, h))

    # Compute cumulative arc length for V coordinate
    arc = [0.0]
    for i in range(1, len(profile)):
        dr = profile[i][0] - profile[i - 1][0]
        dz = profile[i][1] - profile[i - 1][1]
        arc.append(arc[-1] + math.hypot(dr, dz))
    total_arc = max(arc[-1], 1e-6)
    v_coords = [a / total_arc for a in arc]

    rings = []
    for r, z in profile:
        ring = []
        for s in range(radial_segments):
            theta = (2.0 * math.pi * s) / radial_segments
            ring.append(bm.verts.new((r * math.cos(theta), r * math.sin(theta), z)))
        rings.append(ring)

    bm.verts.ensure_lookup_table()
    for i in range(len(profile) - 1):
        v0 = v_coords[i]
        v1 = v_coords[i + 1]
        for s in range(radial_segments):
            s_next = (s + 1) % radial_segments
            u0 = s / radial_segments
            u1 = (s + 1) / radial_segments
            v_a = rings[i][s]
            v_b = rings[i][s_next]
            v_c = rings[i + 1][s_next]
            v_d = rings[i + 1][s]
            face = bm.faces.new((v_a, v_b, v_c, v_d))
            face.smooth = False
            face.loops[0][uv_layer].uv = (u0, v0)
            face.loops[1][uv_layer].uv = (u1, v0)
            face.loops[2][uv_layer].uv = (u1, v1)
            face.loops[3][uv_layer].uv = (u0, v1)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = False
    mesh.update()
    return mesh


def build_rope_mesh(span_length=1.80, rope_height=0.85, sag=0.08, tube_radius=0.018,
                    length_segments=48, radial_sides=28):
    """
    Build one canonical sagging catenary tube mesh along the X axis from -span/2 to +span/2
    at Y=0, with endpoints at Z=rope_height and midpoint sagging by `sag`.
    Reused as a linked duplicate for every span of every bay enclosure.
    """
    if "MESH_rope" in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes["MESH_rope"])

    mesh = bpy.data.meshes.new("MESH_rope")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Trim ends slightly so rope meets the stanchion collar cleanly at radius ~0.024m
    half_x = (span_length * 0.5) - 0.022

    # Compute centerline points and tangents
    centers = []
    for i in range(length_segments + 1):
        t = (i / length_segments) * 2.0 - 1.0  # [-1, +1]
        x = t * half_x
        # Catenary / parabolic sag curve: 0 at t=+-1, -sag at t=0
        z = rope_height - sag * (1.0 - t * t)
        centers.append(Vector((x, 0.0, z)))

    rings = []
    for i, c in enumerate(centers):
        if i == 0:
            tangent = (centers[1] - centers[0]).normalized()
        elif i == len(centers) - 1:
            tangent = (centers[-1] - centers[-2]).normalized()
        else:
            tangent = (centers[i + 1] - centers[i - 1]).normalized()

        # Frame perpendicular to tangent in X-Z plane
        normal_y = Vector((0.0, 1.0, 0.0))
        binormal = tangent.cross(normal_y).normalized()

        ring = []
        for s in range(radial_sides):
            phi = (2.0 * math.pi * s) / radial_sides
            pt = c + tube_radius * (math.cos(phi) * normal_y + math.sin(phi) * binormal)
            ring.append(bm.verts.new(pt))
        rings.append(ring)

    bm.verts.ensure_lookup_table()
    for i in range(length_segments):
        u0 = i / length_segments
        u1 = (i + 1) / length_segments
        for s in range(radial_sides):
            s_next = (s + 1) % radial_sides
            v0 = s / radial_sides
            v1 = (s + 1) / radial_sides
            face = bm.faces.new((rings[i][s], rings[i + 1][s], rings[i + 1][s_next], rings[i][s_next]))
            face.smooth = False
            face.loops[0][uv_layer].uv = (u0, v0)
            face.loops[1][uv_layer].uv = (u1, v0)
            face.loops[2][uv_layer].uv = (u1, v1)
            face.loops[3][uv_layer].uv = (u0, v1)

    # Cap both ends with UV-mapped fans
    for end_idx, u_cap, flip in [(0, 0.0, True), (length_segments, 1.0, False)]:
        c_vert = bm.verts.new(centers[end_idx])
        ring = rings[end_idx]
        for s in range(radial_sides):
            s_next = (s + 1) % radial_sides
            verts = (c_vert, ring[s_next], ring[s]) if flip else (c_vert, ring[s], ring[s_next])
            f = bm.faces.new(verts)
            f.smooth = False
            f.loops[0][uv_layer].uv = (0.5, 0.5)
            f.loops[1][uv_layer].uv = (0.5 + 0.5 * math.cos(2 * math.pi * s_next / radial_sides),
                                       0.5 + 0.5 * math.sin(2 * math.pi * s_next / radial_sides))
            f.loops[2][uv_layer].uv = (0.5 + 0.5 * math.cos(2 * math.pi * s / radial_sides),
                                       0.5 + 0.5 * math.sin(2 * math.pi * s / radial_sides))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = False
    mesh.update()
    return mesh


def create_stained_glass_color_mesh(source_mesh, name="MESH_stained_glass_colored"):
    """Create a mesh copy of TEAPOT_LOW with a random stained-glass jewel color per face."""
    if name in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes[name])
    m = source_mesh.copy()
    m.name = name
    for p in m.polygons:
        p.use_smooth = False

    if "panel_color" in m.color_attributes:
        m.color_attributes.remove(m.color_attributes["panel_color"])
    attr = m.color_attributes.new(name="panel_color", type='FLOAT_COLOR', domain='CORNER')

    palette = [
        (0.88, 0.16, 0.14, 1.0),  # ruby red
        (0.95, 0.58, 0.10, 1.0),  # amber gold
        (0.14, 0.42, 0.86, 1.0),  # cobalt blue
        (0.12, 0.68, 0.34, 1.0),  # emerald green
        (0.62, 0.20, 0.78, 1.0),  # amethyst purple
        (0.15, 0.74, 0.78, 1.0),  # turquoise
        (0.92, 0.78, 0.15, 1.0),  # warm yellow
    ]
    rng = random.Random(42)
    for poly in m.polygons:
        col = palette[rng.randrange(len(palette))]
        for loop_idx in poly.loop_indices:
            attr.data[loop_idx].color = col
    m.update()
    return m


# ---------------------------------------------------------------------------
# Room Dimension & Slot Derivation from PARAMS
# ---------------------------------------------------------------------------
def derive_room_layout(params):
    n_back = params["bays"]["back"]
    n_left = params["bays"]["left"]
    n_right = params["bays"]["right"]
    spacing = params["bay_spacing"]
    plinth_half = params["plinth"]["top"] * 0.5
    rope_half = plinth_half + params["rope"]["clearance"]  # 0.35 + 0.55 = 0.90 m
    bay_wall_offset = rope_half + 0.10                     # 1.00 m from wall inner surface to plinth center
    corner_wall_margin = 1.00                              # 1.00 m from outer back-bay rope to side wall
    corner_bay_gap = 0.50                                  # 0.50 m gap between side-bay rope and back-bay rope

    # Room Width W along X (centered at X=0)
    back_span_half = 0.5 * max(0, n_back - 1) * spacing
    half_width = back_span_half + rope_half + corner_wall_margin  # 2.6 + 0.90 + 1.00 = 4.50 m
    room_width = 2.0 * half_width                                 # 9.00 m

    # Side bay X coordinates
    x_left = -half_width + bay_wall_offset                        # -3.50 m
    x_right = half_width - bay_wall_offset                        # +3.50 m

    # Camera main FOV and position (Y=0 is inner face of front wall behind camera)
    cam_cfg = params["camera_main"]
    cam_y = cam_cfg["wall_gap"]                                   # 1.00 m
    cam_z = cam_cfg["eye_height"]                                 # 1.60 m
    focal_mm = cam_cfg.get("focal_length_mm", 20.0)
    sensor_mm = cam_cfg["sensor_width_mm"]                        # 36.0 mm
    tan_half_hfov = (0.5 * sensor_mm) / focal_mm                  # 18 / 20 = 0.90
    hfov_deg = math.degrees(2.0 * math.atan(tan_half_hfov))       # 83.97 deg
    vfov_deg = math.degrees(2.0 * math.atan(tan_half_hfov * (1080.0 / 2560.0)))  # 41.58 deg

    # Position nearest side bays (L1, R1) so they sit inside central ~80% of horizontal frame
    frame_fraction = cam_cfg.get("frame_fraction", 0.80)
    half_frame_at_first_side = abs(x_right) / frame_fraction      # 3.50 / 0.80 = 4.375 m
    dist_y_first_side = round(half_frame_at_first_side / tan_half_hfov, 2)  # 4.86 m
    y_first_side = cam_y + dist_y_first_side                      # 5.86 m

    n_side_max = max(n_left, n_right)
    y_last_side = y_first_side + max(0, n_side_max - 1) * spacing # 8.46 m

    # Back wall bays Y coordinate (rope_half + corner_bay_gap + rope_half = 2.30 m past last side bay)
    y_back_bays = round(y_last_side + 2.0 * rope_half + corner_bay_gap, 2)  # 10.76 m
    room_depth = round(y_back_bays + bay_wall_offset, 2)                    # 11.76 m
    ceiling_height = params["ceiling_height"]                               # 3.60 m

    # Slot dictionary: slot -> {location, wall, bay_rot_z, default_yaw_deg}
    slots = {}
    for i in range(n_back):
        slot_name = f"B{i + 1}"
        bx = -back_span_half + i * spacing
        by = y_back_bays
        # Spout (+X) toward room centerline (or viewer's right for center slot), turned 25 deg toward camera (-Y)
        default_yaw = -25.0 if bx <= 1e-4 else -155.0
        slots[slot_name] = {
            "slot": slot_name,
            "wall": "back",
            "x": round(bx, 4),
            "y": round(by, 4),
            "bay_rot_z": 0.0,
            "default_yaw_deg": default_yaw,
        }

    for i in range(n_left):
        slot_name = f"L{i + 1}"
        bx = x_left
        by = y_first_side + i * spacing
        slots[slot_name] = {
            "slot": slot_name,
            "wall": "left",
            "x": round(bx, 4),
            "y": round(by, 4),
            "bay_rot_z": math.pi * 0.5,  # open rope side (-X) against left wall
            "default_yaw_deg": -25.0,    # toward centerline (+X) and 25 deg toward camera (-Y)
        }

    for i in range(n_right):
        slot_name = f"R{i + 1}"
        bx = x_right
        by = y_first_side + i * spacing
        slots[slot_name] = {
            "slot": slot_name,
            "wall": "right",
            "x": round(bx, 4),
            "y": round(by, 4),
            "bay_rot_z": -math.pi * 0.5, # open rope side (+X) against right wall
            "default_yaw_deg": -155.0,   # toward centerline (-X) and 25 deg toward camera (-Y)
        }

    return {
        "width": room_width,
        "half_width": half_width,
        "depth": room_depth,
        "height": ceiling_height,
        "rope_half": rope_half,
        "bay_wall_offset": bay_wall_offset,
        "cam_pos": (0.0, cam_y, cam_z),
        "focal_mm": focal_mm,
        "sensor_mm": sensor_mm,
        "hfov_deg": hfov_deg,
        "vfov_deg": vfov_deg,
        "slots": slots,
    }


# ---------------------------------------------------------------------------
# Main Scene Builder
# ---------------------------------------------------------------------------
def build_gallery(params=PARAMS):
    os.makedirs(TEXTURE_DIR, exist_ok=True)
    os.makedirs(BLEND_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'METERS'

    scene.render.resolution_x = 2560
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = 1.0
    scene.render.pixel_aspect_y = 1.0

    # Ensure dark world background (no environment lighting)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg_node = next((n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg_node:
        bg_node.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
        bg_node.inputs[1].default_value = 0.0

    # 1. Ensure Collection skeleton
    col_names = [
        "ASSETS",
        "ROOM",
        "BAY_TEMPLATE",
        "EXHIBITS",
        "LIGHT_dim",
        "LIGHT_bright",
        "PREVIEW_ONLY_LIGHTS",
        "PAINTINGS",
        "DRESSING",
        "CAMERAS",
    ]
    cols = {}
    for cname in col_names:
        if cname not in bpy.data.collections:
            c = bpy.data.collections.new(cname)
            scene.collection.children.link(c)
        cols[cname] = bpy.data.collections[cname]

    # Remove default "Collection" if present and empty
    if "Collection" in bpy.data.collections and len(bpy.data.collections["Collection"].objects) == 0:
        bpy.data.collections.remove(bpy.data.collections["Collection"])

    # 2. Ensure ASSETS are imported and scaled idempotently
    assets_col = cols["ASSETS"]
    teapot_scale = params["teapot_scale"]
    crystal_norm = (3.0 / 0.75645) if params.get("normalize_crystal_to_3_units", True) else 1.0

    for key, fname in MESH_FILES.items():
        fpath = os.path.join(MESH_DIR, fname)
        if not os.path.exists(fpath):
            continue
        if key not in bpy.data.objects:
            bpy.ops.wm.obj_import(
                filepath=fpath,
                forward_axis='Y',
                up_axis='Z',
                use_split_objects=False,
                use_split_groups=False,
            )
            obj = bpy.context.selected_objects[0]
            obj.name = key
            obj.data.name = key
            for uc in list(obj.users_collection):
                uc.objects.unlink(obj)
            assets_col.objects.link(obj)
            obj["applied_scale"] = 1.0

        obj = bpy.data.objects[key]
        target_scale = teapot_scale * (crystal_norm if key == "TEAPOT_CRYSTAL" else 1.0)
        cur_scale = float(obj.get("applied_scale", 1.0))
        ratio = target_scale / cur_scale
        if abs(ratio - 1.0) > 1e-7:
            obj.data.transform(Matrix.Scale(ratio, 4))
            obj.data.update()
            obj["applied_scale"] = target_scale
        for poly in obj.data.polygons:
            poly.use_smooth = False
        obj.location = (0.0, 0.0, 0.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.scale = (1.0, 1.0, 1.0)

    assets_col.hide_viewport = True
    assets_col.hide_render = True

    # 3. Clear all generated collections (everything except ASSETS)
    for cname in col_names:
        if cname == "ASSETS":
            continue
        c = cols[cname]
        for obj in list(c.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

    # Clean up orphan lights and cameras
    for l in list(bpy.data.lights):
        if l.users == 0:
            bpy.data.lights.remove(l)
    for cam in list(bpy.data.cameras):
        if cam.users == 0:
            bpy.data.cameras.remove(cam)

    # 4. Validate exhibit count vs slots
    layout = derive_room_layout(params)
    slots = layout["slots"]
    enabled_exhibits = [ex for ex in params["exhibits"] if ex.get("enabled", True)]
    if len(enabled_exhibits) > len(slots):
        raise ValueError(f"More enabled exhibits ({len(enabled_exhibits)}) than slots ({len(slots)})!")

    exhibit_by_slot = {}
    for ex in enabled_exhibits:
        sname = ex.get("slot")
        if sname not in slots:
            raise ValueError(f"Exhibit '{ex['id']}' assigned to invalid slot '{sname}'")
        exhibit_by_slot[sname] = ex

    # 5. Build Materials and Canonical Meshes
    mats = build_preview_materials()
    prims = ensure_analytic_primitive_meshes()
    stanchion_mesh = build_stanchion_mesh(
        post_height=params["rope"]["post_height"],
        radial_segments=48,
    )
    rope_span = 2.0 * layout["rope_half"]  # 1.80 m
    rope_mesh = build_rope_mesh(
        span_length=rope_span,
        rope_height=params["rope"]["rope_height"],
        sag=params["rope"]["sag"],
        tube_radius=0.018,
        length_segments=48,
        radial_sides=28,
    )

    def spawn_mesh_obj(name, mesh_data, col, location, rotation=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0),
                       mat=None, props=None):
        obj = bpy.data.objects.new(name, mesh_data)
        col.objects.link(obj)
        obj.location = location
        obj.rotation_euler = rotation
        obj.scale = scale
        if mat is not None:
            if len(obj.data.materials) == 0:
                # Assign material on object slot so shared primitive meshes can have distinct materials per object!
                obj.data.materials.append(mat)
            obj.material_slots[0].link = 'OBJECT'
            obj.material_slots[0].material = mat
        if props:
            for k, v in props.items():
                if v is not None:
                    obj[k] = v
        return obj

    # 6. Build Room Shell (Floor, Ceiling, 4 Walls as analytic PRIM_CUBE slabs)
    W = layout["width"]
    hw = layout["half_width"]
    D = layout["depth"]
    H = layout["height"]
    ht = 0.10  # half-thickness of room slabs (0.20 m thick)
    room_col = cols["ROOM"]

    spawn_mesh_obj(
        "PRIM_CUBE_floor", prims["CUBE"], room_col,
        location=(0.0, D * 0.5, -ht),
        scale=(hw + 2 * ht, D * 0.5 + 2 * ht, ht),
        mat=mats["floor"],
        props={"renderer_material": "floor"},
    )
    spawn_mesh_obj(
        "PRIM_CUBE_ceiling", prims["CUBE"], room_col,
        location=(0.0, D * 0.5, H + ht),
        scale=(hw + 2 * ht, D * 0.5 + 2 * ht, ht),
        mat=mats["ceiling"],
        props={"renderer_material": "ceiling"},
    )
    spawn_mesh_obj(
        "PRIM_CUBE_wall_back", prims["CUBE"], room_col,
        location=(0.0, D + ht, H * 0.5),
        scale=(hw + 2 * ht, ht, H * 0.5),
        mat=mats["wall"],
        props={"renderer_material": "wall", "wall_id": "back"},
    )
    spawn_mesh_obj(
        "PRIM_CUBE_wall_front", prims["CUBE"], room_col,
        location=(0.0, -ht, H * 0.5),
        scale=(hw + 2 * ht, ht, H * 0.5),
        mat=mats["wall"],
        props={"renderer_material": "wall", "wall_id": "front"},
    )
    spawn_mesh_obj(
        "PRIM_CUBE_wall_left", prims["CUBE"], room_col,
        location=(-hw - ht, D * 0.5, H * 0.5),
        scale=(ht, D * 0.5, H * 0.5),
        mat=mats["wall"],
        props={"renderer_material": "wall", "wall_id": "left"},
    )
    spawn_mesh_obj(
        "PRIM_CUBE_wall_right", prims["CUBE"], room_col,
        location=(hw + ht, D * 0.5, H * 0.5),
        scale=(ht, D * 0.5, H * 0.5),
        mat=mats["wall"],
        props={"renderer_material": "wall", "wall_id": "right"},
    )

    # 7. Build Canonical Bay Template in BAY_TEMPLATE (hidden at origin)
    tpl_col = cols["BAY_TEMPLATE"]
    plinth_hx = params["plinth"]["top"] * 0.5     # 0.35 m
    plinth_hz = params["plinth"]["height"] * 0.5  # 0.45 m
    plinth_top_z = params["plinth"]["height"]     # 0.90 m
    rh = layout["rope_half"]                      # 0.90 m
    em_half = params["emitter"]["size"] * 0.5     # 0.06 m
    em_z = plinth_top_z + params["emitter"].get("height_above_plinth", 2.55)  # 3.45 m

    spawn_mesh_obj(
        "PRIM_CUBE_tpl_plinth", prims["CUBE"], tpl_col,
        location=(0.0, 0.0, plinth_hz),
        scale=(plinth_hx, plinth_hx, plinth_hz),
        mat=mats["plinth"],
        props={"renderer_material": "plinth"},
    )
    tpl_corners = [(-rh, -rh), (rh, -rh), (rh, rh), (-rh, rh)]
    for idx, (cx, cy) in enumerate(tpl_corners, 1):
        spawn_mesh_obj(
            f"STANCHION_tpl_{idx}", stanchion_mesh, tpl_col,
            location=(cx, cy, 0.0),
            mat=mats["brass"],
            props={"renderer_material": "brass", "placeholder_for": "M05"},
        )
    # u3 rope spans in local bay space (open side is +Y against wall): front (-Y), left (-X), right (+X)
    tpl_ropes = [
        ("front", (0.0, -rh, 0.0), 0.0),
        ("left",  (-rh, 0.0, 0.0), math.pi * 0.5),
        ("right", (rh,  0.0, 0.0), math.pi * 0.5),
    ]
    if params["rope"]["enclosure"] == "ring4":
        tpl_ropes.append(("back", (0.0, rh, 0.0), 0.0))
    for rname, rloc, rrot in tpl_ropes:
        spawn_mesh_obj(
            f"ROPE_tpl_{rname}", rope_mesh, tpl_col,
            location=rloc,
            rotation=(0.0, 0.0, rrot),
            mat=mats["velvet_red"],
            props={"renderer_material": "velvet_red", "placeholder_for": "M05"},
        )
    spawn_mesh_obj(
        "PRIM_PLANE_tpl_emitter", prims["PLANE"], tpl_col,
        location=(0.0, 0.0, em_z),
        rotation=(math.pi, 0.0, 0.0),  # +Z normal faces straight down (-Z)
        scale=(em_half, em_half, 1.0),
        mat=mats["emitter_plane_preview"],
        props={
            "renderer_material": "emitter_spot",
            "emission_color": params["emitter"]["color"],
            "emission_strength": float(params["emitter"]["strength"]),
            "lobe_exponent": int(params["emitter"]["lobe_exponent"]),
        },
    )
    spawn_mesh_obj(
        "PRIM_PLANE_tpl_placard", prims["PLANE"], tpl_col,
        location=(0.65, layout["bay_wall_offset"] - 0.005, 1.50),
        rotation=(math.pi * 0.5, 0.0, 0.0),
        scale=(0.14, 0.09, 1.0),
        mat=mats["plinth"],
        props={"renderer_material": "placard"},
    )
    tpl_col.hide_viewport = True
    tpl_col.hide_render = True

    # 8. Instantiate Bays per Slot (linked duplicates sharing mesh data)
    light_dim_col = cols["LIGHT_dim"]
    preview_lights_col = cols["PREVIEW_ONLY_LIGHTS"]

    for sname, sinfo in slots.items():
        ex = exhibit_by_slot.get(sname)
        if ex is None and params.get("skip_empty_bays", False):
            continue

        bx, by = sinfo["x"], sinfo["y"]
        rot_z = sinfo["bay_rot_z"]
        cos_z = math.cos(rot_z)
        sin_z = math.sin(rot_z)

        def to_world(lx, ly, lz):
            return (bx + lx * cos_z - ly * sin_z, by + lx * sin_z + ly * cos_z, lz)

        # Plinth
        spawn_mesh_obj(
            f"PRIM_CUBE_plinth_{sname}", prims["CUBE"], room_col,
            location=(bx, by, plinth_hz),
            rotation=(0.0, 0.0, rot_z),
            scale=(plinth_hx, plinth_hx, plinth_hz),
            mat=mats["plinth"],
            props={"renderer_material": "plinth", "slot": sname},
        )

        # 4 Brass Stanchions
        for idx, (cx, cy) in enumerate(tpl_corners, 1):
            spawn_mesh_obj(
                f"STANCHION_{sname}_{idx}", stanchion_mesh, room_col,
                location=to_world(cx, cy, 0.0),
                rotation=(0.0, 0.0, rot_z),
                mat=mats["brass"],
                props={"renderer_material": "brass", "slot": sname, "placeholder_for": "M05"},
            )

        # Velvet Rope Spans
        for rname, (rx, ry, rz), rrot in tpl_ropes:
            spawn_mesh_obj(
                f"ROPE_{sname}_{rname}", rope_mesh, room_col,
                location=to_world(rx, ry, rz),
                rotation=(0.0, 0.0, rot_z + rrot),
                mat=mats["velvet_red"],
                props={"renderer_material": "velvet_red", "slot": sname, "placeholder_for": "M05"},
            )

        # Placard on Wall beside the Bay (for side walls, place toward +Y so R1 and L1 are symmetric and inside CAM_main frame)
        ex_id = ex["id"] if ex else "empty"
        ex_mat_name = ex["renderer_material"] if ex else "none"
        placard_mat = create_placard_material(sname, ex_id, ex_mat_name)
        placard_lx = -0.65 if sinfo["wall"] == "right" else 0.65
        spawn_mesh_obj(
            f"PRIM_PLANE_placard_{sname}", prims["PLANE"], room_col,
            location=to_world(placard_lx, layout["bay_wall_offset"] - 0.005, 1.50),
            rotation=(math.pi * 0.5, 0.0, rot_z),
            scale=(0.14, 0.09, 1.0),
            mat=placard_mat,
            props={
                "renderer_material": "placard",
                "slot": sname,
                "exhibit_id": ex_id,
                "texture": f"assets/textures/placard_{ex_id}.png",
            },
        )

        # Emitter Plane in LIGHT_dim (aimed straight down at plinth top center)
        em_pos = Vector((bx, by, em_z))
        target_pos = Vector((bx, by, plinth_top_z))
        aim_dir = (target_pos - em_pos).normalized()  # (0, 0, -1)
        # PRIM_PLANE emits from its +Z side -> rotate 180 deg around X so local +Z points along (0, 0, -1)
        spawn_mesh_obj(
            f"PRIM_PLANE_emitter_{sname}", prims["PLANE"], light_dim_col,
            location=(bx, by, em_z),
            rotation=(math.pi, 0.0, 0.0),
            scale=(em_half, em_half, 1.0),
            mat=mats["emitter_plane_preview"],
            props={
                "renderer_material": "emitter_spot",
                "slot": sname,
                "emission_color": params["emitter"]["color"],
                "emission_strength": float(params["emitter"]["strength"]),
                "lobe_exponent": int(params["emitter"]["lobe_exponent"]),
                "aim_direction": [round(aim_dir.x, 4), round(aim_dir.y, 4), round(aim_dir.z, 4)],
            },
        )

        # Co-located Blender Area Light in PREVIEW_ONLY_LIGHTS
        ldata = bpy.data.lights.new(name=f"PREVIEW_AREA_{sname}", type='AREA')
        ldata.shape = 'SQUARE'
        ldata.size = params["emitter"]["size"]
        ldata.color = tuple(params["emitter"]["color"])
        ldata.energy = float(params["emitter"].get("preview_watts", 85.0))
        if hasattr(ldata, "spread"):
            # Cosine power n=100 has half-power half-angle ~6.75 deg (~0.3m half-power radius on plinth)
            ldata.spread = math.radians(18.0)
        lobj = bpy.data.objects.new(name=f"PREVIEW_AREA_{sname}", object_data=ldata)
        preview_lights_col.objects.link(lobj)
        lobj.location = (bx, by, em_z - 0.002)
        lobj.rotation_euler = (0.0, 0.0, 0.0)  # Blender Area light shoots along local -Z by default

    # 9. Place Exhibits in EXHIBITS Collection
    ex_col = cols["EXHIBITS"]
    stand_ins = params.get("stand_ins", {})

    for ex in enabled_exhibits:
        ex_id = ex["id"]
        sname = ex["slot"]
        sinfo = slots[sname]
        bx, by = sinfo["x"], sinfo["y"]
        yaw_deg = float(ex.get("yaw_deg", sinfo["default_yaw_deg"]))
        yaw_rad = math.radians(yaw_deg)
        req_mesh_key = ex["mesh"]
        rmat = ex["renderer_material"]
        needs_model = ex.get("needs_model")

        # Determine whether mesh file exists or falls back to stand-in
        actual_mesh_key = req_mesh_key
        used_stand_in = False
        if actual_mesh_key not in bpy.data.objects:
            actual_mesh_key = stand_ins.get(req_mesh_key, "TEAPOT_CRYSTAL")
            used_stand_in = True

        is_placeholder = bool(used_stand_in or (needs_model is not None))
        common_props = {
            "exhibit_id": ex_id,
            "slot": sname,
            "renderer_material": rmat,
            "placeholder": is_placeholder,
            "yaw_deg": yaw_deg,
        }
        if needs_model:
            common_props["needs_model"] = needs_model
            common_props["placeholder_for"] = needs_model

        # Special Exhibit 1: Cloud (cumulonimbus teapot in nested analytic glass cubes)
        if ex_id == "cloud":
            # Outer cube: 0.62 x 0.62 x 0.42 m (half-extent 0.31, 0.31, 0.21), fits on 0.70 x 0.70 m plinth top
            outer_hx, outer_hy, outer_hz = 0.31, 0.31, 0.21
            wall_t = params.get("case_wall_m", 0.01)
            inner_hx, inner_hy, inner_hz = outer_hx - wall_t, outer_hy - wall_t, outer_hz - wall_t
            case_cz = plinth_top_z + outer_hz  # 0.90 + 0.21 = 1.11 m

            spawn_mesh_obj(
                "PRIM_CUBE_case_outer", prims["CUBE"], ex_col,
                location=(bx, by, case_cz),
                rotation=(0.0, 0.0, 0.0),
                scale=(outer_hx, outer_hy, outer_hz),
                mat=mats["glass_case"],
                props={
                    "exhibit_id": "cloud",
                    "slot": sname,
                    "renderer_material": "glass_case_outer",
                    "placeholder": True,
                    "needs_model": "M07",
                    "placeholder_for": "M07",
                },
            )
            spawn_mesh_obj(
                "PRIM_CUBE_case_inner", prims["CUBE"], ex_col,
                location=(bx, by, case_cz),
                rotation=(0.0, 0.0, 0.0),
                scale=(inner_hx, inner_hy, inner_hz),
                mat=mats["glass_case"],
                props={
                    "exhibit_id": "cloud",
                    "slot": sname,
                    "renderer_material": "glass_case_inner_medium_bounds",
                    "placeholder": True,
                    "needs_model": "M07",
                    "placeholder_for": "M07",
                },
            )

            # CLOUD_PROXY: TEAPOT_LOW scaled by 0.80 so it has >= 0.05 m clearance on all 6 sides inside inner cube
            proxy_src = bpy.data.objects[actual_mesh_key].data
            proxy_scale = 0.80
            proxy_height = 3.0 * teapot_scale * proxy_scale  # 0.192 m
            proxy_z = case_cz - 0.5 * proxy_height           # 1.014 m (centered vertically at 1.11 m)
            proxy_props = dict(common_props)
            proxy_props["cloud_proxy"] = True
            spawn_mesh_obj(
                "CLOUD_PROXY", proxy_src, ex_col,
                location=(bx, by, proxy_z),
                rotation=(0.0, 0.0, yaw_rad),
                scale=(proxy_scale, proxy_scale, proxy_scale),
                mat=mats["cloud_volume"],
                props=proxy_props,
            )

            # Optional backlight emitter behind the case in LIGHT_dim for a silver-lining rim
            if params.get("cloud_backlight", True):
                spawn_mesh_obj(
                    "PRIM_PLANE_cloud_backlight", prims["PLANE"], light_dim_col,
                    location=(bx, by + outer_hy + 0.05, case_cz + 0.14),
                    rotation=(math.radians(125.0), 0.0, 0.0),  # angled down and forward (-Y, -Z) through the cloud top rim
                    scale=(0.09, 0.045, 1.0),
                    mat=mats["cloud_backlight"],
                    props={
                        "renderer_material": "emitter_diffuse",
                        "slot": sname,
                        "exhibit_id": "cloud",
                        "emission_color": [0.95, 0.97, 1.0],
                        "emission_strength": 12.0,
                        "lobe_exponent": 1,
                        "aim_direction": [0.0, -0.8192, -0.5736],
                    },
                )
            continue

        # Special Exhibit 2: Stained Glass (per-panel color attribute + optional thin shell + internal sphere light)
        if ex_id == "stained_glass":
            src_mesh = bpy.data.objects[actual_mesh_key].data
            colored_mesh = create_stained_glass_color_mesh(src_mesh, "MESH_stained_glass_colored")
            sg_obj = spawn_mesh_obj(
                "EX_stained_glass", colored_mesh, ex_col,
                location=(bx, by, plinth_top_z),
                rotation=(0.0, 0.0, yaw_rad),
                scale=(1.0, 1.0, 1.0),
                mat=mats["stained_glass"],
                props=common_props,
            )

            # Build thin-walled preview shell derivative named EX_stained_glass_thin (Solidify inward by glass_thickness_m)
            thin_mesh = colored_mesh.copy()
            thin_mesh.name = "MESH_stained_glass_thin"
            thin_obj = spawn_mesh_obj(
                "EX_stained_glass_thin", thin_mesh, ex_col,
                location=(bx, by, plinth_top_z),
                rotation=(0.0, 0.0, yaw_rad),
                scale=(1.0, 1.0, 1.0),
                mat=mats["stained_glass"],
                props=dict(common_props, derivative="solidify_inward_4mm"),
            )
            mod = thin_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            mod.thickness = params.get("glass_thickness_m", 0.004)
            mod.offset = -1.0  # inward
            bpy.context.view_layer.objects.active = thin_obj
            bpy.ops.object.modifier_apply(modifier=mod.name)
            for p in thin_obj.data.polygons:
                p.use_smooth = False

            show_thin = params.get("show_stained_glass_thin_shell", False)
            thin_obj.hide_viewport = not show_thin
            thin_obj.hide_render = not show_thin
            sg_obj.hide_viewport = show_thin
            sg_obj.hide_render = show_thin

            # Internal emissive sphere (PRIM_SPHERE, radius 0.02 m) at the center of the hollow interior
            bulb_z = plinth_top_z + 0.11  # center of 0.24 m tall teapot body
            spawn_mesh_obj(
                "PRIM_SPHERE_stained_glass_emitter", prims["SPHERE"], light_dim_col,
                location=(bx, by, bulb_z),
                scale=(0.02, 0.02, 0.02),
                mat=mats["stained_glass_bulb"],
                props={
                    "renderer_material": "emitter_diffuse",
                    "slot": sname,
                    "exhibit_id": "stained_glass",
                    "emission_color": [1.0, 0.92, 0.75],
                    "emission_strength": 45.0,
                    "lobe_exponent": 0,
                },
            )
            continue

        # Special Exhibit 3: Melitta (uses MELITTA mesh if present and enabled, else primitive stand-in)
        if ex_id == "melitta" and (not params.get("use_melitta_mesh", True) or "MELITTA" not in bpy.data.objects):
            # Primitive stand-in: ellipsoid body, cylinder spout, torus handle
            body_obj = spawn_mesh_obj(
                "PLACEHOLDER_M01_body", prims["SPHERE"], ex_col,
                location=(bx, by, plinth_top_z + 0.14),
                rotation=(0.0, 0.0, yaw_rad),
                scale=(0.12, 0.12, 0.14),
                mat=mats["melitta"],
                props=dict(common_props, placeholder=True, placeholder_for="M01"),
            )
            continue

        # Standard mesh exhibits (melitta, metal, jade, porcelain, crystal)
        src_obj = bpy.data.objects[actual_mesh_key]
        ex_mat = mats.get(rmat, mats["porcelain"])
        main_obj = spawn_mesh_obj(
            f"EX_{ex_id}", src_obj.data, ex_col,
            location=(bx, by, plinth_top_z),
            rotation=(0.0, 0.0, yaw_rad),
            scale=(1.0, 1.0, 1.0),
            mat=ex_mat,
            props=common_props,
        )

        # Only place separate lid if using the no-lid cavity mesh (TEAPOT_CAVITY_NOLID)
        if actual_mesh_key == "TEAPOT_CAVITY_NOLID" and "TEAPOT_CAVITY_LID" in bpy.data.objects:
            lid_src = bpy.data.objects["TEAPOT_CAVITY_LID"]
            lid_props = dict(common_props, part="lid")
            spawn_mesh_obj(
                f"EX_{ex_id}_lid", lid_src.data, ex_col,
                location=(bx, by, plinth_top_z),
                rotation=(0.0, 0.0, yaw_rad),
                scale=(1.0, 1.0, 1.0),
                mat=ex_mat,
                props=lid_props,
            )

    # 10. Build Cove Fill Strips in LIGHT_dim and Bright Comparison Lighting in LIGHT_bright
    # Faint ceiling cove strips along the 4 upper wall perimeters so enclosed room shadows don't go pitch black
    cove_z = H - 0.12
    cove_strips = [
        ("back",  (0.0, D - 0.08, cove_z),     (math.pi, 0.0, 0.0), (hw - 0.6, 0.04, 1.0)),
        ("front", (0.0, 0.08, cove_z),         (math.pi, 0.0, 0.0), (hw - 0.6, 0.04, 1.0)),
        ("left",  (-hw + 0.08, D * 0.5, cove_z), (math.pi, 0.0, 0.0), (0.04, D * 0.5 - 0.8, 1.0)),
        ("right", (hw - 0.08, D * 0.5, cove_z),  (math.pi, 0.0, 0.0), (0.04, D * 0.5 - 0.8, 1.0)),
    ]
    for cname, cloc, crot, cscale in cove_strips:
        spawn_mesh_obj(
            f"PRIM_PLANE_cove_{cname}", prims["PLANE"], light_dim_col,
            location=cloc,
            rotation=crot,
            scale=cscale,
            mat=mats["cove_emitter"],
            props={
                "renderer_material": "emitter_diffuse",
                "slot": f"cove_{cname}",
                "emission_color": [1.0, 0.93, 0.84],
                "emission_strength": 3.2,
                "lobe_exponent": 1,
                "aim_direction": [0.0, 0.0, -1.0],
            },
        )

    # LIGHT_bright: white-cube gallery overhead diffuse panels (disabled by default)
    light_bright_col = cols["LIGHT_bright"]
    panel_ys = [3.2, 6.4, 9.6]
    panel_xs = [-2.2, 2.2]
    p_idx = 1
    for py in panel_ys:
        for px in panel_xs:
            spawn_mesh_obj(
                f"PRIM_PLANE_bright_panel_{p_idx:02d}", prims["PLANE"], light_bright_col,
                location=(px, py, H - 0.05),
                rotation=(math.pi, 0.0, 0.0),
                scale=(1.1, 1.1, 1.0),
                mat=mats["bright_panel"],
                props={
                    "renderer_material": "emitter_diffuse",
                    "slot": f"bright_{p_idx:02d}",
                    "emission_color": [1.0, 0.98, 0.95],
                    "emission_strength": 14.0,
                    "lobe_exponent": 1,
                    "aim_direction": [0.0, 0.0, -1.0],
                },
            )
            p_idx += 1

    light_dim_col.hide_viewport = False
    light_dim_col.hide_render = False
    light_bright_col.hide_viewport = True
    light_bright_col.hide_render = True

    # 11. Build Cameras (CAM_main, CAM_close_<id>, CAM_overview_top, CAM_alt_front_ortho)
    cam_col = cols["CAMERAS"]

    def create_camera(name, location, target_pos, focal_mm=20.0, sensor_mm=36.0,
                      ortho=False, ortho_scale=12.0, fstop=2.8, dof_enabled=False):
        cdata = bpy.data.cameras.new(name=name)
        cdata.sensor_fit = 'HORIZONTAL'
        cdata.sensor_width = sensor_mm
        if ortho:
            cdata.type = 'ORTHO'
            cdata.ortho_scale = ortho_scale
        else:
            cdata.type = 'PERSP'
            cdata.lens = focal_mm
        cobj = bpy.data.objects.new(name=name, object_data=cdata)
        cam_col.objects.link(cobj)
        cobj.location = location

        loc_v = Vector(location)
        tgt_v = Vector(target_pos)
        direction = (tgt_v - loc_v).normalized()
        if abs(direction.z) > 0.999:
            # Top-down orthographic camera: look straight down -Z with camera +Y (top of frame) toward world +Y
            cobj.rotation_euler = (0.0, 0.0, 0.0) if direction.z < 0 else (math.pi, 0.0, 0.0)
        else:
            # Blender camera looks along local -Z with local +Y as screen-up -> track '-Z', up 'Y'
            rot_quat = direction.to_track_quat('-Z', 'Y')
            cobj.rotation_euler = rot_quat.to_euler('XYZ')

        focus_dist = (tgt_v - loc_v).length
        cdata.dof.use_dof = dof_enabled
        cdata.dof.focus_distance = focus_dist
        cdata.dof.aperture_fstop = fstop

        cobj["target"] = [round( tgt_v.x, 4), round(tgt_v.y, 4), round(tgt_v.z, 4)]
        cobj["focus_distance_m"] = round(focus_dist, 4)
        cobj["fstop"] = fstop
        cobj["camera_model"] = "thin_lens" if dof_enabled else "pinhole"
        return cobj

    # CAM_main: inside room on centerline, looking +Y (slightly pitched to center the 7 bays vertically)
    cam_main_loc = layout["cam_pos"]  # (0.0, 1.0, 1.6)
    cam_main_tgt = (0.0, D, 1.35)     # aimed along +Y centerline at exhibit/placard height
    cam_main = create_camera(
        "CAM_main",
        location=cam_main_loc,
        target_pos=cam_main_tgt,
        focal_mm=layout["focal_mm"],
        sensor_mm=layout["sensor_mm"],
        ortho=False,
        fstop=2.8,
        dof_enabled=False,
    )
    scene.camera = cam_main

    # CAM_close_<exhibit_id>: 3/4 view from viewer's side of the ropes, 85mm on 36mm sensor
    close_cfg = params["camera_close"]
    close_focal = float(close_cfg["focal_length_mm"])
    close_sensor = float(close_cfg["sensor_width_mm"])
    close_fstop = float(close_cfg["fstop"])
    close_dof = bool(close_cfg.get("dof_enabled", False))
    tan_half_close = (0.5 * close_sensor) / close_focal  # 18 / 85 = 0.211765

    for ex in enabled_exhibits:
        ex_id = ex["id"]
        sname = ex["slot"]
        sinfo = slots[sname]
        bx, by = sinfo["x"], sinfo["y"]
        wall = sinfo["wall"]

        # Target center of the exhibit above the plinth top (0.90 m)
        if ex_id == "cloud":
            tgt_z = plinth_top_z + 0.20  # center of glass case (1.10 m)
            ex_width = 0.72              # frame the full glass case + cloud cleanly
        elif ex_id == "melitta":
            tgt_z = plinth_top_z + 0.16  # 0.32 m tall Melitta teapot
            ex_width = 0.50
        else:
            tgt_z = plinth_top_z + 0.12  # 0.24 m tall Utah teapot
            ex_width = 0.48

        fill_frac = close_cfg.get("fill_fraction", 0.60)
        half_frame_w = 0.5 * (ex_width / fill_frac)
        horiz_dist = half_frame_w / tan_half_close  # ~1.89..2.83 m (outside the 0.90 m rope enclosure)

        # Viewer-side 3/4 azimuth angle (clear of ropes and adjacent bays, showing spout, body, and handle)
        if wall == "left":
            az = math.radians(-58.0)   # 3/4 view from central aisle (+X, -Y) toward L1/L2 (yaw=-25 deg)
        elif wall == "right":
            az = math.radians(-122.0)  # 3/4 view from central aisle (-X, -Y) toward R1/R2 (yaw=-155 deg)
        else:
            # Back wall (B1, B2, B3)
            if bx < -0.5:
                az = math.radians(-66.0)   # B1 (yaw=-25 deg): 3/4 view from viewer's side (-Y, +X)
            elif bx > 0.5:
                az = math.radians(-114.0)  # B3 (yaw=-155 deg): 3/4 view from viewer's side (-Y, -X)
            else:
                az = math.radians(-68.0)   # B2 (yaw=-25 deg): 3/4 view from viewer's front-right

        cam_x = bx + horiz_dist * math.cos(az)
        cam_y = by + horiz_dist * math.sin(az)
        # Camera height +0.26 m above exhibit center looks smoothly over the 0.85 m velvet rope
        cam_z = tgt_z + 0.26

        create_camera(
            f"CAM_close_{ex_id}",
            location=(round(cam_x, 4), round(cam_y, 4), round(cam_z, 4)),
            target_pos=(bx, by, tgt_z),
            focal_mm=close_focal,
            sensor_mm=close_sensor,
            ortho=False,
            fstop=close_fstop,
            dof_enabled=close_dof,
        )

    # CAM_overview_top: orthographic plan view from above ceiling
    create_camera(
        "CAM_overview_top",
        location=(0.0, D * 0.5, H + 4.0),
        target_pos=(0.0, D * 0.5, 0.0),
        ortho=True,
        ortho_scale=max(W * 1.25, D * (2560.0 / 1080.0) * 1.15),
    )

    # CAM_alt_front_ortho: orthographic front elevation looking +Y
    create_camera(
        "CAM_alt_front_ortho",
        location=(0.0, 0.5, H * 0.5),
        target_pos=(0.0, D, H * 0.5),
        ortho=True,
        ortho_scale=W * 1.08,
    )

    bpy.context.view_layer.update()
    print(f"Gallery build complete: Room {W:.2f}m x {D:.2f}m x {H:.2f}m, HFOV={layout['hfov_deg']:.2f} deg")
    return layout


if __name__ == "__main__":
    build_gallery(PARAMS)
