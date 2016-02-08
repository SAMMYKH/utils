import sqlite3, subprocess, fcntl, struct, os, glob, mmap
import cairo, pango, pangocairo

# IOCTL numbers for different commands.
set_bright = 0x4 << (4*7) | 4 << (4*4) | ord('x') << (4*2) | 4
get_bright = 0x8 << (4*7) | 4 << (4*4) | ord('x') << (4*2) | 5
set_oediv = 0x4 << (4*7) | 4 << (4*4) | ord('x') << (4*2) | 6
set_greys = 0x4 << (4*7) | 4 << (4*4) | ord('x') << (4*2) | 7

# Sysfs path to FPGA soft-devices.
fpga_devices_path = '/sys/bus/axent_fpga_bus/devices/'

def get_fb_name(device):
    fb_name = os.listdir(os.path.join(
        fpga_devices_path, device, 'graphics'))[0].strip()
    return os.path.join('/dev', fb_name)

def get_fb_names(device_list):
    for d in device_list:
        try:
            yield get_fb_name(d)
        except:
            pass

# This function sets the brightness of a display.

def set_brightness(display_name, fb_device, config_db, brightness=None):
    if brightness == None:
        try:
            brightness = int(config_db.execute(
                'select brightness from display where deviceName=?',
                (display_name,)).fetchone()[0])
        except ValueError:
            return

    with open(fb_device, 'r') as fb_handle:
        fcntl.ioctl(fb_handle, set_bright,
            struct.pack('<I', brightness))

# This function sets the grey depth of a display.

def set_depth(display_name, fb_device, config_db, depth=None):
    if depth == None:
        try:
            depth = int(config_db.execute(
                'select greyDepth from display where deviceName=?',
                (display_name,)).fetchone()[0])
        except ValueError:
            return

    with open(fb_device, 'r') as fb_handle:
        fcntl.ioctl(fb_handle, set_greys,
            struct.pack('<I', depth))

# This function sets the OE divisor of a display.

def set_oediv(display_name, fb_device, config_db, div=None):
    if div == None:
        try:
            div = int(config_db.execute(
                'select oeDivisor from display where deviceName=?',
                (display_name,)).fetchone()[0])
        except ValueError:
            return

    with open(fb_device, 'r') as fb_handle:
        fcntl.ioctl(fb_handle, set_oediv,
            struct.pack('<I', div))

# This function sets the gamma curve and the colour channel offsets.

def set_cmap(display_name, fb_device, config_db,
             gamma=None, r_off=None, g_off=None, b_off=None):
    display_settings = config_db.execute(
        'select gamma, rOffset, gOffset, bOffset \
         from display where deviceName=?', (display_name,)).fetchone()
    
    # Set up fbc command.
    fbc_args = ['fbc', '-d', fb_device]
    
    # Add gamma.
    if gamma is not None:
        fbc_args.append(str(gamma))
    else:
        try:
            fbc_args.append(str(float(display_settings['gamma'])))
        except ValueError:
            fbc_args.append(1.0)
    
    # Add 'r' offset.
    if (r_off is not None) and (r_off > 0 )and (r_off <= 255):
        fbc_args.append(str(r_off))
    else:
        try:
            fbc_args.extend(['-r', str(int(display_settings['rOffset']))])
        except (ValueError, TypeError):
            pass
    
    # Add 'g' offset.
    if (g_off is not None) and (g_off > 0 )and (g_off <= 255):
        fbc_args.append(str(g_off))
    else:
        try:
            fbc_args.extend(['-g', str(int(display_settings['gOffset']))])
        except (ValueError, TypeError):
            pass
    
    # Add 'b' offset.
    if (b_off is not None) and (b_off > 0 )and (b_off <= 255):
        fbc_args.append(str(b_off))
    else:
        try:
            fbc_args.extend(['-b', str(int(display_settings['bOffset']))])
        except (ValueError, TypeError):
            pass
    
    config_db.commit()
    
    # Run fbc to set gamma and/or colour offset for the framebuffer device.
    subprocess.call(fbc_args)

# This function sets the display rotation.

def set_rotation(display_name, fb_device, config_db, rotation=None):
    if rotation == None:
        try:
            rotation = int(config_db.execute(
                'select rotation from display where deviceName=?',
                (display_name,)).fetchone()[0])
        except ValueError:
            return
    elif rotation == 0 or rotation == 180:
        pass
    else:
        raise ValueError('Invalid rotation setting')
    
    with open(fb_device, 'r') as fb_handle:
        # This is an ioctl call to get the variable screen info from a
        # Linux framebuffer device.
        fb_var = fcntl.ioctl(fb_handle, 0x4600, str(bytearray(160)))
        
        a = bytearray(fb_var)
        a[136] = rotation
        
        fcntl.ioctl(fb_handle, 0x4601, str(a))

