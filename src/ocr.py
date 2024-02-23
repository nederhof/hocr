from PIL import Image
from collections import defaultdict
from statistics import median
import pickle
import os
import sys
import heapq
import json

from imageprocessing import area, MIN_SEGMENT_AREA, image_to_vec, Segment, image_to_segments, \
	squared_dist_with_aspect_height, recreate_segment_from_page
from train import default_letter_model_dir

BEAM_WIDTH = 10
BLACK_THRESHOLD = 110

class FontInfo:
	def __init__(self, model_dir, unit_height=None):
		with open(os.path.join(model_dir, 'chars.pickle'), 'rb') as handle:
			self.chars = pickle.load(handle)
		with open(os.path.join(model_dir, 'styles.pickle'), 'rb') as handle:
			self.styles = pickle.load(handle)
		with open(os.path.join(model_dir, 'embeddings.pickle'), 'rb') as handle:
			self.embeddings = pickle.load(handle)
		with open(os.path.join(model_dir, 'aspects.pickle'), 'rb') as handle:
			self.aspects = pickle.load(handle)
		with open(os.path.join(model_dir, 'heights.pickle'), 'rb') as handle:
			self.heights = pickle.load(handle)
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

class ClassifiedSegment:
	def __init__(self, segment, ch, style):
		self.segment = segment
		self.ch = ch
		self.style = style

def find_closest_letter(embedding, aspect, height, k, fontinfo):
	dists = [squared_dist_with_aspect_height(embedding, aspect, height, e, a, h) for (e, a, h) \
				in zip(fontinfo.embeddings, fontinfo.aspects, fontinfo.heights)]
	indexes = heapq.nlargest(k, range(len(dists)), key=lambda i: -dists[i])
	return indexes

def classify_image_letter(im, k, fontinfo):
	embedding = fontinfo.image_to_embedding(im)
	w, h = im.size
	aspect = w / h
	rel_height = h / fontinfo.unit_height
	return find_closest_letter(embedding, aspect, rel_height, k, fontinfo)

def polygon_to_rect(polygon):
	x = polygon[0]
	y = polygon[1]
	w = polygon[2] - polygon[0]
	h = polygon[5] - polygon[1]
	return x, y, w, h

def read_json_words(filename):
	with open(filename, 'r') as f:
		azure = json.load(f)
	return azure['analyzeResult']['pages'][0]['words']

def place_allowed(image_y, image_h, segment_y, segment_h, ch):
	if ch == ',':
		return segment_y > image_y + 0.5 * image_h / 2
	if ch == '.':
		return segment_y > image_y + 0.5 * image_h / 2
	elif ch == '\'':
		return segment_y + segment_h < image_y + 0.7 * image_h
	else:
		return True

def test_ocr(page, x, y, im, fontinfo):
	segments = image_to_segments(im, BLACK_THRESHOLD, strict=True)
	segments = [segment for segment in segments if area(segment.im) >= MIN_SEGMENT_AREA]
	segments = [segment for segment in segments if segment.im.size[1] >= 0.15 * fontinfo.unit_height]
	segments = [recreate_segment_from_page(page, x, y, segment, threshold=BLACK_THRESHOLD) for segment in segments]
	merged = Segment.merge_with_stack(segments)
	indexess = []
	top_list = []
	for segment in merged:
		indexes = classify_image_letter(segment.im, BEAM_WIDTH, fontinfo)
		indexess.append(indexes)
		top_list.append(fontinfo.styles[indexes[0]])
	style = max(set(top_list), key=top_list.count)
	ch = ''
	for segment, indexes in zip(merged, indexess):
		filtered = [index for index in indexes if fontinfo.styles[index] == style]
		filtered = [index for index in indexes \
				if place_allowed(y, im.size[1], segment.y, segment.im.size[1], fontinfo.chars[index])]
		index = filtered[0] if len(filtered) > 0 else indexes[0]
		ch += fontinfo.chars[index]
	return style, ch

def median_height(im, threshold=BLACK_THRESHOLD):
	segments = image_to_segments(im, threshold=BLACK_THRESHOLD, strict=True)
	segments = [segment for segment in segments if area(segment.im) >= MIN_SEGMENT_AREA]
	heights = [segment.im.size[1] for segment in segments]
	return median(heights)
	
if __name__ == '__main__':
	imagefile = '/home/mjn/work/topbib/topbib/ocr/vol1/11.png'
	if len(sys.argv) >= 2:
		imagefile = [sys.argv[1]]
	image = Image.open(imagefile)
	unit_height = median_height(image)
	model_dir = default_letter_model_dir
	fontinfo = FontInfo(model_dir, unit_height)
	words = read_json_words(imagefile + '.json')
	for word in words:
		x, y, w, h = polygon_to_rect(word['polygon'])
		subimage = image.crop((x, y, x+w, y+h))
		style, ch = test_ocr(image, x, y, subimage, fontinfo)
		print(style, ':', word['content'], ch)
