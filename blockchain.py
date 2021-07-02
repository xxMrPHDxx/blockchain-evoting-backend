import hashlib
import json

class Block:
	def __init__(self, chain, data):
		self.__data      = data if type(data) != bytes else data.decode('utf-8')
		self.__nonce     = 0
		self.__prev      = '' if len(chain.blocks) == 0 else chain.blocks[-1].hash
		self.__signature = ''
		self.__hash      = Block.__calc_hash(chain, self)
	@property
	def data(self): return self.__data
	@property
	def nonce(self): return self.__nonce
	@property
	def prev(self): return self.__prev
	@property
	def signature(self): return self.__prev
	@property
	def hash(self): return self.__hash
	def sign(self):
		pass
	def verify(self):
		pass
	def __repr__(self):
		return f'Block(data={self.data},nonce={self.nonce},hash={self.hash})'
	@staticmethod
	def __calc_hash(chain, block):
		target = '0' * chain.difficulty
		res = ''
		while res[:chain.difficulty] != target:
			res = hashlib.sha256(':'.join([
				block.data,
				str(block.nonce),
				block.prev,
				res
			]).encode('utf-8')).hexdigest()
			block.__nonce += 1
		return res

class Blockchain:
	def __init__(self, difficulty=4):
		self.__diff   = difficulty
		self.__blocks = []
	def __iter__(self):
		for block in self.blocks:
			yield block
	@property
	def difficulty(self): return self.__diff
	@property
	def blocks(self): return self.__blocks
	def add(self, data):
		if type(data) == dict: data = json.dumps(data)
		self.blocks.append(Block(chain=self, data=data))

if __name__ == '__main__':
	chain = Blockchain()
	chain.add({'foo': 'bar'})
	chain.add({'one': 'satu'})
	chain.add({'two': 'dua'})

	for block in chain:
		print(block)
