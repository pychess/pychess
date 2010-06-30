import os
import re

import gtk
import rsvg
import cairo

class OverlayWindow (gtk.Window):
    """ This class knows about being an overlaywindow and some svg stuff """
    
    cache = {} # Class global self.cache for svgPath:rsvg and (svgPath,w,h):surface
    
    def __init__ (self, parent):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        colormap = self.get_screen().get_rgba_colormap()
        if colormap:
            self.set_colormap(colormap)
        self.myparent = parent
    
    #===========================================================================
    #   The overlay stuff
    #===========================================================================
    
    def paintTransparent (self, cairoContext):
        if self.is_composited():
            cairoContext.set_operator(cairo.OPERATOR_CLEAR)
            cairoContext.set_source_rgba(0,0,0,0)
            cairoContext.paint()
            cairoContext.set_operator(cairo.OPERATOR_OVER)
    
    def digAHole (self, svgShape, width, height):
        
        # Create a bitmap and clear it
        mask = gtk.gdk.Pixmap(None, width, height, 1)
        mcontext = mask.cairo_create()
        mcontext.set_source_rgb(0, 0, 0)
        mcontext.set_operator(cairo.OPERATOR_DEST_OUT)
        mcontext.paint()
        
        # Paint our shape
        surface = self.getSurfaceFromSvg(svgShape, width, height)
        mcontext.set_operator(cairo.OPERATOR_OVER)
        mcontext.set_source_surface(surface, 0, 0)
        mcontext.paint()
        
        # Apply it only if aren't composited, in which case we only need input
        # masking
        if self.is_composited():
            self.window.input_shape_combine_mask(mask, 0, 0)
        else: self.window.shape_combine_mask(mask, 0, 0)
    
    def translateCoords (self, x, y):
        x1, y1 = self.myparent.window.get_position()
        x += x1 + self.myparent.get_allocation().x
        y += y1 + self.myparent.get_allocation().y
        return x, y
    
    #===========================================================================
    #   The SVG stuff
    #===========================================================================
    
    def getSurfaceFromSvg (self, svgPath, width, height):
        path = os.path.abspath(svgPath)
        if (path, width, height) in self.cache:
            return self.cache[(path, width, height)]
        else:
            if path in self.cache:
                svg = self.cache[path]
            else:
                svg = self.__loadNativeColoredSvg(path)
                self.cache[path] = svg
            surface = self.__svgToSurface(svg, width, height)
            self.cache[(path, width, height)] = surface
            return surface
    
    def getSizeOfSvg (self, svgPath):
        path = os.path.abspath(svgPath)
        if not path in self.cache:
            svg = self.__loadNativeColoredSvg(path)
            self.cache[path] = svg
        svg = self.cache[path]
        return (svg.props.width, svg.props.height)
    
    def __loadNativeColoredSvg (self, svgPath):
        def colorToHex (color, state):
            color = getattr(self.myparent.get_style(), color)[state]
            pixels = (color.red, color.green, color.blue)
            return "#"+"".join(hex(c/256)[2:].zfill(2) for c in pixels)
        
        TEMP_PATH = "/tmp/pychess_theamed.svg"
        colorDic = {"#18b0ff": colorToHex("light", gtk.STATE_SELECTED),
                    "#575757": colorToHex("text_aa", gtk.STATE_PRELIGHT),
                    "#e3ddd4": colorToHex("bg", gtk.STATE_NORMAL),
                    "#d4cec5": colorToHex("bg", gtk.STATE_INSENSITIVE),
                    "#ffffff": colorToHex("base", gtk.STATE_NORMAL),
                    "#000000": colorToHex("fg", gtk.STATE_NORMAL)}
        
        data = file(svgPath).read()
        data = re.sub("|".join(colorDic.keys()),
                      lambda m: m.group() in colorDic and colorDic[m.group()] or m.group(),
                      data)
        f = file(TEMP_PATH, "w")
        f.write(data)
        f.close()
        svg = rsvg.Handle(TEMP_PATH)
        os.remove(TEMP_PATH)
        return svg
    
    def __svgToSurface (self, svg, width, height):
        assert type(width) == int
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        context = cairo.Context(surface)
        context.set_operator(cairo.OPERATOR_SOURCE)
        if svg.props.width != width or svg.props.height != height:
            context.scale(width/float(svg.props.width),
                          height/float(svg.props.height))
        svg.render_cairo(context)
        return surface
    
    def __onStyleSet (self, self_, oldstyle):
        self.cache.clear()
