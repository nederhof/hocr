from flask import Flask, send_from_directory, redirect, request, url_for
from lxml import html
import webbrowser
import sys
import threading
import os
import signal
import logging
import re

PORT = 8000

def open_browser(page):
	app = Flask(__name__)
	log = logging.getLogger('werkzeug')
	log.setLevel(logging.ERROR)
	
	def start_server():
		app.run(host='0.0.0.0', port=PORT)

	@app.route('/<path:path>', methods=['GET'])
	def present_page(path):
		return send_from_directory('', path)
	
	@app.route('/end', methods=['DELETE'])
	def end_server():
		text = request.json['text']
		text = re.sub(r'\n+</body>', '\n</body>', text)
		with open(page, 'w') as file:
			file.write(text)
		os.kill(os.getpid(), signal.SIGTERM)
		return 'Server shutting down...'

	server_thread = threading.Thread(None, start_server, 'server', []) 
	server_thread.start()
	webbrowser.open(f'http://127.0.0.1:{PORT}/{page}', new=0)
	server_thread.join()

if __name__ == '__main__':
	if len(sys.argv) == 2:
		page = sys.argv[1]
		open_browser(page)
	else:
		print('Provide exactly one argument, which is filename')
