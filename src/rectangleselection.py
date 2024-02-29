import sys
import tkinter as tk

from zoomimage import ZoomImage

class RectangleSelector(ZoomImage):
	def __init__(self, root, callback):
		self.root = root
		tk.Frame.__init__(self, self.root)
		self.title = 'Select rectangles'
		self.set_tools(callback)
		self.create_menu()
		self.create_layout()

	def set_tools(self, callback):
		self.master.bind('<Control-m>', lambda event: self.move_mode())
		self.master.bind('<Control-g>', lambda event: self.segment_mode())
		self.master.bind('<Control-d>', lambda event: self.delete_mode())
		self.tools = [('Move', self.move_mode, 'Ctrl+M'),
						('Segment', self.segment_mode, 'Ctrl+G'),
						('Delete', self.delete_mode, 'Ctrl+D')]
		self.save_image = lambda: self.terminate(callback)

	def set_segments(self, segments):
		self.segments = segments
		self.delayed_redraw()

	def draw_annotations(self):
		if self.drag_start is not None:
			if self.mode == 'segment':
				self.canvas.create_rectangle(self.drag_start[0], self.drag_start[1], self.x_canvas, self.y_canvas, 
					outline='red', width=2)
			elif self.mode == 'delete':
				self.canvas.create_rectangle(self.drag_start[0], self.drag_start[1], self.x_canvas, self.y_canvas, 
					outline='gray', width=6)
		self.draw_segments()
	
	def end_drag_annotations(self):
		if self.drag_start is None:
			return
		elif self.mode == 'segment':
			self.single_segment(self.drag_start, (self.x_canvas, self.y_canvas))
		elif self.mode == 'delete':
			self.delete_segment(self.drag_start, (self.x_canvas, self.y_canvas))

	def move_mode(self):
		self.mode = 'move'

	def segment_mode(self):
		self.mode = 'segment'

	def delete_mode(self):
		self.mode = 'delete'

	def terminate(self, callback):
		self.destroy()
		callback(self.segments)

def open_selector(filename, segments, callback):
	root = tk.Tk()
	app = RectangleSelector(root, callback)
	app.set_image(filename)
	app.set_segments(segments)
	app.mainloop()

if __name__ == '__main__':
	root = tk.Tk()
	app = RectangleSelector(root, lambda segments: print(len(segments)))
	if len(sys.argv) >= 2:
		filename = sys.argv[1]
		app.set_image(filename)
	app.mainloop()
