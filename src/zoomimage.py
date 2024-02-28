import sys
import tkinter as tk
from tkinter.filedialog import askopenfilename
from PIL import Image, ImageTk

from imageprocessing import BLACK_THRESHOLD, transparency_to_white
from segments import Segment, MIN_SEGMENT_AREA, image_to_segments, overlap

KEY_ZOOM_STEP = 1.2
MOUSE_ZOOM_STEP = 1.1
MIN_PIXELS_IN_CANVAS = 10
ARROW_STEP = 0.7
DEFAULT_GEOMETRY = '800x800'

remove_transparency = True

class ZoomImageMenu(tk.Menu):
	def __init__(self, parent):
		tk.Menu.__init__(self, parent.master)
		file = tk.Menu(self, tearoff=False)
		file.add_command(label='Open image', command=parent.open_image, accelerator=parent.acc_open_image)
		if parent.save_image is not None:
			file.add_command(label='Save image', command=parent.save_image, accelerator=parent.acc_save_image)
		file.add_command(label='Exit', command=parent.destroy, accelerator=parent.acc_destroy)
		self.add_cascade(label='File', menu=file)
		if len(parent.tools) > 0:
			tools = tk.Menu(self, tearoff=False)
			for label, command, accelerator in parent.tools:
				tools.add_command(label=label, command=command, accelerator=accelerator)
			self.add_cascade(label='Tools', menu=tools)
		view = tk.Menu(self, tearoff=False)
		view.add_command(label='Maximize', command=parent.maximize, accelerator=parent.acc_maximize)
		view.add_command(label='Default view', command=parent.default_view, accelerator=parent.acc_default_view)
		self.add_cascade(label='View', menu=view)

