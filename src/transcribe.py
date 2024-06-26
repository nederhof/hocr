from PIL import Image
from collections import defaultdict
import pickle
import os
import sys
import heapq

from imageprocessing import BLACK_THRESHOLD, area, image_to_vec, normalize_image, \
		aspects_similar, squared_dist, squared_dist_with_aspect
from segments import MIN_SEGMENT_AREA, Segment, ClassifiedSegment, image_to_segments, segments_to_rect
from tables import get_insertions, signlist_dir, get_unicode_to_name
from controls import Horizontal, Vertical, Basic, FULL_LOST, TALL_LOST, WIDE_LOST, \
		D12, N5, Z1, Z4, Z5, Z5a, Z13, Z14
from train import default_sign_model_dir

name_to_insertions = get_insertions()
diagonals = [Z4, Z5, Z5a, Z14, FULL_LOST]
circles = [D12, Z13]

BEAM_WIDTH = 10
OVERLAP_RATIO = 6

class FontInfo:
	def __init__(self, model_dir):
		with open(os.path.join(model_dir, 'chars.pickle'), 'rb') as handle:
			self.chars = pickle.load(handle)
		with open(os.path.join(model_dir, 'partss.pickle'), 'rb') as handle:
			self.partss = pickle.load(handle)
		with open(os.path.join(model_dir, 'embeddingscore.pickle'), 'rb') as handle:
			self.embeddings_core = pickle.load(handle)
		with open(os.path.join(model_dir, 'embeddingsfull.pickle'), 'rb') as handle:
			self.embeddings_full = pickle.load(handle)
		with open(os.path.join(model_dir, 'aspectscore.pickle'), 'rb') as handle:
			self.aspects_core = pickle.load(handle)
		with open(os.path.join(model_dir, 'aspectsfull.pickle'), 'rb') as handle:
			self.aspects_full = pickle.load(handle)
		with open(os.path.join(model_dir, 'dimensions.pickle'), 'rb') as handle:
			self.dimensions = pickle.load(handle)
		with open(os.path.join(model_dir, 'scaler.pickle'), 'rb') as handle:
			self.scaler = pickle.load(handle)
		with open(os.path.join(model_dir, 'pca.pickle'), 'rb') as handle:
			self.pca = pickle.load(handle)

	def image_to_embedding(self, im):
		vec = image_to_vec(im)
		scaled = self.scaler.transform([vec])[0]
		embedding = self.pca.transform([scaled])[0]
		return embedding

def squared_dist_with_aspect_all(vals1, aspect1, vals_core, vals_full, aspect2, unit):
	if aspects_similar(aspect1, aspect2):
		if vals_full is not None:
			return squared_dist(vals1, vals_full)
		else:
			return squared_dist(vals1, vals_core)
	else:
		return sys.float_info.max

def find_closest_core(embedding, aspect, width, height, k, fontinfo):
	dists = [squared_dist_with_aspect(embedding, aspect, width, height, e, a, w, h) for (e, a, (w,h)) \
					in zip(fontinfo.embeddings_core, fontinfo.aspects_core, fontinfo.dimensions)]
	indexes = heapq.nlargest(k, range(len(dists)), key=lambda i: -dists[i])
	return indexes

def find_closest_full(embedding, aspect, k, fontinfo, unit):
	dists = [squared_dist_with_aspect_all(embedding, aspect, ec, ef, a, unit) for (ec, ef, a) \
				in zip(fontinfo.embeddings_core, fontinfo.embeddings_full, fontinfo.aspects_core)]
	indexes = heapq.nlargest(k, range(len(dists)), key=lambda i: -dists[i])
	return indexes

def classify_image_core(im, k, fontinfo, unit):
	embedding = fontinfo.image_to_embedding(im)
	w, h = im.size
	aspect = w / h
	w_rel = w / unit
	h_rel = h / unit
	return find_closest_core(embedding, aspect, w_rel, h_rel, k, fontinfo)

def classify_image_full(im, k, fontinfo, unit=None):
	embedding = fontinfo.image_to_embedding(im)
	w, h = im.size
	aspect = w / h
	return find_closest_full(embedding, aspect, k, fontinfo, unit)

