"""
This script contains functions that 
create data in the Neo4j database.
"""
import re
import json
import platform
import pandas as pd
from timeit import default_timer as timer
from CORD19_GraphOfDocs.algos import *
from CORD19_GraphOfDocs.utils import (
    clear_screen, list_filenames, 
    skip_filenames, read_file, 
    generate_words
)

# Initialize an empty set of edges.
edges = {}
# Initialize an empty list of unique terms.
# We are using a list to preserver order of appearance.
nodes = []

def create_graph_of_words(words, database, filename, relationship, window_size = 4):
    """
    Function that creates a Graph of Words that contains all nodes from each document for easy comparison,
    inside the neo4j database, using the appropriate cypher queries.
    """

    # Files that have word length < window size, are skipped.
    # Window size ranges from 2 to 6.
    length = len(words)
    if (length < window_size):
        # Early exit, we return the skipped filename
        return filename

    # We are using a global set of edges to avoid creating duplicate edges between different graph of words.
    # Basically the co-occurences will be merged.
    global edges

    # We are using a global set of edges to avoid creating duplicate nodes between different graph of words.
    # A list is being used to respect the order of appearance.
    global nodes

    # We are getting the unique terms for the current graph of words.
    terms = []
    creation_list = []
    for word in words:
        if word not in terms: 
            terms.append(word)
    # Remove end-of-sentence token, so it doesn't get created.
    if 'e5c' in terms:
        terms.remove('e5c')
    # If the word doesn't exist as a node, then add it to the creation list.
    for word in terms:
        if word not in nodes:
            creation_list.append(word)
            # Append word to the global node graph, to avoid duplicate creation.
            nodes.append(word)

    # Create all unique nodes, from the creation list.
    database.execute(f'UNWIND {creation_list} as key '
                      'CREATE (word:Word {key: key})', 'w')

    # Create unique connections between existing nodes of the graph.
    for i, current in enumerate(words):
        # If there are leftover items smaller than the window size, reduce it.
        if i + window_size > length:
            window_size = window_size - 1
        # If the current word is the end of sentence string,
        # we need to skip it, in order to go to the words of the next sentence,
        # without connecting words of different sentences, in the database.
        if current == 'e5c':
            continue
        # Connect the current element with the next elements of the window size.
        for j in range(1, window_size):
            next = words[i + j]
            # Reached the end of sentence string.
            # We can't connect words of different sentences,
            # therefore we need to pick a new current word,
            # by going back out to the outer loop.
            if next == 'e5c':
                break
            edge = (current, next)
            if edge in edges:
                # If the edge, exists just update its weight.
                edges[edge] = edges[edge] + 1
                query = (f'MATCH (w1:Word {{key: "{current}"}})-[r:connects]-(w2:Word {{key: "{next}"}}) '
                         f'SET r.weight = {edges[edge]}')
            else:
                # Else, create it, with a starting weight of 1 meaning first co-occurence.
                edges[edge] = 1
                query = (f'MATCH (w1:Word {{key: "{current}"}}) '
                         f'MATCH (w2:Word {{key: "{next}"}}) '
                         f'MERGE (w1)-[r:connects {{weight: {edges[edge]}}}]-(w2)')
            # This line of code, is meant to be executed, in both cases of the if...else statement.
            database.execute(query, 'w')

    # Connect the paper, with all of its words.
    query = (f'MATCH (w:Word) WHERE w.key IN {terms} '
              'WITH collect(w) as words '
             f'MATCH (p:Paper {{filename: "{filename}"}}) '
              'UNWIND words as word '
             f'CREATE (p)-[:{relationship}]->(word)')
    database.execute(query, 'w')
    return

def run_initial_algorithms(database):
    """
    Function that runs centrality & community detection algorithms,
    in order to prepare the data for analysis and visualization.
    Pagerank & Louvain are used, respectively.
    The calculated score for each node of the algorithms is being stored
    on the nodes themselves.
    """
    # Append the parameter 'weight' for the weighted version of the algorithm.
    pagerank(database, 'Word', 'connects', 20, 'pagerank')
    pagerank(database, 'Paper', 'cites', 20, 'pagerank')
    louvain(database, 'Word', 'connects', 'community')
    louvain(database, 'Paper', 'cites', 'community')
    return

def create_similarity_graph(database):
    """
    Function that creates a similarity graph
    based on Jaccard similarity measure.
    This measure connects the paper nodes with each other
    using the relationship 'is_similar', 
    which has the similarity score as a property.
    In order to prepare the data for analysis and visualization,
    we use Louvain Community detection algorithm.
    The calculated community id for each node is being stored
    on the nodes themselves.
    """
    # Remove similarity edges from previous iterations.
    database.execute('MATCH ()-[r:is_similar]->() DELETE r', 'w')

    # Create the similarity graph using Jaccard similarity measure.
    jaccard(database, 'Paper', 'includes', 'Word', 0.23, 'is_similar', 'score')

    # Find all similar document communities.
    # Append the parameter 'score' for the weighted version of the algorithm.
    louvain(database, 'Paper', 'is_similar', 'community')
    print('Similarity graph created.')
    return

