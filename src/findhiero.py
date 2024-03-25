import sys
import os
import pickle
import heapq
import json
import csv
from statistics import median
from PIL import Image, ImageDraw

from train import default_sign_letter_model_dir, default_sign_model_dir
from imageprocessing import area, image_to_vec, squared_dist_with_aspect
from segments import Segment, image_to_segments, MIN_SEGMENT_AREA, MIN_BLACK_AREA
from rectangleselection import open_selector
from transcribe import FontInfo as SignFontInfo, image_to_encoding

BLACK_THRESHOLD = 110

class FontInfo:
	def __init__(self, model_dir, unit_height=None):
		with open(os.path.join(model_dir, 'issign.pickle'), 'rb') as handle:
			self.issign = pickle.load(handle)
		with open(os.path.join(model_dir, 'embeddings.pickle'), 'rb') as handle:
			self.embeddings = pickle.load(handle)
		with open(os.path.join(model_dir, 'aspects.pickle'), 'rb') as handle:
			self.aspects = pickle.load(handle)
		with open(os.path.join(model_dir, 'scaler.pickle'), 'rb') as handle:
			self.scaler = pickle.load(handle)
		with open(os.path.join(model_dir, 'pca.pickle'), 'rb') as handle:
			self.pca = pickle.load(handle)
		self.unit_height = unit_height

	def image_to_embedding(self, im):
		vec = image_to_vec(im)
		scaled = self.scaler.transform([vec])[0]
		embedding = self.pca.transform([scaled])[0]
		return embedding

def closest_shape_is_sign(embedding, w, h, fontinfo):
	dists = [squared_dist_with_aspect(embedding, w, h, e, a) for \
			(e, a) in zip(fontinfo.embeddings, fontinfo.aspects)]
	indexes = heapq.nlargest(1, range(len(dists)), key=lambda i: -dists[i])
	return fontinfo.issign[indexes[0]]

def classify_image(im, fontinfo, pruned=False):
	embedding = fontinfo.image_to_embedding(im)
	w, h = im.size
	rel_width = w / fontinfo.unit_height
	rel_height = h / fontinfo.unit_height
	if rel_width < 0.5 or rel_height < 0.5:
		return False
	elif rel_height > 3:
		return False
	elif pruned and rel_height <= 1.9:
		return False
	else:
		return closest_shape_is_sign(embedding, w, h, fontinfo)

def close_to(segment1, segment2, unit):
	x1 = segment1.x
	y1 = segment1.y
	x2 = segment2.x
	y2 = segment2.y
	w1, h1 = segment1.im.size
	w2, h2 = segment2.im.size
	y_min = min(y1, y2)
	y_max = max(y1+h1, y2+h2)
	if y_max - y_min > 3 * unit:
		return False
	else:
		return x2 < x1+w1+2*unit and x1 < x2+w2+2*unit and y1 < y2+h2 and y2 < y1+h1 or \
			y2 < y1+h1+2*unit and y1 < y2+h2+2*unit and x1 < x2+w2 and x2 < x1+w1

def close_to_any(segment1, segments, unit):
	for segment2 in segments:
		if close_to(segment1, segment2, unit):
			return True
	return False

def find_signs(im, model_dir):
	segments = image_to_segments(im, BLACK_THRESHOLD, strict=True, \
			min_area=MIN_SEGMENT_AREA, min_black_area=MIN_BLACK_AREA)
	segments = sorted(segments, key=lambda s: s.y)
	heights = [segment.h for segment in segments]
	unit_height = median(heights)
	fontinfo = FontInfo(model_dir, unit_height)
	signs = []
	i = 0
	while i < len(segments):
		if classify_image(segments[i].im, fontinfo, pruned=True):
			signs.append(segments.pop(i))
		else:
			i += 1
	changed = len(signs) > 0
	while changed:
		changed = False
		i = 0
		while i < len(segments):
			segment = segments[i]
			if close_to_any(segment, signs, fontinfo.unit_height) and classify_image(segment.im, fontinfo):
				signs.append(segments.pop(i))
				changed = True
			else:
				i += 1
	changed = len(signs) > 0
	while changed:
		changed = False
		i = 0
		while i < len(signs):
			j = i+1
			while j < len(signs):
				if close_to(signs[i], signs[j], unit_height):
					signs[i] = Segment.merge(signs[i], signs[j])
					signs.pop(j)
					changed = True
				else:
					j += 1
			i += 1
	rects = []
	for segment in signs:
		x = segment.x
		y = segment.y
		w, h = segment.im.size
		rects.append((x, y, w, h))
	return rects

def manual_adjust(imagefile, im, rects):
	segments = [Segment.from_rectangle(x, y, w, h) for x, y, w, h in rects]
	open_selector(imagefile, segments, \
			lambda segments: store_rectangles(imagefile, im, segments))

def store_rectangles(imagefile, im, segments):
	sign_fontinfo = SignFontInfo(default_sign_model_dir)
	csvfile = imagefile + '.csv'
	rows = []
	for segment in segments:
		subimage = segment.cut_from_page(im)
		hiero = image_to_encoding(subimage, sign_fontinfo)
		rows.append({'x': segment.x, 'y': segment.y, 'w': segment.w, 'h': segment.h, 'hiero': hiero})
	rows = sorted(rows, key=lambda row: row['y'])
	with open(csvfile, "w") as handle:
		writer = csv.writer(handle, delimiter=' ')
		for row in rows:
			writer.writerow([row['x'], row['y'], row['w'], row['h'], row['hiero']])

def find_hiero_in_page(imagefile):
	im = Image.open(imagefile)
	rects = find_signs(im, default_sign_letter_model_dir)
	rects = manual_adjust(imagefile, im, rects)

def add_rects_to_image(im, rects):
	result = im.convert('RGB')
	drawing = ImageDraw.Draw(result)
	for x, y, w, h in rects:
		drawing.rectangle([(x, y), (x+w, y+h)], outline=(255,0,0))
	return result

if __name__ == '__main__':
	imagefile = '/home/mjn/work/topbib/topbib/ocr/vol1/1.png'
	if len(sys.argv) >= 2:
		imagefile = sys.argv[1]
	find_hiero_in_page(imagefile)
	# im = Image.open(imagefile)
	# rects = find_signs(im, default_sign_letter_model_dir)
	# rects = manual_adjust(imagefile, im, rects)
	# result = add_rects_to_image(im, rects)
	# result.save("test.png")
