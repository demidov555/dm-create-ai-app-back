import os
from cassandra.cluster import Cluster
from dotenv import load_dotenv

load_dotenv()

CASSANDRA_KEYSPACE = os.getenv("CASSANDRA_KEYSPACE")
CASSANDRA_PORT = os.getenv("CASSANDRA_PORT")


class Database:
    def __init__(self):
        if not CASSANDRA_KEYSPACE or not CASSANDRA_PORT:
            raise EnvironmentError("Установите CASSANDRA_KEYSPACE и CASSANDRA_PORT в .env")

        self.keyspace = CASSANDRA_KEYSPACE
        self.cluster = Cluster(
            contact_points=[os.getenv("CASSANDRA_HOST")],
            port=int(CASSANDRA_PORT)
        )
        self.session = self.cluster.connect(self.keyspace)

    def get_session(self):
        return self.session

    def close(self):
        self.cluster.shutdown()


db = Database()
get_session = db.get_session