def create_unique_constraints(database):
    """
    Wrapper function that gathers all CREATE CONSTRAINT queries,
    in one place.
    """
    database.execute('CREATE CONSTRAINT ON (word:Word) '
                     'ASSERT word.key IS UNIQUE', 'w')
    database.execute('CREATE CONSTRAINT ON (paper:Paper) '
                     'ASSERT paper.uid IS UNIQUE', 'w')
    database.execute('CREATE CONSTRAINT ON (author:Author) '
                     'ASSERT author.name IS UNIQUE', 'w')
    database.execute('CREATE CONSTRAINT ON (location:Location) '
                     'ASSERT location.name IS UNIQUE', 'w')
    database.execute('CREATE CONSTRAINT ON (institution:Institution) '
                     'ASSERT institution.name IS UNIQUE', 'w')
    database.execute('CREATE CONSTRAINT ON (laboratory:Laboratory) '
                     'ASSERT laboratory.name IS UNIQUE', 'w')
    return

def create_papers_from_csv(database):
    """
    Function that creates the nodes representing papers,
    by reading each row on the csv.
    """
    filename = r'C:\Users\USER\Desktop\CORD-19-research-challenge\metadata.csv'
    current_system = platform.system()
    
    # Read csv into a pandas dataframe.
    df = pd.read_csv(filename)

    skip_count = 0
    count = 1
    total_count = len(df.index)

    # Skip the first (header) row of the csv.
    for index, row in df.iterrows():
        # Print the number of the currently processed file.
        print(f'Processing {count} out of {total_count} papers...' )

        # If the row doesn't have a title or a filename, then skip it.
        if pd.isnull(row['sha']) or pd.isnull(row['title']):
            skip_count = skip_count + 1
            count = count + 1
            continue

        # Filename field occasionally includes an second unrelated filename,
        # Which is delimited by ';', therefore it is removed below.
        filename = row['sha'].split(';', 1)[0]

        # Title field occasionally includes single or double quotes,
        # which make the create query fail, therefore it is removed below.
        title = row['title'].translate({ord(c): '' for c in '\'\"'})

        # Construct the query, based on columns of the row.
        query = (
                f'CREATE (p:Paper {{uid: "{row["cord_uid"]}", '
                f'filename: "{filename}", '
                f'source: "{row["source_x"]}", '
                f'title: "{title}", '
                f'publish_time: "{row["publish_time"]}", '
                f'url: "{row["url"]}", '
                f'journal: "{row["journal"]}"}})'
        )
        # Replace NaN values from dataframe, with the string literal None.
        query = query.replace('"nan"', '"None"')

        # Update the progress counter.
        count = count + 1
        # Clear the screen to output the update the progress counter.
        clear_screen(current_system)
        database.execute(query, 'w')
    print(f'Created {total_count - skip_count}, skipped {skip_count} papers.')
    return

def create_authors(filename, obj, database):
    """
    Wrapper function that extracts all authors and their affiliations
    from the json object. Each of the authors and their affiliations 
    are created and connected.
    """
    authors = []
    for item in obj['metadata']['authors']:
        # Iterate json obj to find author names and their affiliations.
        name = ''.join([item['first'], ' ', '' if item['middle'] == [] \
            else item['middle'][0] + '. ' if len(item['middle'][0]) == 1 \
            else ' '.join(item['middle']) + ' ', item['last']])
        location = '' if item['affiliation'] == {} \
            else '' if item['affiliation']['location'] == {} \
            else '' if 'country' not in item['affiliation']['location'] \
            else item['affiliation']['location']['country']
        institution = '' if item['affiliation'] == {} \
            else item['affiliation']['institution']
        laboratory = '' if item['affiliation'] == {} \
            else item['affiliation']['laboratory']

        # Replace possible empty entries with the string literal 'None'
        # Also if the string is non-empty remove single or double quotes,
        # which make create queries fail.
        location = '' if location == '' \
            else location.translate({ord(c): '' for c in '\'\"'})
        institution = '' if institution == '' \
            else institution.translate({ord(c): '' for c in '\'\"'})
        laboratory = '' if laboratory == '' \
            else laboratory.translate({ord(c): '' for c in '\'\"'})

        # Merge all info of authors into the database.
        query = f'MERGE (a:Author {{name: "{name}"}}) '
        database.execute(query, 'w')

        # Save all authors into a list for the current paper.
        authors.append(name)

        if location != '':
            database.execute(f'MERGE (l:Location {{name: "{location}"}})', 'w')
            query = (
                f'MATCH (a:Author {{name: "{name}"}}) '
                f'MATCH (l:Location {{name: "{location}"}}) '
                f'MERGE (a)-[:affiliates_with]->(l)'
            )
            database.execute(query, 'w')

        if institution != '':
            database.execute(f'MERGE (i:Institution {{name: "{institution}"}})', 'w')
            query = (
                f'MATCH (a:Author {{name: "{name}"}}) '
                f'MATCH (i:Institution {{name: "{institution}"}}) '
                f'MERGE (a)-[:affiliates_with]->(i)'
            )
            database.execute(query, 'w')

        if laboratory != '':
            database.execute(f'MERGE (l:Laboratory {{name: "{laboratory}"}})', 'w')
            query = (
                f'MATCH (a:Author {{name: "{name}"}}) '
                f'MATCH (l:Laboratory {{name: "{laboratory}"}}) '
                f'MERGE (a)-[:affiliates_with]->(l)'
            )
            database.execute(query, 'w')

    # Connect all authors of the paper, with the paper, itself.
    query = (f'MATCH (a:Author) WHERE a.name IN {authors} '
              'WITH collect(a) as authors '
             f'MATCH (p:Paper {{filename: "{filename}"}}) '
              'UNWIND authors as author '
              'CREATE (author)-[:writes]->(p)')
    database.execute(query, 'w')
    return

