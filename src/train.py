import os
import sys
from PIL import Image, ImageOps
import pickle
import re

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from tables import get_unicode_to_name, numerals, composite, repeated_single
from imageprocessing import BLACK_THRESHOLD, normalize_image, area, image_to_vec
from segments import image_to_segments

default_sign_font_dirs = ['gardiner', 'newgardiner']
default_letter_font_dirs = ['letters']
default_sign_model_dir = 'signmodel'
default_letter_model_dir = 'lettermodel'
default_sign_letter_model_dir = 'signlettermodel'
default_pca_dim = 30

def ascender(ch):
	return ch in ['b', 'd', 'f', 'fi', 'h', 'i', 'k', 'l', 'th', '6', '8', ]

def small_ascender(ch):
	return ch in ['t', 'ts']

def descender(ch):
	return ch in ['g', 'gu', 'p', 'q', 'y', '3', '4', '5', '7', '9']

def ascender_descender(ch):
	return ch in ['j', 'J']

def accented_lower(ch):
	return ch in ['à', 'è', 'ì', 'ò', 'ù', \
		'á', 'é', 'í', 'ó', 'ú', \
		'â', 'ê', 'î', 'ô', 'û', \
		'ã', 'ñ', 'õ', \
		'ë', 'ï', 'ö', 'ü', \
		'ā', 'ē', 'ī', 'ō', 'ū', \
		'ı͗', 'š']

def accented_lower_descender(ch):
	return ch in ['ý', 'ÿ']

def below_accented_lower(ch):
	return ch in ['ç', 'ḥ', 'ḫ', 'ẖ', 'ḳ', 'ṯ', 'ḏ']

def accented_upper(ch):
	return ch in ['À', 'È', 'Ì', 'Ò', 'Ù', \
		'Á', 'É', 'Í', 'Ó', 'Ú', 'Ý', \
		'Â', 'Ê', 'Î', 'Ô', 'Û', \
		'Ã', 'Ñ', 'Õ', \
		'Ä', 'Ë', 'Ï', 'Ö', 'Ü', 'Ÿ', \
		'Ā', 'Ē', 'Ī', 'Ō', 'Ū', \
		'Č', 'Ꞽ', 'Š']

def below_accented_upper(ch):
	return ch in ['Ç', 'Q', 'Ḥ', 'Ḫ', 'H̱', 'Ḳ', 'Ṯ', 'Ḏ']

def relative_height(ch, style):
	match ch:
		case '.':
			return 0.3
		case ',':
			return 0.6
		case ';':
			return 1.3
		case '-':
			return 0.2
		case '[':
			return 2
		case ']':
			return 2
		case '(':
			return 2
		case ')':
			return 2
		case '&':
			return 1.5
		case '*':
			return 0.9
		case 'ꜥ':
			return 0.9
		case 'Ꜥ':
			return 0.9
	match style:
		case 'normal':
			if ascender(ch):
				return 1.5
			elif small_ascender(ch):
				return 1.3
			elif descender(ch):
				return 1.5
			elif ascender_descender(ch):
				return 2
			elif accented_lower(ch):
				return 1.5
			elif accented_lower_descender(ch):
				return 2
			elif below_accented_lower(ch):
				return 2
			elif accented_upper(ch):
				return 2
			elif below_accented_upper(ch):
				return 2
			elif ch.isupper():
				return 1.7
			else:
				return 1
		case 'italic':
			if ascender(ch):
				return 1.5
			elif small_ascender(ch):
				return 1.3
			elif descender(ch):
				return 1.5
			elif ascender_descender(ch):
				return 2
			elif accented_lower(ch):
				return 1.5
			elif accented_lower_descender(ch):
				return 2
			elif below_accented_lower(ch):
				return 2
			elif accented_upper(ch):
				return 2
			elif below_accented_upper(ch):
				return 2
			elif ch.isupper():
				return 1.7
			else:
				return 1
		case 'bold':
			if ascender(ch):
				return 1.5
			elif small_ascender(ch):
				return 1.3
			elif descender(ch):
				return 1.5
			elif ascender_descender(ch):
				return 1.8
			elif accented_lower(ch):
				return 1.3
			elif accented_lower_descender(ch):
				return 1.8
			elif below_accented_lower(ch):
				return 1.8
			elif accented_upper(ch):
				return 1.8
			elif below_accented_upper(ch):
				return 1.8
			elif ch.isupper():
				return 1.4
			else:
				return 1
		case 'smallcaps':
			if ascender(ch):
				return 1.5
			elif small_ascender(ch):
				return 1.1
			elif descender(ch):
				return 1.1
			elif ascender_descender(ch):
				return 2
			elif accented_lower(ch):
				return 1.5
			elif accented_lower_descender(ch):
				return 2
			elif below_accented_lower(ch):
				return 1.7
			elif accented_upper(ch):
				return 2
			elif below_accented_upper(ch):
				return 2
			elif ch.isupper():
				return 1.6
			else:
				return 1

