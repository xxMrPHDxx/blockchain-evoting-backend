import mysql.connector

class Database():
	def __init__(self, host, user, password, database):
		self.__conn = mysql.connector.connect(
				host=host,
				user=user,
				password=password,
				database=database,
				auth_plugin='mysql_native_password'
		)
	def commit(self):
		self.__conn.commit()
	def execute(self, stmt, args=None):
		cursor = self.__conn.cursor(buffered=True)
		if args is None: cursor.execute(stmt)
		else: cursor.execute(stmt, args)
		return cursor
