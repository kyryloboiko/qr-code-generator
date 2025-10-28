import qrcode
from qrcode.image.pil import PilImage 
from PIL import Image, ImageDraw, ImageColor, ImageOps
from qrcode.exceptions import DataOverflowError

def normalize_logo(img, target_size):
    """
    Scales and crops an image to the target size from the center.
    """
    print(f"...Normalizing logo to {target_size[0]}x{target_size[1]}...")
    return ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)

def draw_rounded_modules(img_qr_base, qr_object, box_size, border_size, fill_color, back_color, module_radius_ratio=0.5):
    """
    Draws modules with rounding on "outer" corners only,
    by checking neighboring modules.
    """
    draw = ImageDraw.Draw(img_qr_base)
    
    radius = int(box_size * module_radius_ratio)
    if radius > box_size // 2:
        radius = box_size // 2

    def get_state(r, c):
        """
        Safely get the state of a module (True/False).
        Returns False if out of bounds.
        """
        if not (0 <= r < qr_object.modules_count and 0 <= c < qr_object.modules_count):
            return False
        return qr_object.modules[r][c]

    for r in range(qr_object.modules_count):
        for c in range(qr_object.modules_count):
            
            x = (c + border_size) * box_size
            y = (r + border_size) * box_size
            
            # If module is empty (False), draw the background color and skip
            if not get_state(r, c):
                draw.rectangle((x, y, x + box_size, y + box_size), fill=back_color)
                continue 
            
            # Get state of 4 main neighbors
            up = get_state(r - 1, c)
            down = get_state(r + 1, c)
            left = get_state(r, c - 1)
            right = get_state(r, c + 1)
            
            # A. Draw the central cross (always)
            draw.rectangle(
                (x + radius, y, x + box_size - radius, y + box_size), 
                fill=fill_color
            )
            draw.rectangle(
                (x, y + radius, x + box_size, y + box_size - radius), 
                fill=fill_color
            )

            # B. Draw the 4 corners (conditionally)
            
            # Top-Left
            if up or left:
                draw.rectangle((x, y, x + radius, y + radius), fill=fill_color)
            else:
                draw.pieslice((x, y, x + (radius*2), y + (radius*2)), 180, 270, fill=fill_color)
            
            # Top-Right
            if up or right:
                draw.rectangle((x + box_size - radius, y, x + box_size, y + radius), fill=fill_color)
            else:
                draw.pieslice((x + box_size - (radius*2), y, x + box_size, y + (radius*2)), 270, 360, fill=fill_color)

            # Bottom-Left
            if down or left:
                draw.rectangle((x, y + box_size - radius, x + radius, y + box_size), fill=fill_color)
            else:
                draw.pieslice((x, y + box_size - (radius*2), x + (radius*2), y + box_size), 90, 180, fill=fill_color)

            # Bottom-Right
            if down or right:
                draw.rectangle((x + box_size - radius, y + box_size - radius, x + box_size, y + box_size), fill=fill_color)
            else:
                draw.pieslice((x + box_size - (radius*2), y + box_size - (radius*2), x + box_size, y + box_size), 0, 90, fill=fill_color)

    return img_qr_base


