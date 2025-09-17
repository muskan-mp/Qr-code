from flask import Flask, render_template, request, send_file, redirect, url_for, session
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import *
from qrcode.image.styles.colormasks import *
from io import BytesIO
import json
import os
from PIL import Image, ImageDraw, ImageFont
import random
import base64
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max file size
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Add a secret key for session management

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def hex_to_rgba(hex_color, alpha=255):
    """Convert hex color to RGBA tuple"""
    rgb = hex_to_rgb(hex_color)
    return rgb + (alpha,)

def safe_int(value, default=0):
    """Safely convert value to integer with default fallback"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def generate_qr_code(data, options):
    """Generate QR code with given options"""
    # Create QR code
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    # Convert colors to proper format
    fg_rgb = hex_to_rgb(options.get('fg_color', '#000000'))
    bg_rgb = hex_to_rgb(options.get('bg_color', '#ffffff'))
    
    # Handle background transparency
    if options.get('transparent_bg'):
        bg_rgb = (0, 0, 0, 0)  # Transparent
    
    gradient_start_rgb = hex_to_rgb(options.get('gradient_start', '#000000'))
    gradient_end_rgb = hex_to_rgb(options.get('gradient_end', '#ffffff'))
    
    # Choose module drawer based on shape
    dot_shape = options.get('dot_shape', 'square')
    if dot_shape == 'circle':
        module_drawer = CircleModuleDrawer()
    elif dot_shape == 'rounded':
        module_drawer = RoundedModuleDrawer()
    elif dot_shape == 'vertical':
        module_drawer = VerticalBarsDrawer()
    elif dot_shape == 'horizontal':
        module_drawer = HorizontalBarsDrawer()
    else:  # square
        module_drawer = SquareModuleDrawer()
    
    # Choose eye drawer based on shape
    eye_shape = options.get('eye_shape', 'square')
    if eye_shape == 'circle':
        eye_drawer = CircleModuleDrawer()
    elif eye_shape == 'rounded':
        eye_drawer = RoundedModuleDrawer()
    else:  # square
        eye_drawer = SquareModuleDrawer()
    
    # Create color mask based on gradient type
    gradient_type = options.get('gradient_type', 'none')
    if gradient_type == 'linear':
        color_mask = HorizontalGradiantColorMask(
            back_color=bg_rgb, 
            left_color=gradient_start_rgb,
            right_color=gradient_end_rgb
        )
    elif gradient_type == 'radial':
        color_mask = RadialGradiantColorMask(
            back_color=bg_rgb,
            center_color=gradient_start_rgb,
            edge_color=gradient_end_rgb
        )
    else:
        color_mask = SolidFillColorMask(back_color=bg_rgb, front_color=fg_rgb)
    
    # Generate QR code image
    img = qr.make_image(
        image_factory=StyledPilImage,
        color_mask=color_mask,
        module_drawer=module_drawer,
        eye_drawer=eye_drawer
    )
    
    # Add logo if provided
    logo_path = options.get('logo_path')
    if logo_path and os.path.exists(logo_path):
        logo_img = Image.open(logo_path).convert("RGBA")
        
        # Resize logo based on percentage
        qr_size = img.size[0]
        logo_size = safe_int(options.get('logo_size', 20))
        logo_size_px = int(qr_size * logo_size / 100)
        logo_img.thumbnail((logo_size_px, logo_size_px), Image.Resampling.LANCZOS)
        
        # Calculate position
        logo_position = options.get('logo_position', 'center')
        if logo_position == 'center':
            position = ((qr_size - logo_img.size[0]) // 2, (qr_size - logo_img.size[1]) // 2)
        elif logo_position == 'top-left':
            position = (qr_size // 10, qr_size // 10)
        elif logo_position == 'top-right':
            position = (qr_size - logo_img.size[0] - qr_size // 10, qr_size // 10)
        elif logo_position == 'bottom-left':
            position = (qr_size // 10, qr_size - logo_img.size[1] - qr_size // 10)
        elif logo_position == 'bottom-right':
            position = (qr_size - logo_img.size[0] - qr_size // 10, qr_size - logo_img.size[1] - qr_size // 10)
        
        # Paste logo onto QR code
        img.paste(logo_img, position, logo_img)
    
    # Add logo text if provided
    logo_text = options.get('logo_text', '')
    if logo_text:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        text_width = draw.textlength(logo_text, font=font)
        text_position = (img.size[0] - text_width - 10, img.size[1] - 30)
        draw.text(text_position, logo_text, fill=fg_rgb, font=font)
    
    return img

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/customize/<qr_type>')
def customize(qr_type):
    return render_template('customize.html', qr_type=qr_type)

@app.route('/preview', methods=['POST'])
def preview():
    # Get form data
    qr_type = request.form.get('qr_type')
    content = request.form.get('content')
    
    # QR code options
    options = {
        'fg_color': request.form.get('fg_color', '#000000'),
        'bg_color': request.form.get('bg_color', '#ffffff'),
        'transparent_bg': request.form.get('transparent_bg') == 'on',
        'dot_shape': request.form.get('dot_shape', 'square'),
        'eye_shape': request.form.get('eye_shape', 'square'),
        'gradient_type': request.form.get('gradient_type', 'none'),
        'gradient_start': request.form.get('gradient_start', '#000000'),
        'gradient_end': request.form.get('gradient_end', '#ffffff'),
        'inner_eye_color': request.form.get('inner_eye_color', '#000000'),
        'outer_eye_color': request.form.get('outer_eye_color', '#000000'),
        'random_pattern': request.form.get('random_pattern') == 'on',
        'eye_glow': request.form.get('eye_glow') == 'on',
        'logo_size': safe_int(request.form.get('logo_size', 20)),
        'logo_position': request.form.get('logo_position', 'center'),
        'logo_frame_style': request.form.get('logo_frame_style', 'none'),
        'logo_text': request.form.get('logo_text', '')
    }
    
    # Handle logo upload
    logo = request.files.get('logo')
    logo_filename = None
    if logo and logo.filename:
        # Generate unique filename for logo
        logo_filename = f"logo_{uuid.uuid4().hex}_{logo.filename}"
        logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
        logo.save(logo_path)
        options['logo_path'] = logo_path
        # Store logo filename in session for download
        session['logo_filename'] = logo_filename
    
    # Set content based on type
    if qr_type == 'url':
        data = content if content.startswith(('http://', 'https://')) else f'http://{content}'
    elif qr_type == 'phone':
        data = f'tel:{content}'
    elif qr_type == 'multilink':
        try:
            multilink_data = json.loads(content)
            # Convert multilink to appropriate format
            formatted_content = "MECARD:"
            for link in multilink_data.get('links', []):
                formatted_content += f"{link.get('title', 'Link')}:{link.get('url', '')};"
            data = formatted_content
        except:
            data = content
    else:  # text
        data = content
    
    # Generate QR code
    img = generate_qr_code(data, options)
    
    # Convert image to base64 for preview
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    img_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    
    # Store options in session for download
    session['qr_options'] = options
    session['qr_type'] = qr_type
    session['qr_content'] = content
    
    return render_template('preview.html', qr_type=qr_type, content=content, 
                          options=options, img_data=img_data)

@app.route('/download')
def download():
    # Get data from session
    qr_type = session.get('qr_type')
    content = session.get('qr_content')
    options = session.get('qr_options', {})
    
    # Handle logo from session
    logo_filename = session.get('logo_filename')
    if logo_filename:
        logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
        if os.path.exists(logo_path):
            options['logo_path'] = logo_path
    
    # Set content based on type
    if qr_type == 'url':
        data = content if content.startswith(('http://', 'https://')) else f'http://{content}'
    elif qr_type == 'phone':
        data = f'tel:{content}'
    elif qr_type == 'multilink':
        try:
            multilink_data = json.loads(content)
            # Convert multilink to appropriate format
            formatted_content = "MECARD:"
            for link in multilink_data.get('links', []):
                formatted_content += f"{link.get('title', 'Link')}:{link.get('url', '')};"
            data = formatted_content
        except:
            data = content
    else:  # text
        data = content
    
    # Generate QR code
    img = generate_qr_code(data, options)
    
    # Save image to bytes buffer
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # Clean up logo file
    if logo_filename:
        logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
        if os.path.exists(logo_path):
            os.remove(logo_path)
    
    # Clear session data
    session.pop('qr_options', None)
    session.pop('qr_type', None)
    session.pop('qr_content', None)
    session.pop('logo_filename', None)
    
    return send_file(img_buffer, mimetype='image/png', as_attachment=True, download_name='qrcode.png')

if __name__ == '__main__':
    app.run(debug=True)