def test_mode(mode, fbdev_list):
    # Get mappings between FBDevs and display names in case we're doing an
    # identify.
    display_map = {}
    
    for f in glob.glob('/sys/bus/axent_fpga_bus/drivers/axent_ledfb/*'):
        try:
            fb_name = get_fb_name(f)
        except:
            pass
        else:
            display_map[fb_name] = os.path.basename(f)
    
    for f in fbdev_list:
        try:
            fb = open(f, 'r+')
        except IOError:
            continue
        
        # This is an ioctl call to get the variable screen info from a
        # Linux framebuffer device.
        fb_var = fcntl.ioctl(fb, 0x4600, str(bytearray(160)))
        fb_width, fb_height = struct.unpack('<2L', fb_var[:8])
        
        # mmap() the framebuffer device.
        mmap_size = fb_width * fb_height * 4
        pixel_map = mmap.mmap(fb.fileno(), mmap_size)
        pixel_map.seek(0)
        
        # Draw test mode depending on which test mode to display.
        if mode == 9:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                fb_width, fb_height)
            context = cairo.Context(surface)
            
            # Draw background rectangle.
            context.rectangle(0, 0, fb_width, fb_height)
            context.set_source_rgb(0, 0, 0)
            context.fill()
            
            pangocairo_context = pangocairo.CairoContext(context)
            pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
            
            layout = pangocairo_context.create_layout()
            
            # Select appropriate font.
            font = pango.FontDescription('arial %d' % fb_height)
            layout.set_font_description(font)
            
            # Try to set the display text to the display name.
            try:
                layout.set_text('%s' \
                    % display_map[f].upper())
            except KeyError:
                continue
            
            # Get rendered text size.
            text_width, text_height = layout.get_pixel_size()
            
            # Scale context to match.
            factor = min((fb_width / float(text_width)),
                (fb_height / float(text_height)))
            
            # Center the text.
            context.translate((fb_width - (text_width * factor)) / 2.0,
                (fb_height - (text_height * factor)) / 2.0)
            context.scale(factor, factor)
            
            context.set_source_rgb(1, 1, 1)
            pangocairo_context.update_layout(layout)
            pangocairo_context.show_layout(layout)
            
            pixel_map.write(surface.get_data())
        else:
            for i in xrange(fb_height):
                if mode == 1:
                    line = ''.join('\xff\xff\xff\xff' \
                        for c in xrange(fb_width))
                elif mode == 2:
                    line = ''.join('\x00\x00\x00\x00' \
                        for c in xrange(fb_width))
                elif mode == 3:
                    if i%2 == 0:
                        line = ''.join('\x00\x00\x00\x00\xff\xff\xff\xff' \
                            for c in xrange(fb_width/2))
                    else:
                        line = ''.join('\xff\xff\xff\xff\x00\x00\x00\x00' \
                            for c in xrange(fb_width/2))
                elif mode == 4:
                    if i%2 == 0:
                        line = ''.join('\xff\xff\xff\xff\x00\x00\x00\x00' \
                            for c in xrange(fb_width/2))
                    else:
                        line = ''.join('\x00\x00\x00\x00\xff\xff\xff\xff' \
                            for c in xrange(fb_width/2))
                elif mode == 5:
                    line = ''.join('\x00\x00\x00\x00\xff\xff\xff\xff' \
                        for c in xrange(fb_width/2))
                elif mode == 6:
                    line = ''.join('\xff\xff\xff\xff\x00\x00\x00\x00' \
                        for c in xrange(fb_width/2))
                elif mode == 7:
                    if i%2 == 0:
                        line = ''.join('\x00\x00\x00\x00' \
                            for c in xrange(fb_width))
                    else:
                        line = ''.join('\xff\xff\xff\xff' \
                            for c in xrange(fb_width))
                elif mode == 8:
                    if i%2 == 0:
                        line = ''.join('\xff\xff\xff\xff' \
                            for c in xrange(fb_width))
                    else:
                        line = ''.join('\x00\x00\x00\x00' \
                            for c in xrange(fb_width))
                else:
                    continue
            
                # Write each line to the framebuffer.
                pixel_map.write(line)                   
