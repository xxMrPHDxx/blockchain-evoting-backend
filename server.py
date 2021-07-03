from http.server import HTTPServer
from threading import Thread
import requests
import base64
import json
import time
import re

from blockchain import Blockchain
from handler import Handler
from db import Database

'''
The structure would be

	Blockchains               : The elections
	Blocks in each blockchain : Votes in each election

'''

blockchains = {} # TODO: Populate this from db to get existing blockchains

def enqueue_voting(server):
	db = Database('127.0.0.1', 'root', 'password', 'blockchain')

	# populating the blockchains cache
	cursor = db.execute(
			f"SELECT id, difficulty, block_id FROM blockchains"
	)
	if cursor and cursor.rowcount > 0:
		# Go through all chains
		for blockchain in cursor:
			chain_id, difficulty, block_id = blockchain
			chain = Blockchain(difficulty=difficulty)
			
			# Getting the head block
			cursor = db.execute(
				f"SELECT data, hash FROM blocks WHERE id={block_id}"
			)
			if not cursor or cursor.rowcount != 1:
				print('Warning, empty blockchain with no head block detected!')
				continue
			block_data, block_hash = cursor.next()
			chain.add(block_data)
			assert chain.blocks[-1].hash == block_hash, 'Unmatched hash!'

			# Go through all blocks in each chain (excluding the head)
			while True:
				cursor = db.execute(
					f"SELECT data, hash FROM blocks WHERE prev_hash='{block_hash}'"
				)
				if not cursor or cursor.rowcount != 1:
					print(f'Found {len(chain.blocks)} blocks for chain {chain_id}!')
					blockchains[chain_id] = chain
					break
				block_data, block_hash = cursor.next()
				chain.add(block_data)
				assert chain.blocks[-1].hash == block_hash, 'Unmatched hash!'

	print('Blockchains cache', blockchains)

	while True:
		time.sleep(1)
		if len(server.queue) > 0:
			print('Found a vote!')
			vote        = server.queue.pop()
			vote_id     = vote['vote']
			election_id = vote['election']
			public_key  = vote['public_key']

			# Sign the vote and get the signature
			result = json.loads(requests.post(
				'http://localhost/blockchain/ajax.php?action=sign',
				headers={
					'Authorization': public_key
				},
				data={'vote_id': vote_id}
			).text)
			if not result['success']:
				print(f'Warning: Failed to sign vote with id {vote_id}')
				print('Voting result', result)

			# Check for existing block chain
			cursor = db.execute(
				f"SELECT id FROM blockchains WHERE election_id={election_id}"
			)
			if cursor:
				if cursor.rowcount == 0:
					# Using a default difficulty
					difficulty = 4

					# Create a new block chain
					chain = Blockchain(difficulty=difficulty)

					# Encrypt the block data
					block_data = json.loads(requests.post(
						'http://localhost/blockchain/ajax.php?action=encrypt',
						headers={
							'Authorization': public_key
						},
						data={'data': json.dumps({'vote_id': vote_id})}
					).text)['data']

					# Adding new head block to it
					chain.add(block_data)

					# Insert the head block into the blocks table
					block = chain.blocks[-1]
					cursor = db.execute(
						'INSERT INTO blocks ' +
						'(data, nonce, prev_hash, hash) ' + 
						'VALUE (%s, %s, %s, %s)', 
						(block.data, block.nonce, block.prev, block.hash)
					)
					db.commit()
					print('Info: Block successfully inserted into db')
					
					# Get the block id from the hash
					cursor = db.execute(
							f"SELECT id FROM blocks WHERE hash='{block.hash}'"
					)
					block_id = cursor.next()[0]

					# Insert the chain into blockchains table
					cursor = db.execute('''
						INSERT INTO blockchains (block_id, election_id, difficulty)
						 VALUE (%s, %s, %s)
					''', (block_id, election_id, difficulty))
					db.commit()
					print('Info: Blockchain successfully inserted into db')

					# Get the inserted blockchain id and insert into cache
					cursor = db.execute(
						f"SELECT id FROM blockchains WHERE election_id={election_id}"
					)
					blockchains[int(cursor.next()[0])] = chain
				elif cursor.rowcount == 1:
					# Use that existing block chain
					chain = blockchains[int(cursor.next()[0])]

					# Encrypt the block data
					block_data = json.loads(requests.post(
						'http://localhost/blockchain/ajax.php?action=encrypt',
						headers={
							'Authorization': public_key.encode('utf-8')
						},
						data={'data': json.dumps({'vote_id': vote_id})}
					).text)['data']

					# Adding new head block to it
					chain.add(block_data)

					# Insert the head block into the blocks table
					block = chain.blocks[-1]
					cursor = db.execute(
						'INSERT INTO blocks ' +
						'(data, nonce, prev_hash, hash) ' + 
						'VALUE (%s, %s, %s, %s)', 
						(block.data, block.nonce, block.prev, block.hash)
					)
					db.commit()
					print('Info: Block successfully inserted into db.')

if __name__ == '__main__':
	server = HTTPServer(('0.0.0.0', 8000), Handler)
	server.queue = [] # The queue for the incoming votes
	
	Thread(target=enqueue_voting, daemon=True, args=(server, )).start()
	server.serve_forever()