def classify_segments_core(segments, fontinfo, unit):
	classifieds = []
	for segment in segments:
		ch_indexes = classify_image_core(segment.im, BEAM_WIDTH, fontinfo, unit)
		classifieds.append(ClassifiedSegment(segment.im, segment.x, segment.y, ch_indexes))
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
			segment_location = relative_location(segment, other)
			for part_location in parts:
				if similar_location(segment_location, part_location):
					merged = Segment.merge(merged, other)
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
		segment = classifieds_list[i]
		candidates = segment.ch
		for candidate in candidates:
			dist, merged, indices = \
					find_best_with_parts(classifieds_list, i, segment, candidate, fontinfo)
			if dist < best_dist:
				best_dist = dist
				best_merged = merged
				best_ch = fontinfo.chars[candidate]
				best_indices = indices
		classifieds.append(ClassifiedSegment(best_merged.im, best_merged.x, best_merged.y, best_ch))
		for index in reversed(best_indices):
			classifieds_list.pop(index)
		i = i+1
	return classifieds

# Hack to avoid Z1 being confused with narrow signs that normally appear bigger.
# If sign tall (aspect ratio < 0.3) and narrower than 1/9 of widest sign and lower than
# 1/3 of tallest sign, then it probably is Z1.
def correct_Z1(sign, widest, tallest):
	ratio = sign.w / sign.h
	if sign.w < widest / 9 and sign.h < tallest / 3 and ratio < 0.3:
		sign.ch = Z1

def image_to_signs(im, fontinfo, unit):
	segments = image_to_segments(im, BLACK_THRESHOLD, min_area=MIN_SEGMENT_AREA)
	widest = max([segment.w for segment in segments])
	tallest = max([segment.h for segment in segments])
	segments = sorted(segments, key=lambda s: -s.area())
	classifieds_list = classify_segments_core(segments, fontinfo, unit)
	classifieds = find_best_chars(classifieds_list, fontinfo)
	for sign in classifieds:
		correct_Z1(sign, widest, tallest)
	return classifieds

def rejoin_hor(groups):
	i = 0
	while i+1 < len(groups):
		group = groups[i]
		group_next = groups[i+1]
		_, y, _, h = segments_to_rect(group)
		_, y_next, _, h_next = segments_to_rect(group_next)
		mid = y + h/2
		mid_next = y_next + h_next/2
		if y + h < mid_next and y_next < y + h and len(group_next) > 1 or \
				mid_next < y and y < y_next + h_next and len(group_next) > 1 or \
				y_next + h_next < mid and y < y_next + h_next and len(group) > 1 or \
				mid < y_next and y_next < y + h and len(group) > 1:
			groups[i] = groups[i] + groups.pop(i+1)
		else:
			i = i+1
	return groups

def rejoin_ver(groups):
	i = 0
	while i+1 < len(groups):
		group = groups[i]
		group_next = groups[i+1]
		x, _, w, _ = segments_to_rect(group)
		x_next, _, w_next, _ = segments_to_rect(group_next)
		mid = x + w/2
		mid_next = x_next + w_next/2
		if x + w < mid_next and x_next < x + w and len(group_next) > 1 or \
				mid_next < x and x < x_next + w_next and len(group_next) > 1 or \
				x_next + w_next < mid and x < x_next + w_next and len(group) > 1 or \
				mid < x_next and x_next < x + w and len(group) > 1:
			groups[i] = groups[i] + groups.pop(i+1)
		else:
			i = i+1
	return groups

def partition_hor(signs):
	signs = sorted(signs, key=lambda s: s.x)
	groups = []
	while len(signs) > 0:
		sign = signs.pop(0)
		group = [sign]
		x_min = sign.x
		x_max = sign.x + sign.w
		while len(signs) > 0:
			x_max_old = x_max
			i = 0
			while i < len(signs):
				sign = signs[i]
				sign_w = sign.w
				min_overlap = min(x_max-x_min, sign_w)/OVERLAP_RATIO
				if sign.x <= x_max - min_overlap:
					group.append(sign)
					x_max = max(x_max, sign.x + sign_w)
					signs.pop(i)
				else:
					i = i+1
			if x_max == x_max_old:
				break
		groups.append(group)
	return rejoin_hor(groups)

