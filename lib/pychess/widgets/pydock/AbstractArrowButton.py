import os
import re

import gtk
import rsvg
import cairo

class AbstractArrowButton (gtk.DrawingArea):
    
    def __init__ (self):
        assert type(self) != AbstractArrowButton
        gtk.DrawingArea.__init__(self)
    
    cache = {} # Class global self.cache for svgPath:rsvg and (svgPath,w,h):surface
    
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
            color = getattr(self.get_style(), color)[state]
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
