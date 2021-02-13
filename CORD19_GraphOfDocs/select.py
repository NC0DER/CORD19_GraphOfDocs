"""
This script contains functions that 
select data in the Neo4j database,
to generate train / test datasets
and features for a Machine learning
model.
"""
def get_positive_examples(database, limit, train_set = True):
    relationship = 'co_author_early' if train_set else 'co_author_late'
    query = (
        f'MATCH (author:Author)-[:{relationship}]->(other:Author) '
         'WITH id(author) AS node1, id(other) AS node2, 1 AS label, rand() AS random '
         'WHERE random > 0.5 '
        f'RETURN node1, node2, label LIMIT {limit}'
    )
    return database.execute(query, 'r')

def get_negative_examples(database, limit, train_set = True, min_hops = 2, max_hops = 3):
    relationship = 'co_author_early' if train_set else 'co_author_late'
    query = (
        f'MATCH (author:Author)-[:{relationship}*{min_hops}..{max_hops}]-(other:Author) '
        f'WHERE author <> other AND NOT (author)-[:{relationship}]-(other) '
         'WITH id(author) AS node1, id(other) AS node2, 0 AS label, rand() AS random '
         'WHERE random > 0.5 '
        f'RETURN node1, node2, label LIMIT {limit}'
    )
    return database.execute(query, 'r')

def create_graph_features(database, data, train_set):
    relationship = 'co_author_early' if train_set else 'co_author_late'
    similarity_edge = 'is_similar_early' if train_set else 'is_similar_late'

    query = (
    f'UNWIND {data} AS pair '
    'MATCH (p1) WHERE id(p1) = pair[0] '
    'MATCH (p2) WHERE id(p2) = pair[1] '
    f'OPTIONAL MATCH (p1)-[r:{similarity_edge}]-(p2) '
    'RETURN p1.name AS node1, '
    '       p2.name AS node2, '
    '       gds.alpha.linkprediction.adamicAdar('
    f'       p1, p2, {{relationshipQuery: "{relationship}"}}) AS aa, '
    '       gds.alpha.linkprediction.commonNeighbors('
    f'       p1, p2, {{relationshipQuery: "{relationship}"}}) AS cn, '
    '       gds.alpha.linkprediction.preferentialAttachment('
    f'       p1, p2, {{relationshipQuery: "{relationship}"}}) AS pa, '
    '       gds.alpha.linkprediction.totalNeighbors('
    f'       p1, p2, {{relationshipQuery: "{relationship}"}}) AS tn, '
    '       r.score AS similarity, '
    '       pair[2] AS label       '
    )
    return database.execute(query, 'r')