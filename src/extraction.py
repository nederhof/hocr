import tkinter as tk

from imageprocessing import area
from segments import Segment, image_to_segments, MIN_SEGMENT_AREA
from storing import SignStorer, LetterStorer
from transcribe import FontInfo as FontInfoSigns
from simpleocr import FontInfo as FontInfoLetters, median_height
from zoomimage import ZoomImage

sign_model_dir = 'signmodel'
letter_model_dir = 'lettermodel'

class Extractor(ZoomImage):
	def __init__(self, root):
		self.root = root
		tk.Frame.__init__(self, self.root)
		self.set_tools()
		self.create_menu()
		self.create_layout()

	def set_tools(self):
		self.master.bind('<Control-m>', lambda event: self.move_mode())
		self.master.bind('<Control-g>', lambda event: self.segment_mode())
		self.master.bind('<Control-p>', lambda event: self.parse_mode())
		self.master.bind('<Control-d>', lambda event: self.delete_mode())
		self.master.bind('<Control-c>', lambda event: self.classify())
		self.tools = [('Move', self.move_mode, 'Ctrl+M'),
						('Segment', self.segment_mode, 'Ctrl+G'),
						('Parse', self.parse_mode, 'Ctrl+P'),
						('Delete', self.delete_mode, 'Ctrl+D'),
						('Classify', self.classify, 'Ctrl+C')]
		self.save_image = None

	def set_image(self, path):
		ZoomImage.set_image(self, path)
		self.adjust_fontinfo()

	def draw_annotations(self):
		if self.drag_start is not None:
			if self.mode == 'segment':
				self.canvas.create_rectangle(self.drag_start[0], self.drag_start[1], self.x_canvas, self.y_canvas, 
					outline='red', width=2)
			elif self.mode == 'parse':
				self.canvas.create_rectangle(self.drag_start[0], self.drag_start[1], self.x_canvas, self.y_canvas, 
					outline='red', dash=(3,5), width=2)
			elif self.mode == 'delete':
				self.canvas.create_rectangle(self.drag_start[0], self.drag_start[1], self.x_canvas, self.y_canvas, 
					outline='gray', width=6)
		self.draw_segments()

	def end_drag_annotations(self):
		if self.drag_start is None:
			return
		elif self.mode == 'segment':
			self.single_segment(self.drag_start, (self.x_canvas, self.y_canvas))
		elif self.mode == 'parse':
			self.parse_segment(self.drag_start, (self.x_canvas, self.y_canvas))
		elif self.mode == 'delete':
			self.delete_segment(self.drag_start, (self.x_canvas, self.y_canvas))

	def move_mode(self):
		self.mode = 'move'

	def segment_mode(self):
		self.mode = 'segment'

	def parse_mode(self):
		self.mode = 'parse'

	def delete_mode(self):
		self.mode = 'delete'

	def parse_segment(self, p1, p2):
		if self.image is None:
			return
		x, y, im = self.subimage(p1, p2)
		segments = self.extract_signs(im)
		for segment in segments:
			self.segments.append(segment.transpose(x, y))
		self.delayed_redraw()

	def classify(self):
		if len(self.segments) > 0:
			segment = self.segments.pop(0)
			self.delayed_redraw()
			sub = tk.Toplevel()
			self.storer(sub, segment.im, self.fontinfo, self.classify)

class SignExtractor(Extractor):
	def __init__(self, root):
		self.storer = SignStorer
		self.fontinfo = FontInfoSigns(sign_model_dir)
		self.threshold = 128
		self.title = 'Sign extractor'
		Extractor.__init__(self, root)

	def extract_signs(self, im):
		segments = image_to_segments(im, self.threshold) 
		# merged = Segment.merge_with_overlap(segments)
		return [segment for segment in segments if area(segment.im) >= MIN_SEGMENT_AREA]

	def adjust_fontinfo(self):
		None

class LetterExtractor(Extractor):
	def __init__(self, root):
		self.storer = LetterStorer
		self.fontinfo = FontInfoLetters(letter_model_dir)
		self.threshold = 110
		self.title = 'Letter extractor'
		Extractor.__init__(self, root)

	def extract_signs(self, im):
		segments = image_to_segments(im, self.threshold) 
		merged = Segment.merge_with_stack(segments)
		return [segment for segment in merged if area(segment.im) >= MIN_SEGMENT_AREA]

	def adjust_fontinfo(self):
		self.fontinfo.unit_height = median_height(self.image, threshold=self.threshold)
