import pickle
import os
import sys
import heapq
import json
from PIL import Image
from collections import defaultdict
from statistics import median

from imageprocessing import area, image_to_vec, squared_dist_with_aspect_height
from segments import Segment, image_to_segments, MIN_SEGMENT_AREA
from train import default_letter_model_dir
from azure import AzurePage

style_list = ['normal', 'italic', 'bold', 'smallcaps']

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

def place_allowed(image_y, image_h, segment_y, segment_h, ch):
	if ch == ',':
		return segment_y > image_y + 0.5 * image_h / 2
	if ch == '.':
		return segment_y > image_y + 0.5 * image_h / 2
	elif ch == '\'':
		return segment_y + segment_h < image_y + 0.7 * image_h
	else:
		return True

def do_ocr(page, word, fontinfo):
	im = page.im.crop((word.x, word.y, word.x+word.w, word.y+word.h))
	segments = image_to_segments(im, BLACK_THRESHOLD, strict=True, min_area=MIN_SEGMENT_AREA)
	segments = [segment for segment in segments if segment.h >= 0.15 * fontinfo.unit_height]
	segments = [segment.transpose(word.x, word.y) for segment in segments]
	segments = [segment.recreate_from_page(page.im, BLACK_THRESHOLD) for segment in segments]
	segments = Segment.merge_with_stack(segments)
	indexess = []
	top_list = []
	for segment in segments:
		indexes = classify_image_letter(segment.im, BEAM_WIDTH, fontinfo)
		indexess.append(indexes)
		first = indexes[0]
		if not fontinfo.chars[first] in [',', '.'] or len(segments) == 1:
			top_list.append(fontinfo.styles[first])
	top_list_sorted = [style for style in style_list if style in top_list]
	style = max(top_list_sorted, key=top_list.count)
	ch = ''
	for segment, indexes in zip(segments, indexess):
		filtered = [index for index in indexes if fontinfo.styles[index] == style]
		filtered = [index for index in indexes \
				if place_allowed(word.y, im.size[1], segment.y, segment.h, fontinfo.chars[index])]
		index = filtered[0] if len(filtered) > 0 else indexes[0]
		ch += fontinfo.chars[index]
	if style == 'smallcaps':
		high = max(segment.h for segment in segments)
		low = min(segment.h for segment in segments if segment.h > high/2)
		if not ch.lower() in ['mss.']:
			if high / low < 1.35 or high / low > 1.9 or high < 1.4 * fontinfo.unit_height:
				style = 'normal'
	return style, ch

def median_height(im, threshold=BLACK_THRESHOLD):
	segments = image_to_segments(im, BLACK_THRESHOLD, strict=True, min_area=MIN_SEGMENT_AREA)
	heights = [segment.im.size[1] for segment in segments]
	return median(heights)
	
if __name__ == '__main__':
	imagefile = '/home/mjn/work/topbib/topbib/ocr/vol1/1.png'
	if len(sys.argv) >= 2:
		imagefile = [sys.argv[1]]
	image = Image.open(imagefile)
	unit_height = median_height(image)
	model_dir = default_letter_model_dir
	fontinfo = FontInfo(model_dir, unit_height)
	page = AzurePage(imagefile)
	for line in page.lines:
		for word in line.words:
			style, ch = do_ocr(image, word, fontinfo)
			if word.confidence < 0.8:
				print(style, ':', word.content, ch, '!!!!!!!!!!!!!!!!!!!!!!')
			else:
				print(style, ':', word.content, ch)
