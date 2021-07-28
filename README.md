# Blockchain backend mining

This server acts as a mining central for the voting system and
uses a queue and is totally responsible for the blockchain and 
the blocks table. Any votes from the user is directly added into
the votes table.

## Pre-requisites
Make sure you create a filed named "config.json" which contains
the appropriate schema

## How to run
Simply run this command in terminal: `python3 server.py`
