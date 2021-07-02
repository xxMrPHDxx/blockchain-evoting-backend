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
			vote = server.queue.pop()
			voter_id     = vote['voter']
			candidate_id = vote['candidate']
			election_id  = vote['election']

			# Check for the voter
			cursor = db.execute(f'SELECT public_key FROM voters	WHERE id={voter_id}')
			if not cursor:
				print(f'Warning: Ignoring invalid voter id {voter_id}')
				continue
			public_key = cursor.next()[0]

			# Check for existing vote
			cursor = db.execute('''
					SELECT id FROM votes
						WHERE voter_id=%s AND candidate_id=%s AND election_id=%s
			''', (voter_id, candidate_id, election_id))
			if cursor and cursor.rowcount == 0:
				# Create a new vote if it's not exist
				cursor = db.execute('''
					INSERT INTO votes 
						(voter_id, candidate_id, election_id) 
						VALUE (%s, %s, %s)
				''', (voter_id, candidate_id, election_id))
				db.commit()

				# Get the inserted vote's id
				cursor = db.execute('''
						SELECT id FROM votes
							WHERE voter_id=%s AND candidate_id=%s AND election_id=%s
				''', (voter_id, candidate_id, election_id))
				vote_id = cursor.next()[0]

				# Sign the vote and get the sign
				exit(requests.post(
					'http://localhost/blockchain/ajax.php?action=sign',
					headers={
						'Authorization': base64.b64encode(public_key.encode('utf-8'))
					},
					data={'vote_id': vote_id}
				).text)

				# Update the signature
				cursor = db.execute(f"UPDATE votes SET signature='{signature}'")
				db.commit()
			else:
				print('Warning: Vote already exists!')
				continue

			# Check for existing block chain
			cursor = db.execute('''
				SELECT id FROM blockchains WHERE election_id=%s
			''', (election_id,))
			if cursor:
				if cursor.rowcount == 0:
					# Using a default difficulty
					difficulty = 4

					# Create a new block chain
					chain = Blockchain(difficulty=difficulty)
					print('Chain created!', chain)

					# Encrypt the block data
					block_data = json.loads(requests.post(
						'http://localhost/blockchain/ajax.php?action=encrypt',
						headers={
							'Authorization': base64.b64encode(public_key.encode('utf-8'))
						},
						data={'data': json.dumps({'vote_id': vote_id})}
					).text)['data']

					# Adding new head block to it
					chain.add(block_data)

					# Check if head block is not inserted yet
					block = chain.blocks[-1]
					cursor = db.execute(
						f"SELECT * FROM blocks WHERE hash='{block.hash}'"
					)
					if cursor and cursor.rowcount == 0:
						# Insert the head block into the blocks table
						cursor = db.execute(
							'INSERT INTO blocks ' +
							'(data, nonce, prev_hash, hash) ' + 
							'VALUE (%s, %s, %s, %s)', 
							(block.data, block.nonce, block.prev, block.hash)
						)
						db.commit()
					
					# Get the block id from the hash
					cursor = db.execute(
							f"SELECT id FROM blocks WHERE hash='{block.hash}'"
					)
					block_id = cursor.next()[0]
					print('Block ID', block_id)

					# Insert the chain into blockchains table
					cursor = db.execute('''
						INSERT INTO blockchains (block_id, election_id, difficulty)
						 VALUE (%s, %s, %s)
					''', (block_id, election_id, difficulty))
					db.commit()

					# The the inserted blockchain id
					cursor = db.execute(
						f"SELECT id FROM blockchains WHERE election_id={election_id}"
					)
					blockchains[int(cursor.next()[0])] = chain
				elif cursor.rowcount == 1:
					# Use that existing block chain
					chain = blockchains[int(cursor.next()[0])]

					print('Found existing chain', chain)
			continue

if __name__ == '__main__':
	server = HTTPServer(('0.0.0.0', 8000), Handler)
	server.queue = [] # The queue for the incoming votes
	
	Thread(target=enqueue_voting, daemon=True, args=(server, )).start()
	server.serve_forever()
