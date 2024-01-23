from PIL import Image
import numpy as np
import math

binarize = False
block_prototype = True
threshold = 128

grid_size = 64

def normalize_image(im):
	if binarize:
		return im.convert('1', dither=None)
	else:
		return im.convert('L')

def white_image(w, h):
	if binarize:
		return Image.new(mode='1', size=(w, h), color=255)
	else:
		return Image.new(mode='L', size=(w, h), color=255)

def area(im):
	w, h = im.size
	return w * h

def image_to_vec(im):
	if block_prototype:
		return image_to_vec_block(im)
	else:
		return image_to_vec_unused(im)

def image_to_vec_block(im):
	resized = im.resize((grid_size, grid_size))
	vec = np.asarray(resized).flatten()
	return vec

def image_to_vec_center(im):
	w, h = im.size
	if w < h:
		w_resize = math.ceil(grid_size * w / h)
		h_resize = grid_size
	else:
		w_resize = grid_size
		h_resize = math.ceil(grid_size * h / w)
	resized = im.resize((w_resize, h_resize))
	block = white_image(grid_size, grid_size)
	x = (grid_size - w_resize) // 2
	y = (grid_size - h_resize) // 2
	block.paste(resized, (x, y))
	vec = np.asarray(block).flatten()
	return vec

def find_component(im, visited, x, y):
	component = []
	w, h = im.size
	to_visit = [(x,y)]
	while len(to_visit) > 0:
		(x1,y1) = to_visit.pop()
		if 0 <= x1 and x1 < w and 0 <= y1 and y1 < h and (x1,y1) not in visited:
			p = im.getpixel((x1,y1))
			if p <= threshold:
				visited.add((x1,y1))
				component.append((x1,y1,p))
				for x_diff in [-1,0,1]:
					for y_diff in [-1,0,1]:
						if x_diff != 0 or y_diff != 0:
							to_visit.append((x1+x_diff,y1+y_diff))
	return component

def find_component_list(im, visited, x, y):
	component = find_component(im, visited, x, y)
	return [component] if len(component) > 0 else []

def find_components(im):
	w, h = im.size
	visited = set()
	components = []
	for x in range(w):
		for y in range(h):
			for c in find_component_list(im, visited, x, y):
				components.append(c)
	return components

class Segment:
	def __init__(self, im, x, y):
		self.im = im
		self.x = x
		self.y = y

	def copy(self):
		return Segment(self.im.copy(), self.x, self.y)

	@staticmethod
	def merge(segment1, segment2):
		w1, h1 = segment1.im.size
		w2, h2 = segment2.im.size
		x_min = min(segment1.x, segment2.x)
		x_max = max(segment1.x+w1, segment2.x+w2)
		y_min = min(segment1.y, segment2.y)
		y_max = max(segment1.y+h1, segment2.y+h2)
		w = x_max - x_min
		h = y_max - y_min
		im = white_image(w,h)
		im.paste(segment1.im, (segment1.x-x_min, segment1.y-y_min))
		im.paste(segment2.im, (segment2.x-x_min, segment2.y-y_min))
		return Segment(im, x_min, y_min)

def component_to_segment(component):
	x_offset = min([x for x,_,_ in component])
	x_max = max([x for x,_,_ in component])
	y_offset = min([y for _,y,_ in component])
	y_max = max([y for _,y,_ in component])
	w = x_max - x_offset + 1
	h = y_max - y_offset + 1
	im = white_image(w,h)
	for x, y, p in component:
		im.putpixel((x-x_offset,y-y_offset), p)
	return Segment(im, x_offset, y_offset)

def image_to_segments(im):
	components = find_components(im)
	segments = [component_to_segment(c) for c in components]
	return segments

# testing
if __name__ == '__main__':
	im = normalize_image(Image.open('tests/test3.png'))
	w, h = im.size
	segments = image_to_segments(im)
	print(len(segments), 'segments')
	recreated = white_image(w, h)
	i = 0
	recreated.paste(segments[i].im, (segments[i].x, segments[i].y))
	recreated.save('tests/test.png')
