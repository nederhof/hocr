import os
from PIL import Image, ImageFont, ImageDraw, ImageOps

font_name = 'signlist/NewGardinerSMP.ttf'
font_size = 50
font = ImageFont.truetype(font_name, font_size)

target_dir = 'newgardiner'

def dump_char(c):
	img = Image.new('RGB', (2 * font_size, 2 * font_size), (255, 255, 255))
	draw = ImageDraw.Draw(img)
	draw.text((0, 0), c, font=font, fill='black')
	inverted = ImageOps.invert(img)		
	bbox = inverted.getbbox()
	img = img.crop(bbox)
	img.save(os.path.join(target_dir, str(ord(c)) + '.png'))

def dump_font():
	if not os.path.exists(target_dir):
		os.mkdir(target_dir)
	chars = list(range(0x13000, 0x1342F + 1)) + [0x5B, 0x5D]
	for c in chars:
		dump_char(chr(c))

if __name__ == '__main__':
	dump_font()
