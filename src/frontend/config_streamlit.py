import random
import colorsys

def random_color():
    h = random.random()                        
    s = 0.8 + random.random() * 0.2             
    l = 0.6 + random.random() * 0.2           
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
