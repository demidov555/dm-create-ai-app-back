import os
from cassandra.cluster import Cluster
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        self.keyspace = os.getenv("CASSANDRA_KEYSPACE")
        self.cluster = Cluster(
            contact_points=[os.getenv("CASSANDRA_HOST")],
            port=int(os.getenv("CASSANDRA_PORT"))
        )
        self.session = self.cluster.connect(self.keyspace)

    def get_session(self):
        return self.session

    def close(self):
        self.cluster.shutdown()


db = Database()
get_session = db.get_session