def generate_custom_qr(url, output_file, target_size, fill_color_str, eye_color_str, logo_path):
    
    # --- A. Anti-aliasing (Supersampling) Setup ---
    SUPERSAMPLING_FACTOR = 4 
    
    original_target_size = target_size 
    target_size = original_target_size * SUPERSAMPLING_FACTOR
    
    print(f"...Rendering at {SUPERSAMPLING_FACTOR}x size (~{target_size}px) for anti-aliasing...")

    # --- 0. Color configuration and constants ---
    try:
        fill_color = ImageColor.getrgb(fill_color_str)
        eye_color = ImageColor.getrgb(eye_color_str)
        white_color = (255, 255, 255)
    except ValueError as e:
        print(f"ERROR: Invalid color format '{e}'. Use names like 'red' or hex like '#FF0000'.")
        return

    BORDER_SIZE = 0
    LOGO_TARGET_SIZE = (512, 523)
    FIXED_VERSION = 6 
    
    VERSION_MODULES = {
        1: 21, 2: 25, 3: 29, 4: 33, 5: 37, 6: 41, 7: 45
    }

    if FIXED_VERSION not in VERSION_MODULES:
        print(f"ERROR: Unknown version {FIXED_VERSION}.")
        return

    modules_count = VERSION_MODULES[FIXED_VERSION]
    total_modules_with_border = modules_count + BORDER_SIZE * 2
    
    BOX_SIZE = max(1, target_size // total_modules_with_border)
    
    qr = qrcode.QRCode(
        version=FIXED_VERSION, 
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=BOX_SIZE,
        border=BORDER_SIZE,
    )
    qr.add_data(url)
    
    try:
        qr.make(fit=False)
    except DataOverflowError:
        print(f"ERROR: URL '{url[:20]}...' is too long for QR Version {FIXED_VERSION}.")
        print("Try increasing FIXED_VERSION in the code.")
        return

    # --- 3. "Cut out" the center for the logo ---
    try:
        logo_img = Image.open(logo_path)
    except FileNotFoundError:
        print(f"ERROR: Logo file '{logo_path}' not found.")
        return
    except Exception as e:
        print(f"ERROR opening logo: {e}")
        return

    # Scale logo size for supersampling
    scaled_logo_size = (
        LOGO_TARGET_SIZE[0] * SUPERSAMPLING_FACTOR, 
        LOGO_TARGET_SIZE[1] * SUPERSAMPLING_FACTOR
    )
    logo = normalize_logo(logo_img, scaled_logo_size)

    qr_width, qr_height = total_modules_with_border * BOX_SIZE, total_modules_with_border * BOX_SIZE
    
    logo_padding = 2 * SUPERSAMPLING_FACTOR # Scale padding as well
    
    logo_max_size = (qr_height // 4) - logo_padding 
    
    logo.thumbnail((logo_max_size, logo_max_size))
    logo_pos = ((qr_width - logo.width) // 2, (qr_height - logo.height) // 2)

    corner_radius = BOX_SIZE
    patch_radius = corner_radius // 2

    patch_left = logo_pos[0]
    patch_top = logo_pos[1]
    patch_right = logo_pos[0] + logo.width
    patch_bottom = logo_pos[1] + logo.height

    # Calculate module coordinates for logo area
    module_left_abs = patch_left // BOX_SIZE
    module_top_abs = patch_top // BOX_SIZE
    module_right_abs = (patch_right + BOX_SIZE - 1) // BOX_SIZE
    module_bottom_abs = (patch_bottom + BOX_SIZE - 1) // BOX_SIZE

    # "Clear" modules in the logo area
    for r_abs in range(module_top_abs, module_bottom_abs):
        for c_abs in range(module_left_abs, module_right_abs):
            r = r_abs - BORDER_SIZE
            c = c_abs - BORDER_SIZE
            if 0 <= r < qr.modules_count and 0 <= c < qr.modules_count:
                qr.modules[r][c] = False

    # --- 4. Render the image ---
    # Create a clean white canvas
    img_qr_base = Image.new(
        'RGB', 
        (qr_width, qr_height), 
        white_color
    )

    # Draw our custom "smart" rounded modules
    img_qr = draw_rounded_modules(
        img_qr_base, 
        qr, 
        BOX_SIZE, 
        BORDER_SIZE, 
        fill_color, 
        white_color,
        module_radius_ratio=0.5 # 0.5 = max rounding
    )

    # --- 5. MANUALLY PAINT THE EYES (position markers) ---
    width, height = img_qr.size
    border_px = BORDER_SIZE * BOX_SIZE
    eye_outer_size_px = 7 * BOX_SIZE
    eye_gap_size_px = 5 * BOX_SIZE
    eye_inner_size_px = 3 * BOX_SIZE
    
    eye_gap_offset_px = (eye_outer_size_px - eye_gap_size_px) // 2
    eye_inner_offset_px = (eye_outer_size_px - eye_inner_size_px) // 2

    # Create the custom eye image
    custom_eye = Image.new('RGB', (eye_outer_size_px, eye_outer_size_px), white_color)
    draw_eye_patch = ImageDraw.Draw(custom_eye)

    # Outer eye shape
    draw_eye_patch.rounded_rectangle(
        (0, 0, eye_outer_size_px, eye_outer_size_px), 
        radius=corner_radius, 
        fill=eye_color
    )
    # White gap
    draw_eye_patch.rounded_rectangle(
        (eye_gap_offset_px, eye_gap_offset_px, 
         eye_gap_offset_px + eye_gap_size_px, eye_gap_offset_px + eye_gap_size_px), 
        radius=corner_radius // 2,
        fill=white_color
    )
    # Inner pupil
    draw_eye_patch.rounded_rectangle(
        (eye_inner_offset_px, eye_inner_offset_px, 
         eye_inner_offset_px + eye_inner_size_px, eye_inner_offset_px + eye_inner_size_px), 
        radius=corner_radius // 3,
        fill=fill_color
    )

    # Top-left eye position
    box_tl_pos = (border_px, border_px)
    # Top-right eye position
    box_tr_pos = (width - border_px - eye_outer_size_px, border_px)
    # Bottom-left eye position
    box_bl_pos = (border_px, height - border_px - eye_outer_size_px)

    # Paste the custom eyes over the QR code
    draw_base = ImageDraw.Draw(img_qr)
    for box_pos in [box_tl_pos, box_tr_pos, box_bl_pos]:
        # Clear the area first to remove any modules
        clear_box = (
            box_pos[0], box_pos[1], 
            box_pos[0] + eye_outer_size_px, box_pos[1] + eye_outer_size_px
        )
        draw_base.rectangle(clear_box, fill=white_color)
        # Paste the eye
        img_qr.paste(custom_eye, box_pos)

    # --- 6. Add logo with a white background patch ---
    white_patch_layer = Image.new('RGBA', img_qr.size, (0, 0, 0, 0))
    draw_patch = ImageDraw.Draw(white_patch_layer)

    # Draw the rounded white patch behind the logo
    draw_patch.rounded_rectangle(
        (patch_left, patch_top, patch_right, patch_bottom), 
        radius=patch_radius, 
        fill=white_color
    )

    # Paste the white patch
    img_qr.paste(white_patch_layer, (0, 0), mask=white_patch_layer)
    # Paste the logo on top
    img_qr.paste(logo, logo_pos, mask=logo.convert('RGBA'))

    # --- 7. Anti-aliasing (Downsampling) and Saving ---
    
    # Calculate final (non-supersampled) size
    final_width = qr_width // SUPERSAMPLING_FACTOR
    final_height = qr_height // SUPERSAMPLING_FACTOR
    
    print(f"...Downsampling from {qr_width}x{qr_height}px to {final_width}x{final_height}px...")
    
    # Resize with high-quality filter for anti-aliasing
    img_qr = img_qr.resize(
        (final_width, final_height), 
        Image.Resampling.LANCZOS
    )

    img_qr.save(output_file)
    print(f"✅ Success! QR code (Ver: {FIXED_VERSION}, Size: {img_qr.width}x{img_qr.height}px) saved to: {output_file}")


# --- Main execution block ---
if __name__ == "__main__":
    
    print("--- 🎨 Custom QR Code Generator ---")
    print("Press Enter to use the default value.\n")

    # 1. URL (required)
    url_input = ""
    while not url_input:
        url_input = input("Enter URL (required): ").strip()
        if not url_input:
            print("ERROR: URL cannot be empty.")

    # 2. Size (default 2048)
    target_size_def = 2048
    target_size_input_str = input(f"Desired size (width) [{target_size_def}]: ").strip()
    if not target_size_input_str:
        target_size_input = target_size_def
    else:
        try:
            target_size_input = int(target_size_input_str)
        except ValueError:
            print(f"Invalid number. Using {target_size_def}.")
            target_size_input = target_size_def

    # 3. Module color (default black)
    fill_color_def = "black"
    fill_color_input = input(f"Module color (e.g. red, #FFFFFF) [{fill_color_def}]: ").strip()
    if not fill_color_input:
        fill_color_input = fill_color_def

    # 4. Eye color (default black)
    eye_color_def = "black"
    eye_color_input = input(f"Eye color (e.g. red, #FF0000) [{eye_color_def}]: ").strip()
    if not eye_color_input:
        eye_color_input = eye_color_def

    # 5. Logo path (default logo.png)
    logo_path_def = "logo.png"
    logo_path_input = input(f"Path to logo [{logo_path_def}]: ").strip()
    if not logo_path_input:
        logo_path_input = logo_path_def
        
    # 6. Output filename (default my_custom_qr.png)
    output_file_def = "my_custom_qr.png"
    output_file_input = input(f"Output filename [{output_file_def}]: ").strip()
    if not output_file_input:
        output_file_input = output_file_def
        
    print("\n...Generating QR code...")

    # Call the main function
    generate_custom_qr(
        url=url_input,
        output_file=output_file_input,
        target_size=target_size_input,
        fill_color_str=fill_color_input,
        eye_color_str=eye_color_input,
        logo_path=logo_path_input
    )
