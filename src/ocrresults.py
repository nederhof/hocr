import sys
import os
import re
import shutil
from PIL import Image

from tables import resources_dir, signlist_dir
from imageprocessing import make_image
from segments import Segment, overlap

def preamble(name):
	 return \
"""<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
""" + \
	'<title>{}</title>'.format(name) + \
"""
<link rel="stylesheet" type="text/css" href="transcription.css">
<link rel="stylesheet" type="text/css" href="hierojax.css">
<script type="text/javascript" src="transcription.js"></script>
<script type="text/javascript" src="hierojax.js"></script>
</head>
<body>
"""

postamble = """</body>
</html>
"""

def prepare_transcription_dir(target_dir):
	if not os.path.exists(target_dir):
		os.mkdir(target_dir)
	for f in ['hierojax.css', 'hierojax.js', 'transcription.css', 'transcription.js', \
				'requirements.txt', 'Makefile', 'correctpage.sh', 'correcter.py']:
		shutil.copy(os.path.join(resources_dir, f), os.path.join(target_dir, f))
	for f in ['NewGardinerSMP.ttf']:
		shutil.copy(os.path.join(signlist_dir, f), os.path.join(target_dir, f))

class Token:
	def __init__(self, style, content, first=False):
		self.style = style
		tag = ''
		if first:
			match self.style:
				case 'italic':
					tag = '<i>'
				case 'bold':
					tag = '<b>'
				case 'smallcaps':
					tag = '<cite>'
		self.content = tag + content
		self.sep = ''

	def end(self):
		tag = ''
		match self.style:
			case 'italic':
				tag = '</i>'
			case 'bold':
				tag = '</b>'
			case 'smallcaps':
				tag = '</cite>'
		if self.content[-1] in [',', ';']:
			self.content = self.content[:-1] + tag + self.content[-1]
		else:
			self.content = self.content + tag

	def space(self):
		self.sep = ' '

	def br(self):
		if self.content[-1] == '-':
			self.sep = '<br>'
		else:
			self.sep = ' <br>\n'

	def __str__(self):
		return self.content + self.sep

class OcrPage:
	def __init__(self, filename):
		self.im = Image.open(filename)
		self.w, self.h = self.im.size

	def remove_words(self, x, y, w, h):
		for line in self.lines:
			line.words = [word for word in line.words if \
				not overlap(x, y, w, h, word.x, word.y, word.w, word.h, w_margin=0.1, h_margin=0.1)]

	def add_word(self, content, style, x, y, w, h):
		mid = y+h/2
		best_dist = sys.maxsize
		best_line = 0
		for i in range(len(self.lines)):
			for word in self.lines[i].words:
				if word.y < mid and mid < word.y + word.h:
					dist = abs(x + w/2 - word.x - word.w/2)
					if dist < best_dist:
						best_dist = dist
						best_line = i
		word = OcrWord(content, 1, 0, len(content), x, y, w, h)
		word.style = style
		self.lines[best_line].words = sorted(self.lines[best_line].words + [word], key=lambda word: word.x)
	
	def get_text_corners(self):
		xmin = self.paras[0].x
		xmax = self.paras[0].x + self.paras[0].w
		ymin = self.paras[0].y
		ymax = self.paras[0].y + self.paras[0].h
		for para in self.paras[1:]:
			xmin = min(xmin, para.x)
			xmax = max(xmax, para.x + para.w)
			ymin = min(ymin, para.y)
			ymax = max(ymax, para.y + para.h)
		return xmin, ymin, xmax-xmin, ymax-ymin

	def widen_to_lines(self):
		for para in self.paras:
			para.widen_to_lines()

	def merge_paras(self, dist):
		self.paras = sorted(self.paras, key=lambda p: p.y)
		i = 0
		while i+1 < len(self.paras):
			this_para = self.paras[i]
			next_para = self.paras[i+1]
			if next_para.y < this_para.y + this_para.h - dist:
				this_para.lines.extend(next_para.lines)
				this_para.length += next_para.length
				xmin = min(this_para.x, next_para.x)
				xmax = max(this_para.x + this_para.w, next_para.x + next_para.w)
				ymin = min(this_para.y, next_para.y)
				ymax = max(this_para.y + this_para.h, next_para.y + next_para.h)
				this_para.x = xmin
				this_para.y = ymin
				this_para.w = xmax-xmin
				this_para.h = ymax-ymin
				self.paras.pop(i+1)
			else:
				i += 1
		change = False
		for para in self.paras:
			change = para.merge_lines(dist) or change
		if change:
			self.lines = [line for para in self.paras for line in para.lines]

	def is_page_header(self, para):
		x, y, w, h = self.text_corners
		return len(para.lines) == 1 and y < para.y + para.h/40 and \
			any([re.match('^[0-9IoO]+$', word.content) and (word.x < x + w/20 or x + w*19/20 < word.x)
				for word in para.lines[0].words])

	def is_section_header(self, para):
		if len(para.lines) != 1:
			return False
		x, y, w, h = self.text_corners
		left = para.x - x
		right = x + w - para.x - para.w
		return left > w/20 and right > w/20 and abs(left-right) < w/20

	def words_to_html(self, line, tokens, last_style_token, last_line_token):
		for word in line.words:
			if last_line_token is not None:
				last_line_token.space()
			if word.style == 'hiero':
				token = Token('hiero', '<span class="hierojax">' + word.content + '</span>')
			else:
				first = True
				if last_style_token is not None:
					if word.style != last_style_token.style:
						last_style_token.end()
					else:
						first = False
				token = Token(word.style, word.content, first=first)
				last_style_token = token
			tokens.append(token)
			last_line_token = token
		return last_style_token, last_line_token

	def line_to_html(self, line):
		tokens = []
		last_style_token = None
		last_line_token = None
		last_style_token, _ = self.words_to_html(line, tokens, last_style_token, last_line_token)
		last_style_token.end()
		return ''.join([str(token) for token in tokens])

	def para_to_image_html(self, para, rel_dir, target_dir, i):
		x, y, w, h = self.text_corners
		para_image = self.im.crop((x, para.y, x + w, para.y + para.h))
		rel_name = os.path.join(rel_dir, str(i) + '.png')
		image_name = os.path.join(target_dir, str(i) + '.png')
		image_tag = '<img src="{}">\n'.format(rel_name)
		para_image.save(image_name)
		return image_tag + self.para_to_html(para)

	def para_to_html(self, para):
		if self.is_page_header(para):
			return '<div class="pageheader">' + self.line_to_html(para.lines[0]) + '</div>\n'
		elif self.is_section_header(para):
			return '<h1>' + self.line_to_html(para.lines[0]) + '</h1>\n'
		tokens = []
		last_style_token = None
		last_line_token = None
		for line in para.lines:
			if last_line_token is not None:
				last_line_token.br()
				last_line_token = None
			last_style_token, last_line_token = self.words_to_html(line, tokens, last_style_token, last_line_token)
		last_style_token.end()
		para_text = ''.join([str(token) for token in tokens])
		return '<p>' + para_text + '</p>\n'

	def to_html(self, target_dir, name, cutouts=False):
		html_file = os.path.join(target_dir, name + '.html')
		if cutouts:
			rel_dir = name + 'cutouts'
			cutouts_dir = os.path.join(target_dir, rel_dir)
			if not os.path.exists(cutouts_dir):
				os.mkdir(cutouts_dir)
			txts = [self.para_to_image_html(para, rel_dir, cutouts_dir, i) for i, para in enumerate(self.paras)]
		else:
			txts = [self.para_to_html(para) for para in self.paras]
		content = ''.join(txts)
		content = content.replace(' .', '.')
		html = preamble(name) + content + postamble
		with open(html_file, "w") as handle:
			handle.write(html)

