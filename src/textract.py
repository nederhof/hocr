import sys
import json
from PIL import Image

from imageprocessing import make_image
from segments import Segment

class TextractPage:
	def __init__(self, filename):
		self.im = Image.open(filename)
		self.w, self.h = self.im.size
		with open(filename + '.textract.json', 'r') as f:
			self.results = json.load(f)
		blocks = self.results['Blocks']
		self.words = []
		for block in blocks:
			if block['BlockType'] == 'WORD':
				self.words.append(TextractWord(block, self.w, self.h))

class TextractWord:
	def __init__(self, block, w, h):
		self.content = block['Text']
		self.confidence = block['Confidence'] / 100
		bb = block['Geometry']['BoundingBox']
		self.x = round(bb['Left'] * w)
		self.y = round(bb['Top'] * h)
		self.w = round(bb['Width'] * w)
		self.h = round(bb['Height'] * h)
		
	def white_segment(self):
		im = make_image(self.w, self.h, [])
		return Segment(im, self.x, self.y)

# For testing
def open_window(filename):
	import tkinter as tk
	from rectangleselection import RectangleSelector
	root = tk.Tk()
	app = RectangleSelector(root, lambda segments: print(len(segments)))
	page = TextractPage(filename)
	segments = [word.white_segment() for word in page.words if word.confidence < 0.8]
	app.set_image(filename)
	app.set_segments(segments)
	app.mainloop()

# For testing
def list_words(filename):
	page = TextractPage(filename)
	for word in page.words():
		if word.confidence < 0.8:
			print(word.x, word.y, word.w, word.h, word.content, word.confidence)

# For testing
if __name__ == '__main__':
	# if len(sys.argv) >= 2:
		# filename = sys.argv[1]
		# open_window(filename)
	open_window('/home/mjn/work/topbib/topbib/ocr/vol1/1.png')
