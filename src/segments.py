from PIL import Image, ImageChops

from imageprocessing import normalize_image, white_image, make_image, area, \
		is_black, n_black, find_components, expand_component

MIN_SEGMENT_AREA = 6
MIN_BLACK_AREA = 0.01

def overlap(x1, y1, w1, h1, x2, y2, w2, h2, w_margin=1, h_margin=1):
	w = w_margin * min(w1, w2)
	h = h_margin * min(h1, h2)
	return x1 < x2 + w2 - w and x2 < x1 + w1 - w and y1 < y2 + h2 - h and y2 < y1 + h1 - h

class Segment:
	def __init__(self, im, x, y):
		self.im = im
		self.x = x
		self.y = y
		self.w, self.h = im.size

	def area(self):
		return self.w * self.h

	def copy(self):
		return Segment(self.im.copy(), self.x, self.y)

	def transpose(self, x, y):
		return Segment(self.im, self.x + x, self.y + y)

	def component(self, threshold):
		comp = []
		for x in range(self.w):
			for y in range(self.h):
				if is_black(self.im, x, y, threshold):
					comp.append((self.x + x, self.y + y, self.im.getpixel((x,y))))
		return comp

	def cut_from_page(self, page):
		return page.crop((self.x, self.y, self.x+self.w, self.y+self.h))

	def recreate_from_page(self, page, threshold):
		component = self.component(threshold)
		expand_component(page, self.x, self.y, self.w, self.h, component, threshold)
		return Segment.from_component(component)

	@staticmethod
	def from_component(component):
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

	@staticmethod
	def from_rectangle(x, y, w, h):
		im = make_image(w, h, [])
		return Segment(im, x, y)

	@staticmethod
	def merge(segment1, segment2):
		x_min = min(segment1.x, segment2.x)
		x_max = max(segment1.x + segment1.w, segment2.x + segment2.w)
		y_min = min(segment1.y, segment2.y)
		y_max = max(segment1.y + segment1.h, segment2.y + segment2.h)
		w = x_max - x_min
		h = y_max - y_min
		im1 = white_image(w,h)
		im2 = white_image(w,h)
		im1.paste(segment1.im, (segment1.x-x_min, segment1.y-y_min))
		im2.paste(segment2.im, (segment2.x-x_min, segment2.y-y_min))
		im = ImageChops.darker(im1, im2)
		return Segment(im, x_min, y_min)

	@staticmethod
	def merge_all(segments):
		merged = Segment.copy(segments[0])
		for segment in segments:
			merged = Segment.merge(merged, segment)
		return merged

	@staticmethod
	def merge_big(segments, size=MIN_SEGMENT_AREA):
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
					if segments_sorted[i].y + segments_sorted[i].h < other.y:
						break
					if Segment.overlap(segments_sorted[i], other):
						segments_sorted[i] = Segment.merge(segments_sorted[i], other)
						segments_sorted.pop(j)
						changed = True
					else:
						j = j+1
			i = i+1
		return segments_sorted

	@staticmethod
	def merge_with_stack(segments):
		segments_sorted = sorted(segments, key=lambda s: s.x)
		i = 0
		while i < len(segments_sorted):
			j = i+1
			changed = True
			while changed:
				changed = False
				while j < len(segments_sorted):
					other = segments_sorted[j]
					if other.x <= segments_sorted[i].x + segments_sorted[i].w and \
							(other.y + other.h <= segments_sorted[i].y + 0.3 * segments_sorted[i].h or \
							segments_sorted[i].y + segments_sorted[i].h <= other.y + 0.3 * other.h or \
							other.x + other.w <= segments_sorted[i].x + segments_sorted[i].w):
						segments_sorted[i] = Segment.merge(segments_sorted[i], other)
						segments_sorted.pop(j)
						changed = True
					else:
						j = j+1
			i = i+1
		return segments_sorted

	@staticmethod
	def overlap(segment1, segment2):
		return segment1.x < segment2.x + segment2.w and segment2.x < segment1.x + segment1.w and \
			segment1.y < segment2.y + segment2.h and segment2.y < segment1.y + segment1.h

class ClassifiedSegment(Segment):
	def __init__(self, im, x, y, ch):
		Segment.__init__(self, im, x, y)
		self.ch = ch

	@staticmethod
	def merge_all(segments):
		merged = Segment.merge_all(segments)
		return ClassifiedSegment(merged.im, merged.x, merged.y, None)

def image_to_segments(im, threshold, strict=False, min_area=None, min_black_area=None):
	components = find_components(im, threshold, strict=strict)
	segments = [Segment.from_component(c) for c in components]
	if min_area is not None:
		segments = [segment for segment in segments if min_area <= area(segment.im)]
	if min_black_area is not None:
		x = len(segments)
		segments = [segment for segment in segments \
			if n_black(segment.im, threshold) >= min_black_area * area(segment.im)]
		y = len(segments)
		if y < x:
			print('from', x, 'to', y)
	return segments

def segments_to_rect(segments):
	if len(segments) == 0:
		return None
	segment = segments[0]
	x_min = segment.x
	y_min = segment.y
	x_max = segment.x + segment.w
	y_max = segment.y + segment.h
	for i in range(1, len(segments)):
		segment_i = segments[i]
		x_min = min(x_min, segment_i.x)
		y_min = min(y_min, segment_i.y)
		x_max = max(x_max, segment_i.x + segment_i.w)
		y_max = max(y_max, segment_i.y + segment_i.h)
	return x_min, y_min, x_max-x_min, y_max-y_min

# testing
if __name__ == '__main__':
	im = normalize_image(Image.open('tests/test14.png'))
	segments = image_to_segments(im, 128)
	print(len(segments))
