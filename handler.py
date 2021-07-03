from http.server import BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
	def do_OPTIONS(self):
		self.wfile.write('\r\n'.join([
			'HTTP/1.1 200 OK',
			'Access-Control-Allow-Origin: *',
			'Access-Control-Allow-Methods: *',
			'Access-Control-Allow-Headers: Authorization',
			''
		]).encode('utf-8'))
	def do_GET(self):
		args = self.path.split('?')
		if len(args) == 2: path, params = args
		elif len(args) == 1: path = args[0]
		params = [
			arg.split('=')
			for arg in params.split('&')
		]
		params = {arg[0]: arg[1] for arg in params}

		# Check for auth
		if not 'Authorization' in self.headers:
			return self.send_json({
				'success': False,
				'message': 'You must be authorized to use this API!'
			})
		params['public_key'] = self.headers['Authorization']

		if all([path == '/vote', 'vote' in params]):
			self.server.queue.append(params)
			return self.send_json({
				'success': True,
				'message': 'voting added to queue successfully!'
			})
		self.send_json({
			'success': False,
			'error': f'Cannot GET {path}'
		})
	def send_json(self, data):
		self.wfile.write('\r\n'.join([
			'HTTP/1.1 200 OK',
			'Content-Type: application/json',
			'Access-Control-Allow-Origin: *',
			'Access-Control-Allow-Methods: *',
			'Access-Control-Allow-Headers: Authorization',
			'',
			json.dumps(data)
		]).encode('utf-8'))