class ZoomImage(tk.Frame):
	def __init__(self, root):
		self.root = root
		tk.Frame.__init__(self, self.root)
		self.set_tools()
		self.create_menu()
		self.title = None
		self.create_layout()

	def set_tools(self):
		self.tools = []
		self.save_image = None

	def create_menu(self):
		self.master.bind('<Control-o>', lambda event: self.open_image())
		if self.save_image is not None:
			self.master.bind('<Control-s>', lambda event: self.save_image())
		self.master.bind('<Alt-Key-F4>', lambda event: self.destroy())
		self.master.bind('<F11>', lambda event: self.maximize())
		self.master.bind('<F5>', lambda event: self.default_view())
		self.master.protocol('WM_DELETE_WINDOW', self.destroy)
		self.acc_open_image = 'Ctrl+O'
		self.acc_save_image = 'Ctrl+S'
		self.acc_destroy = 'Alt+F4'
		self.acc_maximize = 'F11'
		self.acc_default_view = 'F5'
		self.menu = ZoomImageMenu(self)
		self.menu_empty = tk.Menu(self.master)

	def menubar_show(self):
		self.master.configure(menu=self.menu)

	def menubar_hide(self):
		self.master.configure(menu=self.menu_empty)

	def create_layout(self):
		if self.title is not None:
			self.master.title(self.title)
		else:
			self.master.title('Image Viewer')
		self.master.bind('<ButtonPress-1>', lambda event: self.start_drag())
		self.master.bind('<ButtonRelease-1>', lambda event: self.end_drag())
		self.master.bind('<Button-4>', lambda event: self.zoom_in_mouse(MOUSE_ZOOM_STEP))
		self.master.bind('<Button-5>', lambda event: self.zoom_out_mouse(MOUSE_ZOOM_STEP))
		self.master.bind('<Configure>', lambda event: self.master.after_idle(self.resize))
		self.master.bind('<Key>', lambda event: self.master.after_idle(self.key, event))
		self.master.bind('<Left>', lambda event: self.left())
		self.master.bind('<Right>', lambda event: self.right())
		self.master.bind('<Up>', lambda event: self.up())
		self.master.bind('<Down>', lambda event: self.down())
		self.canvas = tk.Canvas(self.master, bg='gray')
		self.canvas.pack(fill=tk.BOTH, expand=True)
		self.canvas.bind('<Motion>', lambda event: self.motion_canvas())
		self.canvas.bind('<Leave>', lambda event: self.abort_drag())
		self.x_canvas = -1
		self.y_canvas = -1
		self.w_canvas = 0
		self.h_canvas = 0
		self.drag_start = None
		self.mode = 'move'
		self.image = None
		self.segments = []
		self.timer = None
		self.default_view()

	def default_view(self):
		self.scale = 0.000001
		self.center = (0.5, 0.5)
		self.master.geometry(DEFAULT_GEOMETRY)
		self.maximize(state=False)

	def maximize(self, state=None):
		if state is not None:
			self.fullscreen = state
		else:
			self.fullscreen = not self.fullscreen
		if self.fullscreen:
			self.menubar_hide()
		else:
			self.menubar_show()
		self.master.wm_attributes('-fullscreen', self.fullscreen)
		self.resize()

	def set_image(self, path):
		self.image = Image.open(path)
		self.master.title(path)
		if remove_transparency:
			self.image = transparency_to_white(self.image)
		self.image = self.image.convert('L')
		self.w_image, self.h_image = self.image.size
		self.segments = []
		self.adjust_zoom()

	def draw_annotations(self):
		None

	def draw_segments(self):
		for segment in self.segments:
			x1, y1 = self.to_canvas(segment.x, segment.y)
			x2, y2 = self.to_canvas(segment.x + segment.w, segment.y + segment.h)
			self.canvas.create_rectangle(x1, y1, x2, y2, outline='blue', width=2)

	def open_image(self):
		path = askopenfilename(title='Select an image')
		if path != '' and len(path) > 0: 
			self.set_image(path)

	def resize(self):
		self.canvas.update()
		self.w_canvas = self.canvas.winfo_width()
		self.h_canvas = self.canvas.winfo_height()
		self.adjust_zoom()

	def delayed_redraw(self):
		if self.timer is not None:
			self.root.after_cancel(self.timer);
		self.timer = self.root.after(100, self.redraw)

	def redraw(self):
		self.timer = None
		if self.image is None:
			return
		x_min, y_min, w, h = self.visible_rect()
		x_max = x_min + w
		y_max = y_min + h
		cropped = self.image.crop((x_min, y_min, x_max, y_max))
		resized = cropped.resize((self.w_canvas, self.h_canvas))
		self.im = ImageTk.PhotoImage(resized) # attach to self to avoid garbage collection
		self.canvas.delete('all')
		self.canvas.create_image(0, 0, anchor=tk.NW, image=self.im)
		self.draw_annotations()

	def motion_canvas(self):
		if self.image is None:
			return
		self.x_canvas = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
		self.y_canvas = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
		if self.fullscreen:
			if self.y_canvas < 50: # near top of window
				self.menubar_show()
			else:
				self.menubar_hide()
		if self.drag_start is not None:
			if self.mode == 'move':
				x_diff = (self.x_canvas - self.drag_start[0]) / self.scale / self.w_image
				y_diff = (self.y_canvas - self.drag_start[1]) / self.scale / self.h_image
				self.center = (self.center[0] - x_diff, self.center[1] - y_diff)
				self.start_drag()
				self.adjust_pos()
			elif self.mode != 'move':
				self.delayed_redraw()

	def start_drag(self):
		self.drag_start = (self.x_canvas, self.y_canvas)

	def end_drag(self):
		self.end_drag_annotations()
		self.drag_start = None

	def end_drag_annotations(self):
		None

	def single_segment(self, p1, p2):
		if self.image is None:
			return
		x, y, im = self.subimage(p1, p2)
		segments = image_to_segments(im, BLACK_THRESHOLD)
		segment = Segment.merge_big(segments, size=MIN_SEGMENT_AREA)
		if segment is not None:
			self.segments.append(segment.transpose(x, y))
		self.delayed_redraw()

	def delete_segment(self, p1, p2):
		if self.image is None:
			return
		x, y, w, h = self.canvas_corners_to_rect(p1, p2)
		self.segments = [segment for segment in self.segments if \
			not overlap(x, y, w, h, segment.x, segment.y, segment.w, segment.h)]
		self.delayed_redraw()

	def abort_drag(self):
		self.drag_start = None

	def left(self):
		x, y = self.center
		x -=  self.w_canvas / self.w_image / self.scale * ARROW_STEP
		self.center = (x, y)
		self.adjust_pos()

	def right(self):
		x, y = self.center
		x +=  self.w_canvas / self.w_image / self.scale * ARROW_STEP
		self.center = (x, y)
		self.adjust_pos()

	def up(self):
		x, y = self.center
		y -=  self.h_canvas / self.h_image / self.scale * ARROW_STEP
		self.center = (x, y)
		self.adjust_pos()

	def down(self):
		x, y = self.center
		y +=  self.h_canvas / self.h_image / self.scale * ARROW_STEP
		self.center = (x, y)
		self.adjust_pos()

	def zoom_in_mouse(self, step):
		if self.x_canvas < 0 or self.y_canvas < 0:
			self.zoom_in(step)
			return
		x_diff = (self.w_canvas / 2 - self.x_canvas) / self.scale
		y_diff = (self.h_canvas / 2 - self.y_canvas) / self.scale
		self.scale *= step
		x = self.center[0] + (1/step-1) * x_diff / self.w_image
		y = self.center[1] + (1/step-1) * y_diff / self.h_image
		self.center = (x, y)
		self.adjust_zoom()

	def zoom_out_mouse(self, step):
		if self.x_canvas < 0 or self.y_canvas < 0:
			self.zoom_out(step)
			return
		x_diff = (self.w_canvas / 2 - self.x_canvas) / self.scale
		y_diff = (self.h_canvas / 2 - self.y_canvas) / self.scale
		self.scale /= step
		x = self.center[0] + (step-1) * x_diff / self.w_image
		y = self.center[1] + (step-1) * y_diff / self.h_image
		self.center = (x, y)
		self.adjust_zoom()

	def zoom_in(self, step):
		self.scale *= step
		self.adjust_zoom()

	def zoom_out(self, step):
		self.scale /= step
		self.adjust_zoom()

	def adjust_zoom(self):
		if self.image is None:
			return
		if self.scale * self.w_image < self.w_canvas and self.scale * self.h_image < self.h_canvas:
			self.scale = min(self.w_canvas / self.w_image, self.h_canvas / self.h_image)
		elif self.scale * MIN_PIXELS_IN_CANVAS > min(self.w_canvas, self.h_canvas):
			self.scale = min(self.w_canvas, self.h_canvas) / MIN_PIXELS_IN_CANVAS
		self.adjust_pos()

	def adjust_pos(self):
		w = self.w_canvas / self.scale / self.w_image
		h = self.h_canvas / self.scale / self.h_image
		x = 0.5
		y = 0.5
		if w <= 1:
			x = max(self.center[0], w / 2)
			x = min(x, 1 - w / 2)
		if h <= 1:
			y = max(self.center[1], h / 2)
			y = min(y, 1 - h / 2)
		self.center = (x, y)
		self.delayed_redraw()

	def visible_rect(self):
		x = round(self.center[0] * self.w_image - self.w_canvas / 2 / self.scale)
		y = round(self.center[1] * self.h_image - self.h_canvas / 2 / self.scale)
		w = round(self.w_canvas / self.scale)
		h = round(self.h_canvas / self.scale)
		if w < 1 or h < 1:
			return (0, 0, 0, 0)
		else:
			return (x, y, w, h)

	def to_canvas(self, px, py):
		x,y,_,_ = self.visible_rect()
		return round((px - x) * self.scale), round((py - y) * self.scale)

	def from_canvas(self, px, py):
		x,y,_,_ = self.visible_rect()
		return round(px / self.scale + x), round(py / self.scale + y)

	def key(self, event):
		if event.state == 0: # No Control or Alt or Shift
			None
		elif event.state == 1: # Shift
			if event.char == '<':
				self.zoom_out(KEY_ZOOM_STEP)
			elif event.char == '>':
				self.zoom_in(KEY_ZOOM_STEP)

	def destroy(self):
		self.quit()

	def subimage(self, p1, p2):
		x, y, w, h = self.canvas_corners_to_rect(p1, p2)
		im = self.image.crop((x, y, x+w, y+h))
		return x, y, im.convert('L')

	def canvas_corners_to_rect(self, p1, p2):
		x1, y1 = self.from_canvas(p1[0], p1[1])
		x2, y2 = self.from_canvas(p2[0], p2[1])
		x_min = min(x1, x2)
		x_max = max(x1, x2)
		y_min = min(y1, y2)
		y_max = max(y1, y2)
		return x_min, y_min, x_max-x_min, y_max-y_min

if __name__ == '__main__':
	root = tk.Tk()
	app = ZoomImage(root)
	if len(sys.argv) >= 2:
		filename = sys.argv[1]
		app.set_image(filename)
	app.mainloop()