def partition_ver(signs):
	signs = sorted(signs, key=lambda s: s.y)
	groups = []
	while len(signs) > 0:
		sign = signs.pop(0)
		group = [sign]
		y_min = sign.y
		y_max = sign.y + sign.h
		while len(signs) > 0:
			y_max_old = y_max
			i = 0
			while i < len(signs):
				sign = signs[i]
				sign_h = sign.h
				min_overlap = min(y_max-y_min, sign_h)/OVERLAP_RATIO
				if sign.y <= y_max - min_overlap:
					group.append(sign)
					y_max = max(y_max, sign.y + sign_h)
					signs.pop(i)
				else:
					i = i+1
			if y_max == y_max_old:
				break
		groups.append(group)
	return rejoin_ver(groups)

def relative_corner_location(core, insert):
	x_mid = insert.x + insert.w / 2
	y_mid = insert.y + insert.h / 2
	x = ( x_mid - core.x ) / core.w
	y = ( y_mid - core.y ) / core.h
	return x, y

def distance_loc(loc1, loc2):
	return (loc1[0] - loc2[0]) * (loc1[0] - loc2[0]) + (loc1[1] - loc2[1]) * (loc1[1] - loc2[1])

def corner_control(core, sign):
	insertions = name_to_insertions[core.ch]
	loc = relative_corner_location(core, sign)
	best_corner = max(insertions.keys(), key=lambda c: -distance_loc(insertions[c], loc))
	return best_corner

def basic_to_structure(group):
	group = sorted(group, key=lambda s: -s.area())
	if len(group) > 3 and len([s.ch for s in group if s.ch in diagonals]) > 3:
		merged = ClassifiedSegment.merge_all(group)
		if merged.w < 0.8 * merged.h:
			ch = TALL_LOST
		elif merged.h < 0.8 * merged.w:
			ch = WIDE_LOST
		else:
			ch = FULL_LOST
		return Basic(ch)
	core = group[0]
	if len(group) > 1:
		if core.ch == Z5a:
			return Basic(Z4)
		if core.ch in circles:
			return Basic(N5)
	basic = Basic(core.ch)
	corners = defaultdict(list)
	for sign in group[1:]:
		if sign.area() >= core.area() / 100 and \
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
		subgroups = [horsubgroup_to_structure(g) for g in groups]
		return Horizontal(subgroups)
	else:
		return basic_to_structure(group)

def horsubgroup_to_structure(group):
	groups = partition_ver(group)
	if len(groups) > 1:
		subgroups = [versubgroup_to_structure(g) for g in groups]
		return Vertical(subgroups)
	else:
		return basic_to_structure(group)

def image_to_encoding(im, fontinfo, dir=None):
	w, h = im.size
	if dir is None:
		dir = 'v' if h > w else 'h'
		unit = min(w, h)
	else:
		unit = h if dir == 'h' else w
	signs = image_to_signs(im, fontinfo, unit)
	if dir == 'h':
		groups = partition_hor(signs)
		encodings = [horsubgroup_to_structure(group).normalize().to_unicode() for group in groups]
	else:
		groups = partition_ver(signs)
		encodings = [versubgroup_to_structure(group).normalize().to_unicode() for group in groups]
	encoding = ''.join(encodings)
	return encoding

def print_transcription(filename, fontinfo, unicode_to_name):
	im = normalize_image(Image.open(filename))
	encoding = image_to_encoding(im, fontinfo, dir=direction)
	print(' '.join([unicode_to_name[ch] for ch in encoding]))

# For testing.
if __name__ == '__main__':
	direction = 'h'
	model_dir = default_sign_model_dir
	if len(sys.argv) < 2:
		print('First argument is image')
		exit(-1)
	images = [sys.argv[1]]
	if len(sys.argv) >= 3:
		direction = sys.argv[2]
	if len(sys.argv) >= 4:
		model_dir = sys.argv[3]
	fontinfo = FontInfo(model_dir)
	unicode_to_name = get_unicode_to_name()
	for filename in images:
		print_transcription(filename, fontinfo, unicode_to_name)