def split(im):
	segments = image_to_segments(im, BLACK_THRESHOLD)
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

def get_prototype_sign(path, name):
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

def get_prototype_letter(path, ch, style):
	im = normalize_image(Image.open(path))
	vec = image_to_vec(im)
	w, h = im.size
	aspect = w / h
	height = relative_height(ch, style)
	return vec, aspect, height

def get_prototypes_signs(prototype_dirs):
	names = get_unicode_to_name()
	chars = []
	partss = []
	vecs_core = []
	vecs_full = []
	aspects_core = []
	aspects_full = []
	for prototype_dir in prototype_dirs:
		prototype_files = os.listdir(prototype_dir)
		for filename in prototype_files:
			path = os.path.join(prototype_dir, filename)
			base, ext = os.path.splitext(filename)
			if ext == '.png':
				codepoint = re.sub('-[0-9]+', '', base)
				ch = chr(int(codepoint))
				name = names[ch]
				if name in numerals or name in repeated_single:
					continue
				parts, vec_core, vec_full, aspect_core, aspect_full = get_prototype_sign(path, name)
				chars.append(ch)
				partss.append(parts)
				vecs_core.append(vec_core)
				vecs_full.append(vec_full)
				aspects_core.append(aspect_core)
				aspects_full.append(aspect_full)
	return chars, partss, vecs_core, vecs_full, aspects_core, aspects_full

def get_prototypes_letters(prototype_dirs):
	chars = []
	styles = []
	vecs = []
	aspects = []
	heights = []
	for prototype_dir in prototype_dirs:
		prototype_files = os.listdir(prototype_dir)
		for filename in prototype_files:
			path = os.path.join(prototype_dir, filename)
			base, ext = os.path.splitext(filename)
			if ext == '.png':
				filename = re.sub('-[0-9]+', '', base)
				style, codepoints = filename.split(':')
				ch = ''.join([chr(int(codepoint)) for codepoint in codepoints.split('+')])
				vec, aspect, height = get_prototype_letter(path, ch, style)
				chars.append(ch)
				styles.append(style)
				vecs.append(vec)
				aspects.append(aspect)
				heights.append(height)
	return chars, styles, vecs, aspects, heights

def get_prototypes_signs_letters(sign_dirs, letter_dirs):
	_, _, sign_vecs, _, sign_aspects, _ = get_prototypes_signs(sign_dirs)
	_, _, letter_vecs, letter_aspects, _ = get_prototypes_letters(letter_dirs)
	issign = [True] * len(sign_vecs) + [False] * len(letter_vecs)
	vecs = sign_vecs + letter_vecs
	aspects = sign_aspects + letter_aspects
	return issign, vecs, aspects