class OcrWord:
	def __init__(self, content, confidence, offset, length, x, y, w, h):
		self.content = content
		self.confidence = confidence
		self.offset = offset
		self.length = length
		self.x = x
		self.y = y
		self.w = w
		self.h = h
		self.style = 'normal'

	def white_segment(self):
		im = make_image(self.w, self.h, [])
		return Segment(im, self.x, self.y)

class OcrLine:
	def __init__(self, offset, length):
		self.offset = offset
		self.length = length
		self.words = []

	def get_text_corners(self):
		xmin = self.words[0].x
		xmax = self.words[0].x + self.words[0].w
		ymin = self.words[0].y
		ymax = self.words[0].y + self.words[0].h
		for word in self.words[1:]:
			xmin = min(xmin, word.x)
			xmax = max(xmax, word.x + word.w)
			ymin = min(ymin, word.y)
			ymax = max(ymax, word.y + word.h)
		return xmin, ymin, xmax-xmin, ymax-ymin

class OcrPara:
	def __init__(self, offset, length, x, y, w, h):
		self.offset = offset
		self.length = length
		self.x = x
		self.y = y
		self.w = w
		self.h = h
		self.lines = []

	def merge_lines(self, dist):
		change = False
		i = 0
		while i+1 < len(self.lines):
			this_line = self.lines[i]
			next_line = self.lines[i+1]
			if len(this_line.words) == 0:
				self.lines.pop(i)
				continue
			elif len(next_line.words) == 0:
				self.lines.pop(i+1)
				continue
			_, this_y, _, this_h = this_line.get_text_corners()
			_, next_y, _, next_h = next_line.get_text_corners()
			if next_y < this_y + this_h - dist:
				this_line.words.extend(next_line.words)
				this_line.words = sorted(this_line.words, key=lambda word: word.x)
				this_line.length += next_line.length
				self.lines.pop(i+1)
			else:
				i += 1
		return change

	def white_segment(self):
		im = make_image(self.w, self.h, [])
		return Segment(im, self.x, self.y)

	def widen_to_lines(self):
		for line in self.lines:
			if len(line.words) == 0:
				continue
			_, y, _, h = line.get_text_corners()
			if y < self.y:
				self.h += self.y - y
				self.y = y
			if self.y+self.h < y+h:
				self.h += y+h - (self.y+self.h)
