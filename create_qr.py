import qrcode
from PIL import Image, ImageDraw, ImageColor
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer

def generate_custom_qr(url, output_file, target_size, fill_color_str, eye_color_str, logo_path):
    """
    Generate a customized QR code with a logo, rounded modules,
    custom colors and a target output size.
    (THIS FUNCTION REMAINS UNCHANGED IN LOGIC)
    """
    
    # --- 0. Color configuration and constants ---
    try:
        fill_color = ImageColor.getrgb(fill_color_str)
        eye_color = ImageColor.getrgb(eye_color_str)
        white_color = (255, 255, 255)
    except ValueError as e:
        print(f"ERROR: Invalid color format '{e}'. Use names like 'red' or hex like '#FF0000'.")
        return

    BORDER_SIZE = 4

    # --- 1. Calculate BOX_SIZE ---
    qr_test = qrcode.QRCode(version=1, border=BORDER_SIZE)
    qr_test.add_data(url)
    qr_test.make(fit=True) 
    
    total_modules = qr_test.modules_count + BORDER_SIZE * 2
    BOX_SIZE = max(1, target_size // total_modules)
    
    # --- 2. Create the final QR object ---
    qr = qrcode.QRCode(
        version=qr_test.version,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=BOX_SIZE,
        border=BORDER_SIZE,
    )
    qr.add_data(url)
    qr.make()

    # --- 3. "Cut out" the center for the logo ---
    try:
        logo = Image.open(logo_path)
    except FileNotFoundError:
        print(f"ERROR: Logo file '{logo_path}' not found.")
        return
    except Exception as e:
        print(f"ERROR opening logo: {e}")
        return

    total_modules = qr.modules_count + BORDER_SIZE * 2
    qr_width, qr_height = total_modules * BOX_SIZE, total_modules * BOX_SIZE

    logo_padding = 2
    logo_max_size = (qr_height // 4) - logo_padding
    logo.thumbnail((logo_max_size, logo_max_size))

    logo_pos = ((qr_width - logo.width) // 2, (qr_height - logo.height) // 2)

    corner_radius = BOX_SIZE
    patch_radius = corner_radius // 2

    patch_left = logo_pos[0]
    patch_top = logo_pos[1]
    patch_right = logo_pos[0] + logo.width
    patch_bottom = logo_pos[1] + logo.height

    module_left_abs = patch_left // BOX_SIZE
    module_top_abs = patch_top // BOX_SIZE
    module_right_abs = (patch_right + BOX_SIZE - 1) // BOX_SIZE
    module_bottom_abs = (patch_bottom + BOX_SIZE - 1) // BOX_SIZE

    for r_abs in range(module_top_abs, module_bottom_abs):
        for c_abs in range(module_left_abs, module_right_abs):
            r = r_abs - BORDER_SIZE
            c = c_abs - BORDER_SIZE
            if 0 <= r < qr.modules_count and 0 <= c < qr.modules_count:
                qr.modules[r][c] = False

    # --- 4. Render the image ---
    img_qr = qr.make_image(
        fill_color=fill_color,
        back_color=white_color,
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer() 
    ).convert('RGB')

    # --- 5. MANUALLY PAINT THE EYES (position markers) ---
    width, height = img_qr.size
    
    border_px = BORDER_SIZE * BOX_SIZE
    eye_outer_size_px = 7 * BOX_SIZE
    eye_gap_size_px = 5 * BOX_SIZE
    eye_inner_size_px = 3 * BOX_SIZE
    
    eye_gap_offset_px = (eye_outer_size_px - eye_gap_size_px) // 2
    eye_inner_offset_px = (eye_outer_size_px - eye_inner_size_px) // 2

    custom_eye = Image.new('RGB', (eye_outer_size_px, eye_outer_size_px), white_color)
    draw = ImageDraw.Draw(custom_eye)

    draw.rounded_rectangle(
        (0, 0, eye_outer_size_px, eye_outer_size_px), 
        radius=corner_radius, 
        fill=eye_color
    )
    draw.rounded_rectangle(
        (eye_gap_offset_px, eye_gap_offset_px, 
         eye_gap_offset_px + eye_gap_size_px, eye_gap_offset_px + eye_gap_size_px), 
        radius=corner_radius // 2,
        fill=white_color
    )
    draw.rounded_rectangle(
        (eye_inner_offset_px, eye_inner_offset_px, 
         eye_inner_offset_px + eye_inner_size_px, eye_inner_offset_px + eye_inner_size_px), 
        radius=corner_radius // 3,
        fill=fill_color
    )

    box_tl_pos = (border_px, border_px)
    box_tr_pos = (width - border_px - eye_outer_size_px, border_px)
    box_bl_pos = (border_px, height - border_px - eye_outer_size_px)

    for box_pos in [box_tl_pos, box_tr_pos, box_bl_pos]:
        clear_box = (
            box_pos[0], box_pos[1], 
            box_pos[0] + eye_outer_size_px, box_pos[1] + eye_outer_size_px
        )
        draw_base = ImageDraw.Draw(img_qr)
        draw_base.rectangle(clear_box, fill=white_color)
        img_qr.paste(custom_eye, box_pos)

    # --- 6. Add logo with a white background patch ---
    white_patch_layer = Image.new('RGBA', img_qr.size, (0, 0, 0, 0))
    draw_patch = ImageDraw.Draw(white_patch_layer)

    draw_patch.rounded_rectangle(
        (patch_left, patch_top, patch_right, patch_bottom), 
        radius=patch_radius, 
        fill=white_color
    )

    img_qr.paste(white_patch_layer, (0, 0), mask=white_patch_layer)
    img_qr.paste(logo, logo_pos, mask=logo.convert('RGBA'))

    # --- 7. Save ---
    img_qr.save(output_file)
    print(f"✅ Success! QR code ({img_qr.width}x{img_qr.height}px) saved to: {output_file}")


# --- (NEW BLOCK) Main block to run the script from the terminal ---
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