def train_signs(prototype_dirs, model_dir, pca_dim):
	chars, partss, vecs_core, vecs_full, aspects_core, aspects_full = \
			get_prototypes_signs(prototype_dirs)
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
	if not os.path.exists(model_dir):
		os.mkdir(model_dir)
	with open(os.path.join(model_dir, 'chars.pickle'), 'wb') as handle:
		pickle.dump(chars, handle)
	with open(os.path.join(model_dir, 'partss.pickle'), 'wb') as handle:
		pickle.dump(partss, handle)
	with open(os.path.join(model_dir, 'embeddingscore.pickle'), 'wb') as handle:
		pickle.dump(embeddings_core, handle)
	with open(os.path.join(model_dir, 'embeddingsfull.pickle'), 'wb') as handle:
		pickle.dump(embeddings_full, handle)
	with open(os.path.join(model_dir, 'aspectscore.pickle'), 'wb') as handle:
		pickle.dump(aspects_core, handle)
	with open(os.path.join(model_dir, 'aspectsfull.pickle'), 'wb') as handle:
		pickle.dump(aspects_full, handle)
	with open(os.path.join(model_dir, 'scaler.pickle'), 'wb') as handle:
		pickle.dump(scaler, handle)
	with open(os.path.join(model_dir, 'pca.pickle'), 'wb') as handle:
		pickle.dump(pca, handle)

def train_letters(prototype_dirs, model_dir, pca_dim):
	chars, styles, vecs, aspects, heights = get_prototypes_letters(prototype_dirs)
	scaler = StandardScaler()
	scaled = scaler.fit_transform(vecs)
	pca = PCA(n_components=pca_dim)
	embeddings = pca.fit_transform(scaled)
	if not os.path.exists(model_dir):
		os.mkdir(model_dir)
	with open(os.path.join(model_dir, 'chars.pickle'), 'wb') as handle:
		pickle.dump(chars, handle)
	with open(os.path.join(model_dir, 'styles.pickle'), 'wb') as handle:
		pickle.dump(styles, handle)
	with open(os.path.join(model_dir, 'embeddings.pickle'), 'wb') as handle:
		pickle.dump(embeddings, handle)
	with open(os.path.join(model_dir, 'aspects.pickle'), 'wb') as handle:
		pickle.dump(aspects, handle)
	with open(os.path.join(model_dir, 'heights.pickle'), 'wb') as handle:
		pickle.dump(heights, handle)
	with open(os.path.join(model_dir, 'scaler.pickle'), 'wb') as handle:
		pickle.dump(scaler, handle)
	with open(os.path.join(model_dir, 'pca.pickle'), 'wb') as handle:
		pickle.dump(pca, handle)

def train_signs_letters(sign_dirs, letter_dirs, model_dir, pca_dim):
	issign, vecs, aspects = get_prototypes_signs_letters(sign_dirs, letter_dirs)
	scaler = StandardScaler()
	scaled = scaler.fit_transform(vecs)
	pca = PCA(n_components=pca_dim)
	embeddings = pca.fit_transform(scaled)
	if not os.path.exists(model_dir):
		os.mkdir(model_dir)
	with open(os.path.join(model_dir, 'issign.pickle'), 'wb') as handle:
		pickle.dump(issign, handle)
	with open(os.path.join(model_dir, 'embeddings.pickle'), 'wb') as handle:
		pickle.dump(embeddings, handle)
	with open(os.path.join(model_dir, 'aspects.pickle'), 'wb') as handle:
		pickle.dump(aspects, handle)
	with open(os.path.join(model_dir, 'scaler.pickle'), 'wb') as handle:
		pickle.dump(scaler, handle)
	with open(os.path.join(model_dir, 'pca.pickle'), 'wb') as handle:
		pickle.dump(pca, handle)

def train_signs_default():
	font_dirs = default_sign_font_dirs
	model_dir = default_sign_model_dir
	pca_dim = default_pca_dim
	train_signs(font_dirs, model_dir, pca_dim)

def train_letters_default():
	font_dirs = default_letter_font_dirs
	model_dir = default_letter_model_dir
	pca_dim = default_pca_dim
	train_letters(font_dirs, model_dir, pca_dim)

def train_sign_recognition_default():
	sign_dirs = default_sign_font_dirs
	letter_dirs = default_letter_font_dirs
	model_dir = default_sign_letter_model_dir
	pca_dim = default_pca_dim
	train_signs_letters(sign_dirs, letter_dirs, model_dir, pca_dim)

if __name__ == '__main__':
	train_signs_default()
	train_letters_default()
	train_sign_recognition_default()
