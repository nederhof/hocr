from PIL import Image
from collections import defaultdict
import pickle
import os
import sys
import heapq

from imageprocessing import area, image_to_vec, Segment, image_to_segments
from names import get_insertions
from controls import Horizontal, Vertical, Basic
from train import default_font_dir

name_to_insertions = get_insertions()

default_dir = 'newgardiner'
beam_width = 10

class FontInfo:
	def __init__(self, prototype_dir):
		with open(os.path.join(prototype_dir, 'chars.pickle'), 'rb') as handle:
			self.chars = pickle.load(handle)
		with open(os.path.join(prototype_dir, 'partss.pickle'), 'rb') as handle:
			self.partss = pickle.load(handle)
		with open(os.path.join(prototype_dir, 'embeddingscore.pickle'), 'rb') as handle:
			self.embeddings_core = pickle.load(handle)
		with open(os.path.join(prototype_dir, 'embeddingsfull.pickle'), 'rb') as handle:
			self.embeddings_full = pickle.load(handle)
		with open(os.path.join(prototype_dir, 'aspectscore.pickle'), 'rb') as handle:
			self.aspects_core = pickle.load(handle)
		with open(os.path.join(prototype_dir, 'aspectsfull.pickle'), 'rb') as handle:
			self.aspects_full = pickle.load(handle)
		with open(os.path.join(prototype_dir, 'scaler.pickle'), 'rb') as handle:
			self.scaler = pickle.load(handle)
		with open(os.path.join(prototype_dir, 'pca.pickle'), 'rb') as handle:
			self.pca = pickle.load(handle)

	def image_to_embedding(self, im):
		vec = image_to_vec(im)
		scaled = self.scaler.transform([vec])[0]
		embedding = self.pca.transform([scaled])[0]
		return embedding

class ClassifiedSegment:
	def __init__(self, segment, ch):
		self.segment = segment
		self.ch = ch

def aspects_similar(aspect1, aspect2):
	if aspect1 < 0.3 or 1/aspect1 < 0.3:
		return abs(aspect1-aspect2) / aspect1 < 0.3
	elif aspect1 < 0.5 or 1/aspect1 < 0.5:
		return abs(aspect1-aspect2) / aspect1 < 0.2
	else:
		return abs(aspect1-aspect2) / aspect1 < 0.1

def squared_dist(vals1, vals2):
	return sum([(val1-val2)*(val1-val2) for (val1,val2) in zip(vals1,vals2)])

def conditional_squared_dist(vals1, aspect1, vals2, aspect2):
	if aspects_similar(aspect1, aspect2):
		return squared_dist(vals1, vals2)
	else:
		return sys.float_info.max

def find_closest_core(embedding, aspect, k, fontinfo):
	dists = [conditional_squared_dist(embedding, aspect, e, a) for (e, a) \
					in zip(fontinfo.embeddings_core, fontinfo.aspects_core)]
	indexes = heapq.nlargest(k, range(len(dists)), key=lambda i: -dists[i])
	return indexes

def classify_image(im, k, fontinfo):
	embedding = fontinfo.image_to_embedding(im)
	w, h = im.size
	aspect = w / h
	return find_closest_core(embedding, aspect, k, fontinfo)

def classify_segments(segments, fontinfo):
	classifieds = []
	for segment in segments:
		ch_indexes = classify_image(segment.im, beam_width, fontinfo)
		classifieds.append(ClassifiedSegment(segment, ch_indexes))
	return classifieds

def relative_location(core, segment):
	w_core, h_core = core.im.size
	unit = max(w_core, h_core)
	w, h = segment.im.size
	x_mid = segment.x + w/2
	y_mid = segment.y + h/2
	x_rel = (x_mid - core.x) / unit
	y_rel = (y_mid - core.y) / unit
	w_rel = w / unit
	h_rel = h / unit
	return {'x': x_rel, 'y': y_rel, 'w': w_rel, 'h': h_rel}

def similar_location(pos1, pos2):
	epsilon = 0.2
	return abs(pos1['x']-pos2['x']) < epsilon and abs(pos1['y']-pos2['y']) < epsilon and \
			abs(pos1['w']-pos2['w']) < epsilon and abs(pos1['h']-pos2['h']) < epsilon

def find_best_with_parts(classifieds_list, i, segment, candidate, fontinfo):
	parts = fontinfo.partss[candidate]
	if len(parts) > 0:
		merged = segment.copy()
		indices = []
		for j in range(i+1, len(classifieds_list)):
			other = classifieds_list[j]
			segment_location = relative_location(segment, other.segment)
			for part_location in parts:
				if similar_location(segment_location, part_location):
					merged = Segment.merge(merged, other.segment)
					indices.append(j)
					break
		embedding = fontinfo.image_to_embedding(merged.im)
		dist = squared_dist(embedding, fontinfo.embeddings_full[candidate])
		return dist, merged, indices
	else:
		embedding = fontinfo.image_to_embedding(segment.im)
		dist = squared_dist(embedding, fontinfo.embeddings_core[candidate])
		return dist, segment, []

