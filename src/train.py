import os
import sys
from PIL import Image, ImageOps
import pickle
import re

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from names import get_names, numerals, composite, repeated_single
from imageprocessing import normalize_image, area, image_to_vec, image_to_segments

default_font_dir = 'newgardiner'
default_pca_dim = 30

def split(im):
	segments = image_to_segments(im)
	i_core = max(range(len(segments)), key=lambda i: area(segments[i].im))
	core = segments[i_core]
	w_core, h_core = core.im.size
	unit = max(w_core, h_core)
	parts = []
	for i in range(len(segments)):
		if i != i_core:
			segment = segments[i]
			w, h = segment.im.size
			x_mid = segment.x + w/2
			y_mid = segment.y + h/2
			x_rel = (x_mid - core.x) / unit
			y_rel = (y_mid - core.y) / unit
			w_rel = w / unit
			h_rel = h / unit
			parts.append({'x': x_rel, 'y': y_rel, 'w': w_rel, 'h': h_rel})
	full = im if len(parts) > 0 else None
	return parts, core.im, full

def get_prototype(path, name):
	im = normalize_image(Image.open(path))
	if name in composite:
		parts = []
		core = im
		full = None
	else:
		parts, core, full = split(im)
	vec_core = image_to_vec(core)
	vec_full = image_to_vec(full) if full is not None else None
	w_core, h_core = core.size
	aspect_core = w_core / h_core
	if full is not None:
		w_full, h_full = full.size
		aspect_full = w_full / h_full
	else:
		aspect_full = None
	return parts, vec_core, vec_full, aspect_core, aspect_full

def get_prototypes(prototype_dir):
	names = get_names()
	prototype_files = os.listdir(prototype_dir)
	chars = []
	partss = []
	vecs_core = []
	vecs_full = []
	aspects_core = []
	aspects_full = []
	for filename in prototype_files:
		path = os.path.join(prototype_dir, filename)
		base, ext = os.path.splitext(filename)
		codepoint = re.sub('-[0-9]+', '', base)
		if ext == '.png':
			ch = chr(int(codepoint))
			name = names[ch]
			if name in numerals or name in repeated_single:
				continue
			parts, vec_core, vec_full, aspect_core, aspect_full = get_prototype(path, name)
			chars.append(ch)
			partss.append(parts)
			vecs_core.append(vec_core)
			vecs_full.append(vec_full)
			aspects_core.append(aspect_core)
			aspects_full.append(aspect_full)
	return chars, partss, vecs_core, vecs_full, aspects_core, aspects_full

def train(prototype_dir, pca_dim):
	chars, partss, vecs_core, vecs_full, aspects_core, aspects_full = \
			get_prototypes(prototype_dir)
	scaler = StandardScaler()
	scaled_core = scaler.fit_transform(vecs_core)
	pca = PCA(n_components=pca_dim)
	embeddings_core = pca.fit_transform(scaled_core)
	embeddings_full = []
	for vec in vecs_full:
		if vec is None:
			embeddings_full.append(None)
		else:
			scaled = scaler.transform([vec])[0]
			embedding = pca.transform([scaled])[0]
			embeddings_full.append(embedding)
	with open(os.path.join(prototype_dir, 'chars.pickle'), 'wb') as handle:
		pickle.dump(chars, handle)
	with open(os.path.join(prototype_dir, 'partss.pickle'), 'wb') as handle:
		pickle.dump(partss, handle)
	with open(os.path.join(prototype_dir, 'embeddingscore.pickle'), 'wb') as handle:
		pickle.dump(embeddings_core, handle)
	with open(os.path.join(prototype_dir, 'embeddingsfull.pickle'), 'wb') as handle:
		pickle.dump(embeddings_full, handle)
	with open(os.path.join(prototype_dir, 'aspectscore.pickle'), 'wb') as handle:
		pickle.dump(aspects_core, handle)
	with open(os.path.join(prototype_dir, 'aspectsfull.pickle'), 'wb') as handle:
		pickle.dump(aspects_full, handle)
	with open(os.path.join(prototype_dir, 'scaler.pickle'), 'wb') as handle:
		pickle.dump(scaler, handle)
	with open(os.path.join(prototype_dir, 'pca.pickle'), 'wb') as handle:
		pickle.dump(pca, handle)

if __name__ == '__main__':
	font_dir = default_font_dir
	pca_dim = default_pca_dim
	if len(sys.argv) >= 2:
		font_dir = sys.argv[1]
	if len(sys.argv) >= 3:
		pca_dim = int(sys.argv[2])
	train(font_dir, pca_dim)
