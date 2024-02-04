from PIL import Image, ImageChops
import numpy as np
import math

binarize = False
block_prototype = True

BLACK_THRESHOLD = 128
GRID_SIZE = 64
MIN_SEGMENT_AREA = 6

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

def transparency_to_white(im):
	im = im.convert('RGBA')
	converted = Image.new('RGBA', im.size, 'white')
	converted.paste(im, mask=im)
	return converted

def area(im):
	w, h = im.size
	return w * h

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

def find_component(im, visited, x, y):
	component = []
	w, h = im.size
	to_visit = [(x,y)]
	while len(to_visit) > 0:
		(x1,y1) = to_visit.pop()
		if 0 <= x1 and x1 < w and 0 <= y1 and y1 < h and (x1,y1) not in visited:
			p = im.getpixel((x1,y1))
			if p <= BLACK_THRESHOLD:
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

	def transpose(self, x, y):
		return Segment(self.im, self.x + x, self.y + y)

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
		im1 = white_image(w,h)
		im2 = white_image(w,h)
		im1.paste(segment1.im, (segment1.x-x_min, segment1.y-y_min))
		im2.paste(segment2.im, (segment2.x-x_min, segment2.y-y_min))
		im = ImageChops.darker(im1, im2)
		return Segment(im, x_min, y_min)

	@staticmethod
	def merge_big(segments, size=1):
		merged = None
		for segment in segments:
			if area(segment.im) >= size:
				if merged is None:
					merged = segment
				else:
					merged = Segment.merge(merged, segment)
		return merged

	@staticmethod
	def merge_with_overlap(segments):
		segments_sorted = sorted(segments, key=lambda s: s.y)
		i = 0
		while i < len(segments_sorted):
			j = i+1
			changed = True
			while changed:
				changed = False
				while j < len(segments_sorted):
					other = segments_sorted[j]
					if segments_sorted[i].y + segments_sorted[i].im.size[1] < other.y:
						break
					if Segment.overlap(segments_sorted[i], other):
						segments_sorted[i] = Segment.merge(segments_sorted[i], other)
						segments_sorted.pop(j)
						changed = True
					else:
						j = j+1
			i = i+1
		return segments_sorted

	def overlap(segment1, segment2):
		w1, h1 = segment1.im.size
		w2, h2 = segment2.im.size
		return segment1.x < segment2.x + w2 and segment2.x < segment1.x + w1 and \
			segment1.y < segment2.y + h2 and segment2.y < segment1.y + h1

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