def find_best_chars(classifieds_list, fontinfo):
	classifieds = []
	i = 0
	while i < len(classifieds_list):
		best_dist = sys.float_info.max
		best_merged = None
		best_ch = None
		best_indices = []
		classified_list = classifieds_list[i]
		segment = classified_list.segment
		candidates = classified_list.ch
		for candidate in candidates:
			dist, merged, indices = \
					find_best_with_parts(classifieds_list, i, segment, candidate, fontinfo)
			if dist < best_dist:
				best_dist = dist
				best_merged = merged
				best_ch = fontinfo.chars[candidate]
				best_indices = indices
		classifieds.append(ClassifiedSegment(best_merged, best_ch))
		for index in reversed(best_indices):
			classifieds_list.pop(index)
		i = i+1
	return classifieds

def image_to_signs(im, fontinfo):
	segments = image_to_segments(im)
	segments = [segment for segment in segments if area(segment.im) > 6]
	segments = sorted(segments, key=lambda s: -area(s.im))
	classifieds_list = classify_segments(segments, fontinfo)
	classifieds = find_best_chars(classifieds_list, fontinfo)
	return classifieds

def partition_hor(signs):
	signs = sorted(signs, key=lambda s: s.segment.x)
	groups = []
	while len(signs) > 0:
		sign = signs.pop(0)
		group = [sign]
		x_min = sign.segment.x
		x_max = sign.segment.x + sign.segment.im.size[0]
		while len(signs) > 0:
			x_max_old = x_max
			for i in reversed(range(len(signs))):
				sign = signs[i]
				if sign.segment.x <= x_max:
					group.append(sign)
					x_max = max(x_max, sign.segment.x + sign.segment.im.size[0])
					signs.pop(i)
			if x_max == x_max_old:
				break
		groups.append(group)
	return groups

def partition_ver(signs):
	signs = sorted(signs, key=lambda s: s.segment.y)
	groups = []
	while len(signs) > 0:
		sign = signs.pop(0)
		group = [sign]
		y_min = sign.segment.y
		y_max = sign.segment.y + sign.segment.im.size[1]
		while len(signs) > 0:
			y_max_old = y_max
			for i in reversed(range(len(signs))):
				sign = signs[i]
				if sign.segment.y <= y_max:
					group.append(sign)
					y_max = max(y_max, sign.segment.y + sign.segment.im.size[1])
					signs.pop(i)
			if y_max == y_max_old:
				break
		groups.append(group)
	return groups

def relative_corner_location(core, insert):
	x_mid = insert.x + insert.im.size[0] / 2
	y_mid = insert.y + insert.im.size[1] / 2
	x = ( x_mid - core.x ) / core.im.size[0]
	y = ( y_mid - core.y ) / core.im.size[1]
	return x, y

def distance_loc(loc1, loc2):
	return (loc1[0] - loc2[0]) * (loc1[0] - loc2[0]) + (loc1[1] - loc2[1]) * (loc1[1] - loc2[1])

def corner_control(core, sign):
	insertions = name_to_insertions[core.ch]
	loc = relative_corner_location(core.segment, sign.segment)
	best_corner = max(insertions.keys(), key=lambda c: -distance_loc(insertions[c], loc))
	return best_corner

def basic_to_structure(group):
	group = sorted(group, key=lambda s: -area(s.segment.im))
	core = group[0]
	basic = Basic(core.ch)
	corners = defaultdict(list)
	for sign in group[1:]:
		if area(sign.segment.im) >= area(core.segment.im) / 100 and \
				core.ch in name_to_insertions:
			corner = corner_control(core, sign)
			corners[corner].append(sign)
	for corner in corners:
		basic.corner_to_group[corner] = topgroup_to_structure(corners[corner])
	return basic

def topgroup_to_structure(group):
	groups = partition_hor(group)
	if len(groups) > 1:
		return Horizontal([horsubgroup_to_structure(g) for g in groups])
	else:
		groups = partition_ver(group)
		if len(groups) > 1:
			return Vertical([versubgroup_to_structure(g) for g in groups])
		else:
			return basic_to_structure(group)

def versubgroup_to_structure(group):
	groups = partition_hor(group)
	if len(groups) > 1:
		return Horizontal([horsubgroup_to_structure(g) for g in groups])
	else:
		return basic_to_structure(group)

def horsubgroup_to_structure(group):
	groups = partition_ver(group)
	if len(groups) > 1:
		return Vertical([versubgroup_to_structure(g) for g in groups])
	else:
		return basic_to_structure(group)

def image_to_encoding(im, fontinfo, dir=None):
	signs = image_to_signs(im, fontinfo)
	if dir is None:
		w, h = im.size
		dir = 'v' if h > w else 'h'
	if dir == 'h':
		groups = partition_hor(signs)
		encodings = [horsubgroup_to_structure(group).to_unicode() for group in groups]
	else:
		groups = partition_ver(signs)
		encodings = [versubgroup_to_structure(group).to_unicode() for group in groups]
	encoding = ''.join(encodings)
	return encoding

# for testing can be used without parameters
if __name__ == '__main__':
	from names import get_names
	from imageprocessing import normalize_image
	image = 'tests/test2.png'
	direction = 'h'
	font_dir = default_font_dir
	if len(sys.argv) >= 2:
		image = sys.argv[1]
	if len(sys.argv) >= 3:
		direction = sys.argv[2]
	if len(sys.argv) >= 4:
		font_dir = sys.argv[3]
	fontinfo = FontInfo(default_dir)
	im = normalize_image(Image.open(image))
	encoding = image_to_encoding(im, fontinfo, dir=direction)
	print(' '.join([get_names()[ch] for ch in encoding]))