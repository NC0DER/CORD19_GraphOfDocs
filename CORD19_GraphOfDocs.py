import sys
import platform
from neo4j import ServiceUnavailable
from CORD19_GraphOfDocs.neo4j_wrapper import Neo4jDatabase
from CORD19_GraphOfDocs.create import *

def graphofdocs(create, initialize, dirpath, window_size, 
    extend_window, remove_stopwords, lemmatize, stem):

    current_system = platform.system()
    # Open the database.
    try:
        database = Neo4jDatabase('bolt://localhost:7687', 'neo4j', '123')
        # Neo4j server is unavailable.
        # This client app cannot open a connection.
    except ServiceUnavailable as error:
        print('\t* Neo4j database is unavailable.')
        print('\t* Please check the database connection before running this app.')
        input('\t* Press any key to exit the app...')
        sys.exit(1)

    if create:
        # Delete nodes from previous iterations.
        database.execute('MATCH (n) DETACH DELETE n', 'w')

        # Create uniqueness constraint on key to avoid duplicate word nodes.
        create_unique_constraints(database)

        # Create papers and their citations, authors and their affiliations,
        # and the graph of words for each abstract, 
        # which is a subgraph of the total graph of docs.
        create_papers_from_csv(database)
        create_text_authors_citations_from_json(database)
        
    if initialize:
        # Run initialization functions.
        run_initial_algorithms(database)
        create_similarity_graph(database)
        create_co_authors_graph(database)

    database.close()
    return

if __name__ == '__main__': graphofdocs(True, False, None, 4, False, True, False, False)