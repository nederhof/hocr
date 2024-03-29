import os 
import csv
import shutil
from PIL import Image
from Levenshtein import distance

from train import default_sign_model_dir
from transcribe import FontInfo, image_to_encoding
from imageprocessing import normalize_image
from ocrresults import prepare_transcription_dir

test_dir = 'tests'
target_dir = 'transcriptions'
cutout_dir = 'evalcutouts'
eval_name = 'eval.html'
model_dir = default_sign_model_dir
fontinfo = FontInfo(model_dir)

preamble = """<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>OCR results</title>
<link rel="stylesheet" type="text/css" href="hierojax.css" />
<style>
table, th, td { border: 1px solid; }
img { max-height: 30px; }
.wrong { color: red; }
</style>
<script type="text/javascript" src="hierojax.js"></script>
<script type="text/javascript">
	window.addEventListener("DOMContentLoaded", () => { hierojax.processFragments(); });
</script>
</head>
<body>
"""
postamble = """</body>
</html>
"""

table_header = '<tr><th>file</th><th>image</th>' + \
			'<th>ground truth</th><th>OCR</th></tr>\n'

def read_page_csv(csv_file):
	with open(csv_file) as handler:
		reader = csv.reader(handler, delimiter=' ')
		rows = list(reader)
	return [{'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h), 'ch': ch} for x, y, w, h, ch in rows]

def read_test_csv(csv_file):
	with open(csv_file) as handler:
		reader = csv.reader(handler, delimiter=' ')
		rows = list(reader)
	return rows

def hiero_span(h, correct):
	cl = 'hierojax' if correct else 'hierojax wrong'
	return f'<span class="{cl}" style="font-size: 30px;" data-bracketcolor="blue" data-sep="0.15">' + h + '</span>'

def eval_row(label, im, cutout_file, truth):
	trans = image_to_encoding(im, fontinfo, dir='h')
	n = len(truth)
	hits = max(n - distance(truth, trans), 0)
	correct = (truth == trans)
	row = '<tr><th>' + label + '</th>' + \
		'<td>' + f'<img src="{cutout_file}">' + '</td>' + \
		'<td>' + hiero_span(truth, True) + '</td>' + \
		'<td>' + hiero_span(trans, correct) + '</td></tr>\n'
	return n, hits, row

def eval_rows(name, im_file, csv_file, count):
	hieros = read_page_csv(csv_file)
	label = name
	n_total = 0
	hits_total = 0
	rows_total = ''
	if len(hieros) > 0:
		im = Image.open(im_file)
		for hiero in hieros:
			im_sub = im.crop((hiero['x'], hiero['y'], hiero['x'] + hiero['w'], hiero['y'] + hiero['h']))
			cutout_name = str(count) + '.png'
			cutout_path = os.path.join(target_dir, cutout_dir, cutout_name)
			cutout_rel = os.path.join(cutout_dir, cutout_name)
			im_sub.save(cutout_path)
			n, hits, row = eval_row(label, im_sub, cutout_rel, hiero['ch'])
			n_total += n
			hits_total += hits
			rows_total += row
			label = ''
			count += 1
	return n_total, hits_total, rows_total, count

def eval_test_row(name, truth):
	path = os.path.join(test_dir, name)
	cpy = os.path.join(target_dir, cutout_dir, name) 
	rel = os.path.join(cutout_dir, name)
	shutil.copy(path, cpy)
	im = normalize_image(Image.open(path))
	trans = image_to_encoding(im, fontinfo, dir='h')
	n = len(truth)
	hits = max(n - distance(truth, trans), 0)
	correct = (truth == trans)
	row = f'<tr><th>{name}</th>' + \
		'<td>' + f'<img src="{rel}">' + '</td>' + \
		'<td>' + hiero_span(truth, True) + '</td>' + \
		'<td>' + hiero_span(trans, correct) + '</td></tr>\n'
	return n, hits, row

def eval_results(pages):
	n_total = 0
	hits_total = 0
	rows_total = ''
	count = 0
	for name, im_file in pages:
		csv_file = im_file + '.csv'
		if os.path.exists(csv_file):
			n, hits, rows, count = eval_rows(name, im_file, csv_file, count)
			n_total += n
			hits_total += hits
			rows_total += rows
	table = '<table>\n' + table_header + rows_total + '</table>\n'
	accuracy = '<p>Accuracy ' + '{:3.4f} '.format(hits_total / n_total) + \
		f'[{hits_total} of {n_total}]' + '</p>\n'
	return table + accuracy

def eval_test_results(tests):
	n_total = 0
	hits_total = 0
	rows = ''
	for test, ch in tests:
		n, hits, row = eval_test_row(test, ch)
		n_total += n
		hits_total += hits
		rows += row
	table = '<table>\n' + table_header + rows + '</table>\n'
	accuracy = '<p>Accuracy ' + '{:3.4f} '.format(hits_total / n_total) + \
		f'[{hits_total} of {n_total}]' + '</p>\n'
	return table + accuracy

def get_pages():
	pages = []
	d = '/home/mjn/work/topbib/topbib/ocr/vol1'
	numbers = range(1, 101)
	# numbers = range(63, 64)
	for num in numbers:
		image_name = str(num) + '.png'
		image_file = os.path.join(d, image_name)
		pages.append((str(num), image_file))
	return pages

def prepare_target_dir():
	cutout_path = os.path.join(target_dir, cutout_dir)
	if not os.path.exists(cutout_path):
		os.mkdir(cutout_path)

def store_html(body):
	html = preamble + body + postamble
	html_file = os.path.join(target_dir, eval_name)
	with open(html_file, 'w') as handle:
		handle.write(html)

def store_eval():
	pages = get_pages()
	body = eval_results(pages)
	store_html(body)

def store_test_eval():
	tests = read_test_csv(os.path.join(test_dir, 'index.csv'))
	body = eval_test_results(tests)
	store_html(body)

def do_pages():
	prepare_target_dir()
	store_eval()

def do_tests():
	prepare_target_dir()
	store_test_eval()

if __name__ == '__main__':
	# do_pages()
	do_tests()
