class GraphAlgos:
    """
    Wrapper class which handle the graph algorithms 
    more efficiently, by abstracting repeating code.
    """
    database = None # Static variable shared across objects.

    def __init__(self, database, node_list, rel_list, orientation = "NATURAL"):
        # Initialize the static variable and class member.
        if GraphAlgos.database is None:
            GraphAlgos.database = database

        # Construct the relationship string.
        if type(rel_list[0]) is str:
            rel_string = ', '.join(
                (f'{rel}: {{type: "{rel}", orientation: "{orientation}"}}')
                for rel in rel_list)
        else:
            rel_string = ', '.join(
                (f'{rel[0]}: {{type: "{rel[0]}", orientation: "{rel[1]}", properties: {rel[2]}}}')
                for rel in rel_list)

        # Construct the projection of the anonymous graph.
        self.graph_projection = (
            f'{{nodeProjection: {node_list}, '
            f'relationshipProjection: {{{rel_string}}}'
        )

    def pagerank(self, write_property, max_iterations = 20, damping_factor = 0.85):
        setup = (f'{self.graph_projection}, '
            f'writeProperty: "{write_property}", '
            f'maxIterations: {max_iterations}, '
            f'dampingFactor: {damping_factor}}}'
        )
        GraphAlgos.database.execute(f'CALL gds.pageRank.write({setup})', 'w')

    def nodeSimilarity(self, write_property, write_relationship, cutoff = 0.5, top_k = 10):
        setup = (f'{self.graph_projection}, '
            f'writeProperty: "{write_property}", '
            f'writeRelationshipType: "{write_relationship}", '
            f'similarityCutoff: {cutoff}, '
            f'topK: {top_k}}}'
        )
        query = f'CALL gds.nodeSimilarity.write({setup})'
        GraphAlgos.database.execute(f'CALL gds.nodeSimilarity.write({setup})', 'w')

    def louvain(self, write_property, max_levels = 10, max_iterations = 10):
        setup = (f'{self.graph_projection}, '
            f'writeProperty: "{write_property}", '
            f'maxLevels: {max_levels}, '
            f'maxIterations: {max_iterations}}}'
        )
        GraphAlgos.database.execute(f'CALL gds.louvain.write({setup})', 'w')

    # These methods enable the use of this class in a with statement.
    def __enter__(self):
        return self

    # Automatic cleanup of the created graph of this class.
    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)