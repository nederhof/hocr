from PIL import Image, ImageChops
import numpy as np
import math
import sys
import statistics

binarize = False
block_prototype = True

BLACK_THRESHOLD = 128
GRID_SIZE = 64

def normalize_image(im):
	if binarize:
		return im.convert('1', dither=None)
	else:
		return im.convert('L')

def transparency_to_white(im):
	im = im.convert('RGBA')
	converted = Image.new(mode='RGBA', size=im.size, color='white')
	converted.paste(im, mask=im)
	return converted

def white_image(w, h):
	if binarize:
		return Image.new(mode='1', size=(w, h), color=255)
	else:
		return Image.new(mode='L', size=(w, h), color=255)

def make_image(w, h, pixels):
	im = white_image(w, h)
	for (x,y) in pixels:
		im.putpixel((x,y), 0)
	return im

def area(im):
	w, h = im.size
	return w * h

def in_image(im, x, y):
	w, h = im.size
	return 0 <= x and x < w and 0 <= y and y < h

def is_white(im, x, y, threshold):
	return in_image(im, x, y) and im.getpixel((x,y)) > threshold

def is_black(im, x, y, threshold):
	return in_image(im, x, y) and im.getpixel((x,y)) <= threshold

def n_black(im, threshold):
	w, h = im.size
	n = 0
	for x in range(w):
		for y in range(h):
			if is_black(im, x, y, threshold):
				n += 1
	return n

def aspects_similar(aspect1, aspect2):
	if aspect1 < 0.3 or 1/aspect1 < 0.3:
		return abs(aspect1-aspect2) / aspect1 < 0.3
	elif aspect1 < 0.5 or 1/aspect1 < 0.5:
		return abs(aspect1-aspect2) / aspect1 < 0.2
	else:
		return abs(aspect1-aspect2) / aspect1 < 0.1

def sizes_similar(s1, s2):
	return (s1 > 0.25 or s2 < 0.75) and (s2 > 0.25 or s1 < 0.75)

def heights_similar(h1, h2):
	return abs(h1 - h2) < 0.25

def squared_dist(vals1, vals2):
	return sum([(val1-val2)*(val1-val2) for (val1,val2) in zip(vals1,vals2)])

def squared_dist_with_aspect(vals1, aspect1, w1, h1, vals2, aspect2, w2, h2):
	if w2 > 0 and h2 > 0 and (not sizes_similar(w1, w2) or not sizes_similar(h1, h2)):
		return sys.float_info.max
	elif aspects_similar(aspect1, aspect2):
		return squared_dist(vals1, vals2)
	else:
		return sys.float_info.max

def squared_dist_with_aspect_height(vals1, aspect1, height1, vals2, aspect2, height2):
	if aspects_similar(aspect1, aspect2):
		dist = squared_dist(vals1, vals2)
		penalty = 0 if heights_similar(height1, height2) else 800
		return dist + penalty
	else:
		return sys.float_info.max

def image_to_vec(im):
	if block_prototype:
		return image_to_vec_block(im)
	else:
		return image_to_vec_unused(im)

def image_to_vec_block(im):
	resized = im.resize((GRID_SIZE, GRID_SIZE))
	vec = np.asarray(resized).flatten()
	return vec

def image_to_vec_center(im):
	w, h = im.size
	if w < h:
		w_resize = math.ceil(GRID_SIZE * w / h)
		h_resize = GRID_SIZE
	else:
		w_resize = GRID_SIZE
		h_resize = math.ceil(GRID_SIZE * h / w)
	resized = im.resize((w_resize, h_resize))
	block = white_image(GRID_SIZE, GRID_SIZE)
	x = (GRID_SIZE - w_resize) // 2
	y = (GRID_SIZE - h_resize) // 2
	block.paste(resized, (x, y))
	vec = np.asarray(block).flatten()
	return vec

def find_component(im, visited, x, y, threshold, strict=False):
	component = []
	w, h = im.size
	to_visit = [(x,y)]
	if strict:
		neighbours = [(-1,0),(1,0),(0,-1),(0,1)]
	else:
		neighbours = [(x_diff, y_diff) \
			for x_diff in [-1,0,1] for y_diff in [-1,0,1] if x_diff != 0 or y_diff != 0]
	while len(to_visit) > 0:
		(x1,y1) = to_visit.pop()
		if is_black(im, x1, y1, threshold) and (x1,y1) not in visited:
			visited.add((x1,y1))
			component.append((x1, y1, im.getpixel((x1,y1))))
			for x_diff, y_diff in neighbours:
				to_visit.append((x1+x_diff,y1+y_diff))
	return component

def expand_component(im, x_min, y_min, w, h, component, threshold):
	to_visit = []
	visited = set()
	for x, y, _ in component:
		# print(x, y, x_min, y_min)
		if x == x_min:
			to_visit.append((x-1,y))
		if x == x_min + w - 1:
			to_visit.append((x+1,y))
		if y == y_min:
			to_visit.append((x,y-1))
		if y == y_min + h - 1:
			to_visit.append((x,y+1))
	for x_diff in range(w):
		for y_diff in range(h):
			visited.add((x_min + x_diff, y_min + y_diff))
	neighbours = [(-1,0),(1,0),(0,-1),(0,1)]
	while len(to_visit) > 0:
		(x1,y1) = to_visit.pop()
		if is_black(im, x1, y1, threshold) and (x1,y1) not in visited:
			visited.add((x1,y1))
			component.append((x1, y1, im.getpixel((x1,y1))))
			for x_diff, y_diff in neighbours:
				to_visit.append((x1+x_diff,y1+y_diff))

def visit_white(im, visited, x, y, threshold):
	w, h = im.size
	to_visit = [(x,y)]
	while len(to_visit) > 0:
		(x1,y1) = to_visit.pop()
		if is_white(im, x1, y1) and (x1,y1) not in visited:
			visited.add((x1,y1))
			for x_diff in [-1,0,1]:
				for y_diff in [-1,0,1]:
					if x_diff != 0 or y_diff != 0:
						to_visit.append((x1+x_diff,y1+y_diff))

def find_component_list(im, visited, x, y, threshold, strict=False):
	component = find_component(im, visited, x, y, threshold, strict=strict)
	return [component] if len(component) > 0 else []

def find_components(im, threshold, strict=False):
	w, h = im.size
	visited = set()
	components = []
	for x in range(w):
		for y in range(h):
			for c in find_component_list(im, visited, x, y, threshold, strict=strict):
				components.append(c)
	return components

def find_outside(im, threshold=BLACK_THRESHOLD):
	w, h = im.size
	visited = set()
	for x in range(w):
		visit_white(im, visited, x, 0, threshold)
		visit_white(im, visited, x, h-1, threshold)
	for y in range(h):
		visit_white(im, visited, 0, y, threshold)
		visit_white(im, visited, w-1, y, threshold)
	return make_image(w, h, visited), visited
