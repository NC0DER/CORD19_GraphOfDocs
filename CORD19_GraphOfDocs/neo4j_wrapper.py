from neo4j import GraphDatabase
from neo4j.exceptions import ConstraintError, CypherError, ServiceUnavailable

class Neo4jDatabase(object): 
    """
    Wrapper class which handles the database 
    more efficiently, by abstracting repeating code.
    """
    def __init__(self, uri, user, password): # Create the database connection.
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted = False)

    def close(self):
        self._driver.close()

    def execute(self, query, mode): # Execute queries in the database.
        with self._driver.session() as session:
            try:
                if (mode == 'r'): # Reading query.
                    result = session.read_transaction(self.__execute, query).values()
                elif(mode == 'w'): # Writing query.
                    result = session.write_transaction(self.__execute, query).values()
                elif(mode == 'g'): # Returning graph data query.
                    result = session.read_transaction(self.__execute, query).data()
                else:
                    raise TypeError('Execution mode can either be (r)ead, (w)rite or (g)raph data!')
                return result
            except (CypherError, ConstraintError) as err:
                print(err) # Handle the erroneous query instead of breaking the execution.

    @staticmethod # static private method.
    def __execute(tx, query):
        try:
            result = tx.run(query)
            return result
        except (CypherError, ConstraintError) as err:
            print(err) # Handle the erroneous query instead of breaking the execution.