def create_citations(filename, obj, database):
    """
    Wrapper function that extracts all titles of the cited papers
    from the json obj, and connects them with the one that
    cites them.
    """
    citations = [value['title'] for value in obj['bib_entries'].values()]
    query = (f'MATCH (p:Paper) WHERE p.title IN {citations} '
              'WITH collect(p) as papers '
             f'MATCH (p:Paper {{filename: "{filename}"}}) '
              'UNWIND papers as paper '
              'CREATE (p)-[:cites]->(paper)')
    database.execute(query, 'w')

def create_text(obj, filename, fieldname, database):
    """
    Wrapper function that extracts a specific type of text
    from the json obj, generates its important terms
    and finally creates the graph of words associated
    with the text.
    """
    text = ''.join(item['text'] for item in obj[fieldname])
    if text == '': return
    create_graph_of_words(generate_words(text), 
                          database, filename, 'includes')
    return

def create_text_authors_citations_from_json(database):
    """
    Function that gathers all calls to specialized create() functions,
    in order to create the entirety of the graph.
    """
    dirpath = r'C:\Users\USER\Desktop\CORD-19-research-challenge\dataset'
    current_system = platform.system()

    # Read plaintext from files, which becomes a string in a list called dataset.
    filenames = list_filenames(dirpath)
    # Specify the last file before the crash manually in the place of index.
    #filenames = skip_filenames(filenames, index) 
    count = 1
    total_count = len(filenames)

    # Iterate all file records of the dataset.
    for filename in filenames:
        start = timer() # Start timer to count the time,
                        # it takes to fully create one file in the database
        # Write current filename, in case of a random app crash.
        with open('last_accessed_file.txt', 'w') as f:
            f.write(filename)
        

        # Print the number of the currently processed file.
        print(f'Processing info for {count} out of {total_count} papers...' )
        
        # Read the file as a plaintext string.
        obj = json.loads(read_file(dirpath, filename))
        # Remove the .json extension from the filename.
        filename = filename.split('.', 1)[0]
        
        # Generate the terms and create the entire  
        # graph of docs from the abstract of each file.
        create_text(obj, filename, 'abstract', database)
        
        create_authors(filename, obj, database)
        create_citations(filename, obj, database)
        
        # Update the progress counter.
        count = count + 1
        # Stop the timer.
        end = timer()
        # Clear the screen to output the update the progress counter.
        clear_screen(current_system)
        # Print the duration in seconds.
        print(f'Time duration of last iteration = {end - start} seconds')   
    
    print(f'Created info for {total_count} papers.')
    return

def create_co_authors_graph(database):
    """
    Function that creates the co-authors subgraph,
    which is used for the machine learning link prediction model
    """
    # Create the entire co-author subgraph.
    query = (
        'MATCH (a1:Author)-[:writes]->(p:Paper)<-[:writes]-(a2:Author) ' 
        'WITH a1, a2, p '
        'ORDER BY a1, p.year '
        'WITH a1, a2, collect(p)[0].year AS first_year '
        'MERGE (a1)-[coauthor: co_author {year: first_year}]-(a2)'
    )
    database.execute(query, 'r')

    # Create the training subgraph of co-author.
    query = (
        'MATCH (a:Author)-[r:co_author]->(b:Author) '
        'WHERE r.year < "2013" '
        'MERGE (a)-[:co_author_early {year: r.year}]-(b)'
    )
    database.execute(query, 'r')
    
    # Create the testing subgraph of co-author.
    query = (
        'MATCH (a:Author)-[r:co_author]->(b:Author) '
        'WHERE r.year >= "2013" '
        'MERGE (a)-[:co_author_late {year: r.year}]-(b)'
    )
    database.execute(query, 'r')
    return